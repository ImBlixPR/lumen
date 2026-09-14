import time
import wave
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from lumen.services.book_library import LibraryStore, fold, scan_folder
from lumen.services.library import BookInfo
from lumen.services.settings import SettingsStore


@pytest.fixture
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def make_wav(path: Path, seconds: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds) + path.name.encode())  # unique content
    return path


def info(key: str, path: Path, title: str, author: str = "", duration: float = 100.0) -> BookInfo:
    return BookInfo(path=str(path), key=key, title=title, author=author, duration=duration)


def test_search_ignores_case_and_accents():
    assert fold("Ernest & Célestine") == "ernest & celestine"


def test_opened_books_are_listed_and_persisted(app, tmp_path):
    settings = SettingsStore(tmp_path)
    lib = LibraryStore(settings, tmp_path)
    book = make_wav(tmp_path / "books" / "a.wav")
    lib.record_opened(info("k1", book, "Ernest & Célestine", "Daniel Pennac"))
    again = LibraryStore(settings, tmp_path)
    (row,) = again.books
    assert row["title"] == "Ernest & Célestine" and row["exists"] is True


def test_search_matches_title_author_and_words(app, tmp_path):
    lib = LibraryStore(SettingsStore(tmp_path), tmp_path)
    lib.record_opened(info("k1", tmp_path / "a.mp3", "Ernest & Célestine", "Daniel Pennac"))
    lib.record_opened(info("k2", tmp_path / "b.mp3", "Le Petit Prince", "Saint-Exupéry"))
    lib.setQuery("celestine")
    assert [b["key"] for b in lib.books] == ["k1"]
    lib.setQuery("exupery petit")
    assert [b["key"] for b in lib.books] == ["k2"]
    lib.setQuery("")
    assert len(lib.books) == 2


def test_most_recently_played_first_and_progress_from_positions(app, tmp_path):
    settings = SettingsStore(tmp_path)
    lib = LibraryStore(settings, tmp_path)
    lib.record_opened(info("old", tmp_path / "a.mp3", "Old"))
    time.sleep(0.01)
    lib.record_opened(info("new", tmp_path / "b.mp3", "New", duration=200.0))
    settings.save_position("new", 50.0)
    books = lib.books
    assert [b["key"] for b in books] == ["new", "old"]
    assert books[0]["progress"] == pytest.approx(0.25)
    assert books[1]["exists"] is False  # file isn't there: shown as missing


def test_favorites_view_and_persistence(app, tmp_path):
    settings = SettingsStore(tmp_path)
    lib = LibraryStore(settings, tmp_path)
    lib.record_opened(info("k1", tmp_path / "a.mp3", "Ernest & Célestine"))
    lib.record_opened(info("k2", tmp_path / "b.mp3", "Le Petit Prince"))
    lib.toggleFavorite("k2")
    lib.setFilter("favorites")
    assert [b["key"] for b in lib.books] == ["k2"] and lib.books[0]["favorite"] is True
    assert lib.favoriteCount == 1

    lib.record_opened(info("k2", tmp_path / "b.mp3", "Le Petit Prince"))  # reopening keeps the heart
    again = LibraryStore(settings, tmp_path)
    again.setFilter("favorites")
    assert [b["key"] for b in again.books] == ["k2"]
    again.toggleFavorite("k2")
    assert again.books == [] and again.favoriteCount == 0


def test_recently_played_only_lists_played_books_latest_first(app, tmp_path):
    lib = LibraryStore(SettingsStore(tmp_path), tmp_path)
    lib._import_now([make_wav(tmp_path / "Never played.wav")])
    lib.record_opened(info("first", tmp_path / "a.mp3", "First"))
    time.sleep(0.01)
    lib.record_opened(info("second", tmp_path / "b.mp3", "Second"))
    lib.setFilter("recent")
    books = lib.books
    assert [b["key"] for b in books] == ["second", "first"]
    assert books[0]["playedText"] == "Today"
    assert lib.recentCount == 2 and lib.total == 3
    lib.setQuery("first")  # search works inside a view
    assert [b["key"] for b in lib.books] == ["first"]


def test_played_label():
    from datetime import date, datetime

    from lumen.services.book_library import played_label

    today = date(2026, 9, 12)

    def at(y, m, d):
        return datetime(y, m, d, 15, 0).timestamp()

    assert played_label(0, today) == ""
    assert played_label(at(2026, 9, 12), today) == "Today"
    assert played_label(at(2026, 9, 11), today) == "Yesterday"
    assert played_label(at(2026, 9, 8), today) == "4 days ago"
    assert played_label(at(2026, 8, 30), today) == "30 Aug"
    assert played_label(at(2025, 12, 24), today) == "24 Dec 2025"


def test_remove_keeps_the_file(app, tmp_path):
    lib = LibraryStore(SettingsStore(tmp_path), tmp_path)
    book = make_wav(tmp_path / "a.wav")
    lib.record_opened(info("k1", book, "A"))
    lib.remove("k1")
    assert lib.books == [] and book.exists()


def test_import_reads_real_files_and_recognises_moved_books(app, tmp_path):
    lib = LibraryStore(SettingsStore(tmp_path), tmp_path)
    first = make_wav(tmp_path / "in" / "Mon livre.wav")
    make_wav(tmp_path / "in" / "sub" / "Deuxième.wav")
    (tmp_path / "in" / "notes.txt").write_text("not audio")
    found = scan_folder(tmp_path / "in")
    assert sorted(p.name for p in found) == ["Deuxième.wav", "Mon livre.wav"]

    results = []
    lib.imported.connect(lambda added, failed: results.append((added, failed)))
    lib._import_now(found + [tmp_path / "in" / "notes.txt"])
    assert results == [(2, 1)]
    assert sorted(b["title"] for b in lib.books) == ["Deuxième", "Mon livre"]

    moved = tmp_path / "elsewhere" / "renamed.wav"
    moved.parent.mkdir()
    first.rename(moved)
    lib._import_now([moved])
    assert results[-1] == (0, 0)  # same book, not a duplicate
    assert any(b["path"] == str(moved) for b in lib.books) and len(lib.books) == 2
