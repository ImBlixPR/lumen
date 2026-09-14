"""The background processing process.

The UI process sends plain-dict commands over a multiprocessing queue and receives
plain-dict events back. All model work happens here, so a slow model, a CUDA error or even
a crash never freezes the player. The loop:

1. Apply every waiting command (open a book, playhead moved, native language changed…).
2. Do one unit of work, in this priority order:
   a. translate cached sentences that lack a translation, nearest the playhead first;
   b. transcribe and translate the next window: the first gap at or after the playhead.
      Windows start at 60 s and double up to 4–8 min, so the first subtitles arrive fast.
3. While a window transcribes, watch for a seek that makes it pointless and abandon it.

Run `python -m lumen.pipeline.worker book.mp3 --src fr --tgt ar` to exercise it without the UI.
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import queue
import re
import sys
import time
import traceback
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import languages
from .cache import CacheStore, CachedSentence
from .decoder import AudioDecoder, probe_duration
from .device import DeviceInfo, detect, lower_process_priority
from .scheduler import EPS, Window, covered_seconds, first_gap, next_window, plan_commit, ready_until
from .sentences import build_sentences

PROGRESS_INTERVAL = 0.5
FIRST_WINDOW = 60.0
MAX_WINDOW = {"cuda": 480.0, "cpu": 240.0}
TRANSLATE_BATCH = 24
BACKLOG_LOOKBEHIND = 30.0


class Abort(Exception):
    """A command arrived that makes the window being transcribed pointless."""


def normalize_names(text: str) -> list[str]:
    """" Ernest ,Célestine\\nernest" → ["Ernest", "Célestine"]: split on commas, semicolons or
    new lines, tidy spaces, drop duplicates (case-insensitive), keep at most 30."""
    seen: set[str] = set()
    names: list[str] = []
    for part in re.split(r"[,;\n]+", text or ""):
        name = " ".join(part.split())
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            names.append(name)
    return names[:30]


def prompt_hint(title: str, names: str = "") -> str:
    """Whisper prompt hint from the book title and its character names
    ("ERNEST & CELESTINE", "Ernest, Célestine" → "Ernest & Celestine. Ernest, Célestine.").

    Whisper is biased toward the spellings in its prompt, which fixes misheard character
    names. All-caps tags are title-cased so the hint doesn't push the output into capitals.
    """
    title = " ".join(title.split())[:120]
    title = " ".join(w.capitalize() if w.isupper() and len(w) > 1 else w for w in title.split())
    parts = []
    if title:
        parts.append(title if title.endswith((".", "!", "?")) else title + ".")
    listed = normalize_names(names)
    if listed:
        parts.append(", ".join(listed)[:200] + ".")
    return " ".join(parts)


def _parent_alive() -> bool:
    """False once the UI process is gone (True when running in-process, e.g. the self-test)."""
    parent = multiprocessing.parent_process()
    return parent is None or parent.is_alive()


@dataclass
class Job:
    path: str
    duration: float
    src: str
    tgt: str
    mt_model: str
    cache: CacheStore
    decoder: AudioDecoder
    playhead: float = 0.0
    hint: str = ""  # book title + names: Whisper's initial prompt (first segment of a window)
    names: str = ""  # character names: Whisper hotwords, repeated on every segment
    windows_done: int = 0
    done: bool = False

    def close(self) -> None:
        self.decoder.close()
        self.cache.close()


class PipelineWorker:
    def __init__(self, commands: Any, events: Any):
        self.commands = commands
        self.events = events
        self.pending: deque[dict] = deque()
        self.job: Job | None = None
        self.device: DeviceInfo | None = None
        self.transcriber = None
        self.translator = None
        self._asr_dir: str | None = None
        self._mt_dir: str | None = None
        self._last_progress = 0.0
        self._job_id = 0  # echoed in every event so the UI can drop stale ones after a switch

    def emit(self, kind: str, **payload: Any) -> None:
        self.events.put({"type": kind, "job": self._job_id, **payload})

    # -- main loop ----------------------------------------------------------------------------
    def serve(self) -> None:
        while True:
            busy = self.job is not None and not self.job.done
            cmd = self._take_command(block=not busy)
            if cmd is not None:
                if cmd["type"] == "shutdown":
                    self._close_job()
                    return
                self._guard(self._handle, cmd)
                continue
            if not _parent_alive():  # the UI was killed: don't linger holding the models
                self._close_job()
                return
            self._guard(self.step)

    def _take_command(self, block: bool) -> dict | None:
        if self.pending:
            return self.pending.popleft()
        if not block:
            try:
                return self.commands.get_nowait()
            except queue.Empty:
                return None
        while True:
            try:
                return self.commands.get(timeout=1.0)
            except queue.Empty:
                if not _parent_alive():
                    return {"type": "shutdown"}

    def _guard(self, fn, *args) -> None:
        try:
            fn(*args)
        except Abort:
            pass
        except Exception as exc:
            self.emit("error", message=f"{type(exc).__name__}: {exc}", detail=traceback.format_exc())
            if self.job is not None:
                self.job.done = True
                self.emit("status", state="error", message=str(exc))

    # -- commands -----------------------------------------------------------------------------
    def _handle(self, cmd: dict) -> None:
        kind = cmd["type"]
        if kind == "open":
            self._open(cmd)
        elif kind == "playhead" and self.job is not None:
            self._set_playhead(float(cmd["t"]))
        elif kind == "set_target" and self.job is not None:
            self._load_translator(cmd["mt_dir"])
            self.job.tgt = cmd["tgt"]
            self.job.mt_model = cmd["mt_model"]
            self.job.done = False
            self._emit_progress(force=True)
        elif kind == "close":
            self._close_job()
            self.emit("status", state="idle", message="")

    def _open(self, cmd: dict) -> None:
        self._close_job()
        self._job_id = int(cmd.get("job", 0))
        self.emit("status", state="loading", message="Loading models…")
        self._load_transcriber(cmd["asr_dir"])
        self._load_translator(cmd["mt_dir"])
        duration = float(cmd.get("duration") or 0.0) or probe_duration(cmd["path"])
        self.job = Job(
            path=cmd["path"], duration=duration, src=cmd["src"], tgt=cmd["tgt"],
            mt_model=cmd["mt_model"], cache=CacheStore(Path(cmd["cache_file"])),
            decoder=AudioDecoder(cmd["path"]), playhead=float(cmd.get("playhead", 0.0)),
            hint=prompt_hint(cmd.get("hint", ""), cmd.get("names", "")),
            names=", ".join(normalize_names(cmd.get("names", ""))),
        )
        self.job.cache.ensure_hint(self.job.hint)  # new character names → transcribe again
        device = self.transcriber.device
        self.emit("device", device=device.device, compute_type=device.compute_type, name=device.name)
        self.emit("status", state="processing", message="Preparing subtitles…")
        self._emit_progress(force=True)

    def _set_playhead(self, t: float) -> None:
        job = self.job
        job.playhead = t
        gap = first_gap(job.cache.coverage(), t, job.duration)
        if gap is not None and gap - t < 1.0:
            job.windows_done = 0  # landed in unprocessed audio: restart with a short window

    def _close_job(self) -> None:
        if self.job is not None:
            self.job.close()
            self.job = None

    def _ensure_device(self) -> DeviceInfo:
        if self.device is None:
            self.device = detect()
        return self.device

    def _load_transcriber(self, asr_dir: str) -> None:
        if asr_dir != self._asr_dir:
            from .transcriber import Transcriber

            self.transcriber = None  # free VRAM before loading the replacement
            self.transcriber = Transcriber(Path(asr_dir), self._ensure_device())
            self._asr_dir = asr_dir

    def _load_translator(self, mt_dir: str) -> None:
        if mt_dir != self._mt_dir:
            from .translator import Translator

            self.translator = None
            self.translator = Translator(Path(mt_dir), self._ensure_device())
            self._mt_dir = mt_dir

    # -- work ---------------------------------------------------------------------------------
    def step(self) -> None:
        job = self.job
        if job is None or job.done:
            return

        backlog = job.cache.untranslated(
            job.tgt, job.mt_model, near=max(0.0, job.playhead - BACKLOG_LOOKBEHIND), limit=TRANSLATE_BATCH
        )
        if backlog:
            pairs = self._translate(backlog)
            self.emit("translations", items=[[sid, text] for sid, text in pairs])
            self._emit_progress()
            return

        coverage = job.cache.coverage()
        window = next_window(coverage, job.playhead, job.duration, self._window_length())
        if window is None:
            job.done = True
            self._emit_progress(force=True)
            self.emit("status", state="done", message="All subtitles are ready")
            return
        self._process_window(window, coverage)

    def _window_length(self) -> float:
        device = self.transcriber.device.device if self.transcriber else "cpu"
        return min(MAX_WINDOW[device], FIRST_WINDOW * 2 ** self.job.windows_done)

    def _process_window(self, window: Window, coverage: list) -> None:
        job = self.job
        self.emit("status", state="processing", message="Transcribing…")
        audio = job.decoder.read(window.start, window.end)
        previous = job.cache.sentence_before(window.start)
        prompt = " ".join(p for p in (job.hint, previous.text[-200:] if previous else "") if p) or None

        def on_progress(t: float) -> None:
            self._check_for_abort(window, coverage)
            self._emit_progress(working=(window.start, min(t, window.end)))

        words = self.transcriber.transcribe(
            audio, window.start, job.src, prompt, on_progress, hotwords=job.names or None
        )
        sentences = build_sentences(words, job.src)
        existing = (
            job.cache.sentences_between(window.boundary, window.end) if window.boundary is not None else []
        )
        commit = plan_commit(sentences, window, existing)
        stored = job.cache.commit(window.start, commit.region_end, commit.sentences)
        translated = dict(self._translate(stored))
        job.windows_done += 1
        self.emit(
            "region",
            start=window.start,
            end=commit.region_end,
            sentences=[[s.id, s.start, s.end, translated.get(s.id)] for s in stored],
        )
        self._emit_progress(force=True)

    def _translate(self, rows: list[CachedSentence]) -> list[tuple[int, str]]:
        job = self.job
        pairs: list[tuple[int, str]] = []
        for i in range(0, len(rows), TRANSLATE_BATCH):
            batch = rows[i : i + TRANSLATE_BATCH]
            if job.src == job.tgt:
                texts = [r.text for r in batch]
            else:
                texts = self.translator.translate(
                    [r.text for r in batch], languages.flores(job.src), languages.flores(job.tgt)
                )
            chunk = [(r.id, text) for r, text in zip(batch, texts)]
            job.cache.save_translations(chunk, job.tgt, job.mt_model)
            pairs.extend(chunk)
        return pairs

    def _check_for_abort(self, window: Window, coverage: list) -> None:
        while True:
            try:
                cmd = self.commands.get_nowait()
            except queue.Empty:
                return
            self.pending.append(cmd)
            if cmd["type"] != "playhead":
                raise Abort
            t = float(cmd["t"])
            self.job.playhead = t
            gap = first_gap(coverage, t, self.job.duration)
            if gap is not None and not (window.start - EPS <= gap <= window.end):
                raise Abort

    def _emit_progress(self, force: bool = False, working: tuple[float, float] | None = None) -> None:
        now = time.monotonic()
        if not force and now - self._last_progress < PROGRESS_INTERVAL:
            return
        self._last_progress = now
        job = self.job
        coverage = job.cache.coverage()
        covered = covered_seconds(coverage)
        if working is not None:
            covered += max(0.0, working[1] - working[0])
        translated, sentences = job.cache.translated_count(job.tgt, job.mt_model)
        self.emit(
            "progress",
            covered=min(covered, job.duration),
            duration=job.duration,
            coverage=[[s, e] for s, e in coverage],
            working=list(working) if working else None,
            translated=translated,
            sentences=sentences,
        )


def run(commands: Any, events: Any) -> None:
    """Entry point of the worker process."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models are local; never touch the network
    lower_process_priority()
    try:
        PipelineWorker(commands, events).serve()
    except KeyboardInterrupt:
        pass


# -- command-line self-test ---------------------------------------------------------------------
def selftest(argv: list[str] | None = None) -> int:
    from .. import models, paths
    from .cache import book_key, cache_path

    parser = argparse.ArgumentParser(description="Transcribe and translate a book without the UI.")
    parser.add_argument("audio")
    parser.add_argument("--src", default="fr")
    parser.add_argument("--tgt", default="ar")
    parser.add_argument("--asr", default="small")
    parser.add_argument("--mt", default=models.DEFAULT_MT)
    parser.add_argument("--names", default=None,
                        help="character names, comma-separated (default: the names saved for this book)")
    parser.add_argument("--limit", type=float, default=0.0, help="stop once this many seconds are ready")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    asr, mt = models.get_model(args.asr), models.get_model(args.mt)
    for spec in (asr, mt):
        if not models.is_installed(spec):
            print(f"Model '{spec.id}' is not installed. Run: uv run python scripts/setup_models.py --asr {asr.id} --mt {mt.id}")
            return 1

    cache_file = cache_path(paths.cache_dir(), book_key(args.audio), args.src, asr.id)
    from ..services.library import read_book

    title = read_book(args.audio, book_key(args.audio)).title
    if args.names is None:
        from ..services.settings import SettingsStore

        args.names = SettingsStore().book_names(book_key(args.audio))
    events: queue.Queue = queue.Queue()
    worker = PipelineWorker(queue.Queue(), events)
    started = time.perf_counter()
    worker._handle({
        "type": "open", "path": args.audio, "src": args.src, "tgt": args.tgt, "mt_model": mt.id,
        "asr_dir": str(models.model_dir(asr)), "mt_dir": str(models.model_dir(mt)),
        "cache_file": str(cache_file), "playhead": 0.0, "hint": title, "names": args.names,
    })
    job = worker.job
    already = covered_seconds(job.cache.coverage())
    print(f"Book: {args.audio}  ({job.duration / 60:.1f} min)   cache: {cache_file.name}")
    print(f"Whisper hint: {job.hint or '(none)'}")
    print(f"Cached before this run: {already / 60:.1f} min")

    def drain() -> None:
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                return
            if event["type"] == "device":
                print(f"Device: {event['device']} ({event['compute_type']}) {event['name']}")
            elif event["type"] == "region":
                for _sid, start, end, text in event["sentences"]:
                    print(f"[{start:7.2f} → {end:7.2f}] {text}")
            elif event["type"] == "error":
                print(event["detail"])

    drain()
    processing_started = time.perf_counter()
    while not job.done:
        worker._guard(worker.step)
        drain()
        if args.limit and ready_until(job.cache.coverage(), 0.0) >= min(args.limit, job.duration - EPS):
            break
    elapsed = time.perf_counter() - processing_started
    processed = covered_seconds(job.cache.coverage()) - already
    subtitles = job.cache.subtitles(args.tgt, mt.id)
    print(f"\nSubtitles ready: {sum(1 for s in subtitles if s.text)} / {len(subtitles)}")
    print(f"Model load: {processing_started - started:.1f} s   processing: {elapsed:.1f} s")
    if processed > 1:
        print(f"Processed {processed / 60:.1f} min of audio at {processed / max(elapsed, 1e-6):.1f}× real time")
    else:
        print("Everything came from the cache.")
    worker._close_job()
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest())
