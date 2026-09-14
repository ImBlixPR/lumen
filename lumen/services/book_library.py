"""Your audiobook library: every book you've added or opened, with search.

A small JSON index (`library.json` in the config folder) of what read_book() already
extracts (title, author, cover, duration), plus when each book was added and last played.
Books are identified by the same content key as the cache and the resume positions, so a
moved or renamed file is recognised when it's added again. Reading progress isn't stored
here; it comes from the resume positions in SettingsStore.
"""

from __future__ import annotations

import json
import os
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from .. import paths
from ..pipeline.cache import book_key
from .library import SUPPORTED_SUFFIXES, BookInfo, read_book
from .settings import SettingsStore

MAX_SCAN = 5000  # files considered when adding a folder


@dataclass
class Entry:
    key: str
    path: str
    title: str
    author: str = ""
    cover: str = ""
    duration: float = 0.0
    added: float = 0.0
    played: float = 0.0
    favorite: bool = False


FILTERS = ("all", "favorites", "recent")


def played_label(played: float, today: date | None = None) -> str:
    """When a book was last played, for the Recently Played view ("Today", "3 days ago"…)."""
    if played <= 0:
        return ""
    day = datetime.fromtimestamp(played).date()
    days = ((today or date.today()) - day).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return f"{day.day} {day.strftime('%b')}" + ("" if day.year == (today or date.today()).year else f" {day.year}")


def fold(text: str) -> str:
    """Case- and accent-insensitive form for search ("Célestine" → "celestine")."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def matches(entry: Entry, query: str) -> bool:
    haystack = fold(f"{entry.title} {entry.author} {Path(entry.path).stem}")
    return all(word in haystack for word in fold(query).split())


def scan_folder(folder: str | Path, limit: int = MAX_SCAN) -> list[Path]:
    found: list[Path] = []
    for root, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if name.lower().endswith(SUPPORTED_SUFFIXES):
                found.append(Path(root) / name)
                if len(found) >= limit:
                    return found
    return found


class LibraryStore(QObject):
    booksChanged = Signal()
    importingChanged = Signal()
    imported = Signal(int, int)  # books added, files that couldn't be read
    _found = Signal(object)      # Entry, from the import thread
    _finished = Signal(int)      # failures, from the import thread

    def __init__(self, settings: SettingsStore, folder: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._path = (folder or paths.config_dir()) / "library.json"
        self._entries: dict[str, Entry] = self._load()
        self._query = ""
        self._filter = "all"
        self._importing = False
        self._new_in_import = 0
        self._found.connect(self._on_found)
        self._finished.connect(self._on_finished)

    # -- persistence --------------------------------------------------------------------------
    def _load(self) -> dict[str, Entry]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        entries = {}
        for item in raw.get("books", []) if isinstance(raw, dict) else []:
            try:
                entry = Entry(**{k: item[k] for k in Entry.__dataclass_fields__ if k in item})
            except TypeError:
                continue
            entries[entry.key] = entry
        return entries

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        data = {"books": [asdict(e) for e in self._entries.values()]}
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path)

    # -- QML API ------------------------------------------------------------------------------
    @Property("QVariantList", notify=booksChanged)
    def books(self) -> list:
        """Books in the current view that match the search.

        all        every book, most recently played or added first
        favorites  hearted books, same order
        recent     books that have been played, most recent first
        """
        shown = [e for e in self._entries.values() if not self._query or matches(e, self._query)]
        if self._filter == "favorites":
            shown = [e for e in shown if e.favorite]
        if self._filter == "recent":
            shown = [e for e in shown if e.played > 0]
            shown.sort(key=lambda e: e.played, reverse=True)
        else:
            shown.sort(key=lambda e: max(e.played, e.added), reverse=True)
        return [self._to_qml(e) for e in shown]

    @Property(int, notify=booksChanged)
    def total(self) -> int:
        return len(self._entries)

    @Property(int, notify=booksChanged)
    def favoriteCount(self) -> int:
        return sum(1 for e in self._entries.values() if e.favorite)

    @Property(int, notify=booksChanged)
    def recentCount(self) -> int:
        return sum(1 for e in self._entries.values() if e.played > 0)

    @Property(str, notify=booksChanged)
    def filter(self) -> str:
        return self._filter

    @Slot(str)
    def setFilter(self, name: str) -> None:
        name = name if name in FILTERS else "all"
        if name != self._filter:
            self._filter = name
            self.booksChanged.emit()

    @Slot(str)
    def toggleFavorite(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry is not None:
            entry.favorite = not entry.favorite
            self._save()
            self.booksChanged.emit()

    @Property(str, notify=booksChanged)
    def query(self) -> str:
        return self._query

    @Property(bool, notify=importingChanged)
    def importing(self) -> bool:
        return self._importing

    @Slot(str)
    def setQuery(self, text: str) -> None:
        text = text.strip()
        if text != self._query:
            self._query = text
            self.booksChanged.emit()

    @Slot()
    def refresh(self) -> None:
        """Re-read progress (resume positions change while you listen)."""
        self.booksChanged.emit()

    @Slot(str)
    def remove(self, key: str) -> None:
        """Remove a book from the library. The file itself is never touched."""
        if self._entries.pop(key, None) is not None:
            self._save()
            self.booksChanged.emit()

    @Slot()
    def addFilesDialog(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        patterns = " ".join(f"*{s}" for s in SUPPORTED_SUFFIXES)
        files, _ = QFileDialog.getOpenFileNames(None, "Add audiobooks", str(Path.home()), f"Audiobooks ({patterns})")
        if files:
            self.addFiles(files)

    @Slot()
    def addFolderDialog(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(None, "Add a folder of audiobooks", str(Path.home()))
        if folder:
            self.addFolder(folder)

    @Slot("QStringList")
    def addFiles(self, files: list[str]) -> None:
        local = [QUrl(f).toLocalFile() if f.startswith("file:") else f for f in files]
        self._start_import([Path(f) for f in local])

    @Slot(str)
    def addFolder(self, folder: str) -> None:
        if folder.startswith("file:"):
            folder = QUrl(folder).toLocalFile()
        threading.Thread(target=lambda: self._import_now(scan_folder(folder)), name="library-scan", daemon=True).start()
        self._set_importing(True)

    # -- used by AppController ----------------------------------------------------------------
    def record_opened(self, info: BookInfo) -> None:
        """A book was opened: add it (or refresh it) and mark it as just played."""
        now = time.time()
        old = self._entries.get(info.key)
        self._entries[info.key] = Entry(
            key=info.key, path=info.path, title=info.title, author=info.author, cover=info.cover,
            duration=info.duration, added=old.added if old else now, played=now,
            favorite=old.favorite if old else False,
        )
        self._save()
        self.booksChanged.emit()

    # -- importing ----------------------------------------------------------------------------
    def _start_import(self, files: list[Path]) -> None:
        self._set_importing(True)
        threading.Thread(target=self._import_now, args=(files,), name="library-import", daemon=True).start()

    def _import_now(self, files: list[Path]) -> None:
        """Read metadata for each file (off the UI thread) and hand the entries back."""
        failures = 0
        for file in files:
            if not file.is_file() or not file.name.lower().endswith(SUPPORTED_SUFFIXES):
                failures += 1
                continue
            try:
                key = book_key(file)
                info = read_book(file, key)
            except Exception:
                failures += 1
                continue
            self._found.emit(Entry(key=key, path=str(file), title=info.title, author=info.author,
                                   cover=info.cover, duration=info.duration, added=time.time()))
        self._finished.emit(failures)

    def _on_found(self, entry: Entry) -> None:
        old = self._entries.get(entry.key)
        if old is None:
            self._new_in_import += 1
        else:  # same book (maybe moved): keep its history
            entry.added, entry.played, entry.favorite = old.added, old.played, old.favorite
        self._entries[entry.key] = entry

    def _on_finished(self, failures: int) -> None:
        self._save()
        added, self._new_in_import = self._new_in_import, 0
        self._set_importing(False)
        self.booksChanged.emit()
        self.imported.emit(added, failures)

    def _set_importing(self, value: bool) -> None:
        if value != self._importing:
            self._importing = value
            self.importingChanged.emit()

    def _to_qml(self, entry: Entry) -> dict:
        position = self._settings.position(entry.key)
        progress = min(1.0, position / entry.duration) if entry.duration > 0 else 0.0
        return {
            "key": entry.key, "path": entry.path, "title": entry.title, "author": entry.author,
            "cover": entry.cover, "duration": entry.duration, "progress": progress,
            "finished": progress >= 0.98, "started": position > 5, "exists": Path(entry.path).is_file(),
            "favorite": entry.favorite, "playedText": played_label(entry.played),
        }
