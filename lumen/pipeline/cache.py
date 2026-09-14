"""Per-book SQLite cache of sentences, translations and processed coverage.

One database file per (book, source language, speech model), so switching models never
mixes transcripts. Translations are keyed by target language and translation model, so
changing your native language re-translates cached sentences without re-transcribing.
The worker process writes and the UI process reads; WAL mode makes that safe.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .scheduler import EPS, Interval, merge_intervals
from .sentences import Sentence

SCHEMA_VERSION = "1"
# Bump whenever sentence building or transcription prompting changes. Caches made by an older
# version are then discarded and redone, so earlier books pick up the improvements instead of
# keeping their old subtitles forever.
# 2: subtitles capped at 8 s / 110 characters; the book title is sent as a Whisper hint.
# 3: per-book character names join the hint, and the hint used is stored (see ensure_hint).
# 4: character names are also Whisper hotwords, so they help on every segment, not just the first.
# 5: a one-word fragment misplaced before a pause joins the sentence it begins.
TRANSCRIPT_VERSION = "5"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sentences (
    id INTEGER PRIMARY KEY,
    start REAL NOT NULL,
    end REAL NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sentences_start ON sentences(start);
CREATE TABLE IF NOT EXISTS translations (
    sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    tgt_lang TEXT NOT NULL,
    mt_model TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (sentence_id, tgt_lang, mt_model)
);
CREATE TABLE IF NOT EXISTS coverage (start REAL NOT NULL, end REAL NOT NULL);
"""


@dataclass(frozen=True, slots=True)
class CachedSentence:
    id: int
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class Subtitle:
    id: int
    start: float
    end: float
    text: str | None  # translation; None until translated


def book_key(path: str | os.PathLike[str]) -> str:
    """Stable identity for an audio file: size plus hashes of its first and last megabyte.

    Cheap even for 1 GB audiobooks, and unaffected by renaming or moving the file.
    """
    block = 1 << 20
    size = os.path.getsize(path)
    digest = hashlib.sha256(str(size).encode())
    with open(path, "rb") as fh:
        digest.update(fh.read(block))
        if size > block:
            fh.seek(max(block, size - block))
            digest.update(fh.read(block))
    return digest.hexdigest()[:32]


def cache_path(cache_dir: Path, key: str, src_lang: str, asr_model: str) -> Path:
    safe_model = asr_model.replace("/", "_").replace(".", "_")
    return cache_dir / f"{key}-{src_lang}-{safe_model}.sqlite"


class CacheStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._db = sqlite3.connect(path, timeout=15, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(_SCHEMA)
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema', ?)", (SCHEMA_VERSION,)
            )
        if self.get_meta("transcript") != TRANSCRIPT_VERSION:
            with self._db:  # outdated transcript: drop it (translations cascade) and start over
                self._db.execute("DELETE FROM sentences")
                self._db.execute("DELETE FROM coverage")
                self._db.execute("DELETE FROM meta WHERE key = 'hint'")
                self._db.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES ('transcript', ?)", (TRANSCRIPT_VERSION,)
                )

    def close(self) -> None:
        self._db.close()

    # -- meta ---------------------------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self._db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))

    def ensure_hint(self, hint: str) -> None:
        """Discard the transcript if it was made with a different Whisper hint (e.g. edited
        character names), so the book is transcribed again with the new one."""
        stored = self.get_meta("hint")
        if stored == hint:
            return
        if stored is not None:
            with self._db:
                self._db.execute("DELETE FROM sentences")
                self._db.execute("DELETE FROM coverage")
        self.set_meta("hint", hint)

    # -- coverage -----------------------------------------------------------------------------
    def coverage(self) -> list[Interval]:
        rows = self._db.execute("SELECT start, end FROM coverage").fetchall()
        return merge_intervals((float(s), float(e)) for s, e in rows)

    # -- sentences ----------------------------------------------------------------------------
    def commit(
        self, region_start: float, region_end: float, sentences: Sequence[Sentence]
    ) -> list[CachedSentence]:
        """Atomically replace the sentences that start inside the region and mark it covered."""
        with self._db:
            self._db.execute(
                "DELETE FROM sentences WHERE start >= ? AND start < ?",
                (region_start - EPS, region_end - EPS),
            )
            stored: list[CachedSentence] = []
            for s in sentences:
                cur = self._db.execute(
                    "INSERT INTO sentences(start, end, text) VALUES (?, ?, ?)",
                    (s.start, s.end, s.text),
                )
                stored.append(CachedSentence(int(cur.lastrowid), s.start, s.end, s.text))
            merged = merge_intervals([*self.coverage(), (region_start, region_end)])
            self._db.execute("DELETE FROM coverage")
            self._db.executemany("INSERT INTO coverage(start, end) VALUES (?, ?)", merged)
        return stored

    def sentences_between(self, start: float, end: float) -> list[CachedSentence]:
        rows = self._db.execute(
            "SELECT id, start, end, text FROM sentences WHERE start >= ? AND start < ? ORDER BY start",
            (start - EPS, end),
        ).fetchall()
        return [CachedSentence(*row) for row in rows]

    def sentence_before(self, t: float) -> CachedSentence | None:
        row = self._db.execute(
            "SELECT id, start, end, text FROM sentences WHERE end <= ? ORDER BY end DESC LIMIT 1",
            (t + EPS,),
        ).fetchone()
        return CachedSentence(*row) if row else None

    # -- translations -------------------------------------------------------------------------
    def untranslated(
        self, tgt_lang: str, mt_model: str, near: float = 0.0, limit: int = 64
    ) -> list[CachedSentence]:
        """Untranslated sentences, those at or after `near` first, then everything before."""
        rows = self._db.execute(
            """
            SELECT s.id, s.start, s.end, s.text FROM sentences s
            LEFT JOIN translations t
              ON t.sentence_id = s.id AND t.tgt_lang = ? AND t.mt_model = ?
            WHERE t.sentence_id IS NULL
            ORDER BY (s.start < ?), s.start
            LIMIT ?
            """,
            (tgt_lang, mt_model, near, limit),
        ).fetchall()
        return [CachedSentence(*row) for row in rows]

    def save_translations(
        self, items: Iterable[tuple[int, str]], tgt_lang: str, mt_model: str
    ) -> None:
        with self._db:
            self._db.executemany(
                """
                INSERT OR REPLACE INTO translations(sentence_id, tgt_lang, mt_model, text)
                SELECT ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM sentences WHERE id = ?)
                """,
                [(sid, tgt_lang, mt_model, text, sid) for sid, text in items],
            )

    def subtitles(self, tgt_lang: str, mt_model: str) -> list[Subtitle]:
        rows = self._db.execute(
            """
            SELECT s.id, s.start, s.end, t.text FROM sentences s
            LEFT JOIN translations t
              ON t.sentence_id = s.id AND t.tgt_lang = ? AND t.mt_model = ?
            ORDER BY s.start
            """,
            (tgt_lang, mt_model),
        ).fetchall()
        return [Subtitle(*row) for row in rows]

    def translated_count(self, tgt_lang: str, mt_model: str) -> tuple[int, int]:
        total = self._db.execute("SELECT COUNT(*) FROM sentences").fetchone()[0]
        done = self._db.execute(
            "SELECT COUNT(*) FROM translations WHERE tgt_lang = ? AND mt_model = ?",
            (tgt_lang, mt_model),
        ).fetchone()[0]
        return int(done), int(total)
