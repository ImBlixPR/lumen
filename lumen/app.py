"""AppController: the one object QML talks to.

It owns playback, the subtitle track and clock, the worker process, the overlay, hotkeys
and the single-instance command channel, and exposes a small reactive surface to QML as
the `App` singleton.
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QFileDialog

from . import __version__, languages, models, native, paths
from .commands import CommandServer
from .pipeline.cache import CacheStore, book_key, cache_path
from .pipeline.scheduler import covered_seconds, ready_until
from .pipeline.worker import normalize_names, prompt_hint
from .services.book_library import LibraryStore
from .services.download_service import DownloadService
from .services.floating_player import FloatingPlayerController
from .services.library import SUPPORTED_SUFFIXES, BookInfo, read_book
from .services.overlay import OverlayController
from .services.player import PlayerService
from .services.settings import HOTKEY_ACTIONS, SettingsStore
from .services.subtitle_clock import SubtitleClock, SubtitleTrack
from .services.worker_bridge import WorkerBridge

log = logging.getLogger("lumen")

POSITION_SYNC_MS = 2000  # playhead updates to the worker while playing
MAX_RESTARTS = 3  # worker crashes tolerated per 5 minutes


def format_time(seconds: float) -> str:
    # QML can pass NaN before the duration is known (e.g. remaining = duration - position).
    seconds = max(0, int(seconds)) if math.isfinite(seconds) else 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _model_list(specs) -> list[dict]:
    return [
        {"id": s.id, "label": s.label, "sizeMb": s.size_mb, "speed": s.speed, "accuracy": s.accuracy,
         "note": s.note, "installed": models.is_installed(s)}
        for s in specs
    ]


class AppController(QObject):
    bookChanged = Signal()
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    rateChanged = Signal()
    progressChanged = Signal()
    statusChanged = Signal()
    deviceChanged = Signal()
    hotkeyErrorsChanged = Signal()
    modelsChanged = Signal()
    namesChanged = Signal()
    toast = Signal(str)
    showPlayerRequested = Signal()
    showLibraryRequested = Signal()
    showSettingsRequested = Signal(str)

    def __init__(self, settings: SettingsStore, theme, parent: QObject | None = None):
        super().__init__(parent)
        self.settings = settings
        self.theme = theme
        self.player = PlayerService(self)
        self.track = SubtitleTrack()
        self.clock = SubtitleClock(self.track, self)
        self.worker = WorkerBridge(self)
        self.downloads = DownloadService(self)
        self.hotkeys = native.HotkeyManager(self)
        self.commands = CommandServer(self)
        self.overlay = OverlayController(settings, theme, self)
        self.floating = FloatingPlayerController(self, self)
        self.library = LibraryStore(settings, parent=self)
        self.library.imported.connect(self._on_imported)

        self._book: BookInfo | None = None
        self._cache: CacheStore | None = None
        self._job = 0
        self._coverage: list[tuple[float, float]] = []
        self._covered = 0.0
        self._state = "idle"
        self._status_message = ""
        self._status_text = ""
        self._device = ""
        self._position = 0.0
        self._chapter = ""
        self._waiting = False
        self._hotkey_errors: dict[str, str] = {}
        self._windows: list = []
        self._restarts: list[float] = []
        self._gpu: dict | None = None
        self._deferred_open: str | None = None
        self._last_wait_check = 0.0

        self._ui_timer = QTimer(self, interval=100, timeout=self._sync_position)
        self._playhead_timer = QTimer(self, interval=POSITION_SYNC_MS, timeout=self._send_playhead)
        self._seek_debounce = QTimer(self, singleShot=True, interval=400, timeout=self._send_playhead)
        self._save_timer = QTimer(self, interval=5000, timeout=self._save_position)

        p = self.player
        p.positionChanged.connect(self.clock.report)
        p.playingChanged.connect(self._on_playing)
        p.rateChanged.connect(self._on_rate)
        p.durationChanged.connect(lambda _d: self.durationChanged.emit())
        p.seeked.connect(self._on_seeked)
        p.finished.connect(self.clock.finish)  # clear the overlay when the book ends
        p.error.connect(lambda message: self.toast.emit(f"Playback error: {message}"))
        p.outputChanged.connect(lambda name: self.toast.emit(f"Audio now plays on {name}"))
        self.clock.textChanged.connect(self.overlay.set_text)
        self.clock.tick.connect(self._on_tick)
        self.worker.event.connect(self._on_worker_event)
        self.worker.crashed.connect(self._on_worker_crashed)
        self.downloads.finished.connect(self._on_downloads_finished)
        settings.changed.connect(self._on_setting)
        theme.changed.connect(self._restyle_windows)
        self.hotkeys.activated.connect(self.runAction)
        self.commands.received.connect(self._on_command)

    # -- lifecycle ----------------------------------------------------------------------------
    def start(self, open_path: str | None = None) -> None:
        if not self.commands.listen():
            log.warning("single-instance command channel is unavailable")
        self._register_hotkeys()
        if self._hotkey_errors and self.hotkeys.supported:
            taken = ", ".join(self.settings[f"hotkey_{a}"] for a in self._hotkey_errors)
            log.warning("global shortcuts unavailable: %s", taken)
            # Deferred so the player window is up to show it.
            QTimer.singleShot(1500, lambda: self.toast.emit(
                f"{taken} is used by another app. Pick a new shortcut in Settings → Shortcuts."))
        self.player.set_volume(self.settings["volume"])
        path = open_path or self.settings["last_book"]
        if self.settings["onboarded"] and self._models_ready():
            if path and Path(path).is_file():
                # Reopen the last book paused, in the library window; nothing plays by itself.
                self._open_book(path, autoplay=bool(open_path))
        elif open_path:
            self._deferred_open = open_path

    def shutdown(self) -> None:
        self._save_position()
        self.settings.flush()
        self.hotkeys.unregister_all()
        self.worker.stop()
        if self._cache is not None:
            self._cache.close()

    # -- properties ---------------------------------------------------------------------------
    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(bool, notify=bookChanged)
    def hasBook(self) -> bool:
        return self._book is not None

    @Property("QVariantMap", notify=bookChanged)
    def book(self) -> dict:
        return self._book.to_qml() if self._book else {}

    @Property(str, notify=namesChanged)
    def bookNames(self) -> str:
        return self.settings.book_names(self._book.key) if self._book else ""

    @Property(bool, notify=playingChanged)
    def playing(self) -> bool:
        return self.player.playing

    @Property(float, notify=positionChanged)
    def position(self) -> float:
        return self._position

    @Property(float, notify=durationChanged)
    def duration(self) -> float:
        return self.player.duration or (self._book.duration if self._book else 0.0)

    @Property(float, notify=rateChanged)
    def rate(self) -> float:
        return self.player.rate

    @Property(bool, constant=True)
    def pitchCompensated(self) -> bool:
        return self.player.pitch_compensated

    @Property(str, notify=positionChanged)
    def chapter(self) -> str:
        return self._chapter

    @Property("QVariantList", notify=progressChanged)
    def coverage(self) -> list:
        return [[s, e] for s, e in self._coverage]

    @Property(float, notify=progressChanged)
    def processedSeconds(self) -> float:
        return self._covered

    @Property(float, notify=positionChanged)
    def aheadSeconds(self) -> float:
        return max(0.0, ready_until(self._coverage, self._position) - self._position)

    @Property(str, notify=statusChanged)
    def processingState(self) -> str:
        return self._state

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=statusChanged)
    def waiting(self) -> bool:
        return self._waiting

    @Property(str, notify=deviceChanged)
    def device(self) -> str:
        return self._device

    @Property("QVariantMap", notify=hotkeyErrorsChanged)
    def hotkeyErrors(self) -> dict:
        return self._hotkey_errors

    @Property(bool, constant=True)
    def hotkeysSupported(self) -> bool:
        return self.hotkeys.supported

    @Property("QVariantList", constant=True)
    def languages(self) -> list:
        return [{"code": l.code, "name": l.name, "native": l.native, "rtl": l.rtl} for l in languages.LANGUAGES]

    @Property("QVariantList", notify=modelsChanged)
    def asrModels(self) -> list:
        return _model_list(models.ASR_MODELS)

    @Property("QVariantList", notify=modelsChanged)
    def mtModels(self) -> list:
        return _model_list(models.MT_MODELS)

    @Property(bool, notify=modelsChanged)
    def modelsReady(self) -> bool:
        return self._models_ready()

    @Property("QVariantMap", constant=True)
    def gpu(self) -> dict:
        if self._gpu is None:
            from .pipeline.device import detect

            info = detect()
            self._gpu = {"available": info.device == "cuda", "name": info.name,
                         "recommendedAsr": models.default_asr(info.device == "cuda"),
                         "recommendedMt": models.default_mt(info.device == "cuda")}
        return self._gpu

    @Property(QObject, constant=True)
    def downloadService(self) -> QObject:
        return self.downloads

    @Property(bool, constant=True)
    def nativeBackdrop(self) -> bool:
        return native.backdrop_kind() in ("mica", "blur")

    # -- books --------------------------------------------------------------------------------
    def _models_ready(self) -> bool:
        try:
            return all(models.is_installed(models.get_model(self.settings[k])) for k in ("asr_model", "mt_model"))
        except KeyError:
            return False

    @Slot()
    def openBookDialog(self) -> None:
        last = self.settings["last_book"]
        start = str(Path(last).parent) if last else str(Path.home())
        patterns = " ".join(f"*{suffix}" for suffix in SUPPORTED_SUFFIXES)
        path, _ = QFileDialog.getOpenFileName(None, "Open audiobook", start, f"Audiobooks ({patterns})")
        if path:
            self.openBook(path)

    @Slot(str)
    def openBook(self, path: str) -> None:
        """A book picked by the user: it starts playing, which hands off to the floating player."""
        if path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        if Path(path).is_dir():  # a dropped folder: add its books to the library
            self.library.addFolder(path)
            self.showLibrary()
            return
        if self._book is not None and Path(self._book.path) == Path(path):
            self.player.play()  # the book that's already loaded: just carry on
            return
        self._open_book(path, autoplay=True)

    def _on_imported(self, added: int, failed: int) -> None:
        if added or failed:
            parts = [f"Added {added} book{'s' if added != 1 else ''}"] if added else ["No new books"]
            if failed:
                parts.append(f"{failed} file{'s' if failed != 1 else ''} couldn't be read")
            self.toast.emit(" · ".join(parts))

    def _open_book(self, path: str, autoplay: bool) -> None:
        if path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        file = Path(path)
        if not file.is_file():
            self.toast.emit(f"Can't find {file.name or path}")
            return
        if not self._models_ready():
            self._deferred_open = str(file)
            self.toast.emit("Download the speech and translation models first (Settings → Models).")
            return
        try:
            info = read_book(file, book_key(file))
        except Exception as exc:
            log.exception("could not open %s", file)
            self.toast.emit(f"Couldn't open {file.name}: {exc}")
            return
        self._close_book()
        self._book = info
        self._open_cache()
        start_at = self.settings.position(info.key)
        self._position = start_at
        self.clock.seeked(start_at)
        self.player.load(file, start_at=start_at, autoplay=autoplay)
        self.player.set_rate(self.settings["playback_rate"])
        self._send_open(start_at)
        self.settings.set("last_book", str(file))
        self.library.record_opened(info)
        self.bookChanged.emit()
        self.namesChanged.emit()
        self.durationChanged.emit()
        self.positionChanged.emit()
        self._update_status()

    def _close_book(self) -> None:
        if self._book is None:
            return
        self._save_position()
        self.player.stop()
        self.worker.send({"type": "close"})
        if self._cache is not None:
            self._cache.close()
            self._cache = None
        self.track.clear()
        self.clock.refresh()
        self._book = None
        self._coverage, self._covered, self._state = [], 0.0, "idle"
        self._waiting = False

    def _cache_file(self) -> Path:
        return cache_path(paths.cache_dir(), self._book.key, self.settings["src_lang"], self.settings["asr_model"])

    def _open_cache(self) -> None:
        if self._cache is not None:
            self._cache.close()
        self._cache = CacheStore(self._cache_file())
        # Same check as the worker: a transcript made with other character names is dropped now,
        # so stale subtitles never show while the new transcription catches up.
        self._cache.ensure_hint(prompt_hint(self._book.title, self.settings.book_names(self._book.key)))
        self.track.load(self._cache.subtitles(self.settings["tgt_lang"], self.settings["mt_model"]))
        self._set_coverage(self._cache.coverage())
        self.clock.refresh()

    def _send_open(self, playhead: float) -> None:
        asr = models.get_model(self.settings["asr_model"])
        mt = models.get_model(self.settings["mt_model"])
        self._job += 1
        self._state = "loading"
        self.worker.send({
            "type": "open", "job": self._job, "path": self._book.path, "duration": self._book.duration,
            "src": self.settings["src_lang"], "tgt": self.settings["tgt_lang"], "mt_model": mt.id,
            "asr_dir": str(models.model_dir(asr)), "mt_dir": str(models.model_dir(mt)),
            "cache_file": str(self._cache_file()), "playhead": playhead, "hint": self._book.title,
            "names": self.settings.book_names(self._book.key),
        })

    def _reopen(self) -> None:
        if self._book is not None:
            path = self._book.path
            was_playing = self.player.playing
            self._save_position()
            self._open_book(path, autoplay=was_playing)

    @Slot(str)
    def setBookNames(self, text: str) -> None:
        """Save this book's character names; the book is then transcribed again with them."""
        if self._book is None:
            return
        names = ", ".join(normalize_names(text))
        if names == self.settings.book_names(self._book.key):
            return
        self.settings.set_book_names(self._book.key, names)
        self.namesChanged.emit()
        self.toast.emit("Names saved. Transcribing the book again so they're spelled right…" if names
                        else "Names cleared. Transcribing the book again…")
        self._reopen()

    # -- playback -----------------------------------------------------------------------------
    @Slot()
    def togglePlay(self) -> None:
        if self._book is None:
            self.openBookDialog()
            return
        self._waiting = False
        self.player.toggle()

    @Slot(float)
    def seek(self, seconds: float) -> None:
        if self._book is not None:
            self.player.seek(seconds)

    @Slot(float)
    def skip(self, delta: float) -> None:
        if self._book is not None:
            self.player.skip(delta)

    @Slot()
    def backSentence(self) -> None:
        if self._book is None:
            return
        t = self.clock.position
        target = self.track.back_target(t) if len(self.track) else max(0.0, t - 5.0)
        self.player.seek(target)

    @Slot(float)
    def setRate(self, rate: float) -> None:
        self.player.set_rate(rate)

    @Slot(str)
    def runAction(self, action: str) -> None:
        {
            "play_pause": self.togglePlay,
            "back_sentence": self.backSentence,
            "toggle_overlay": self.toggleOverlay,
            "lock_overlay": self.toggleOverlayLock,
        }.get(action, lambda: None)()

    @Slot(float, result=str)
    def formatTime(self, seconds: float) -> str:
        return format_time(seconds)

    def _on_playing(self, playing: bool) -> None:
        self.clock.set_playing(playing)
        if playing:
            self._ui_timer.start()
            self._playhead_timer.start()
            self._save_timer.start()
        else:
            for timer in (self._ui_timer, self._playhead_timer, self._save_timer):
                timer.stop()
            self._sync_position()
            self._save_position()
            self._send_playhead()
        self.playingChanged.emit()

    def _on_rate(self, rate: float) -> None:
        self.clock.set_rate(rate)
        self.settings.set("playback_rate", rate)
        self.rateChanged.emit()

    def _on_seeked(self, seconds: float) -> None:
        self.clock.seeked(seconds)
        self._sync_position()
        self._seek_debounce.start()

    def _sync_position(self) -> None:
        self._position = self.clock.position
        chapter = self._book.chapter_at(self._position) if self._book else None
        self._chapter = chapter.title if chapter else ""
        self.positionChanged.emit()
        self._update_status()

    def _send_playhead(self) -> None:
        if self._book is not None:
            self.worker.send({"type": "playhead", "t": self.clock.position})

    def _save_position(self) -> None:
        if self._book is not None:
            self.settings.save_position(self._book.key, self.clock.position)

    # -- waiting for subtitles ----------------------------------------------------------------
    def _needs_wait(self, t: float) -> bool:
        if self._book is None or self._state not in ("loading", "processing"):
            return False
        covered = ready_until(self._coverage, t) > t + 0.5
        return not covered or self.track.pending_at(t)

    def _on_tick(self, t: float) -> None:
        now = time.monotonic()
        if now - self._last_wait_check < 0.25:
            return
        self._last_wait_check = now
        if self.settings["pause_when_not_ready"] and self.player.playing and self._needs_wait(t):
            self._waiting = True
            self.player.pause()
            self._update_status()

    def _maybe_resume(self) -> None:
        if self._waiting and not self._needs_wait(self.clock.position):
            self._waiting = False
            self.player.play()
            self._update_status()

    # -- worker events ------------------------------------------------------------------------
    def _on_worker_event(self, event: dict) -> None:
        if event.get("job") != self._job or self._book is None:
            return
        kind = event.get("type")
        if kind == "status":
            self._state = event["state"]
            self._status_message = event.get("message", "")
            self._update_status()
            self._maybe_resume()
        elif kind == "device":
            self._device = f"GPU · {event['name']}" if event["device"] == "cuda" else "CPU"
            self.deviceChanged.emit()
        elif kind == "progress":
            self._set_coverage([tuple(c) for c in event["coverage"]], event["covered"])
        elif kind == "region":
            self.track.apply_region(event["start"], event["end"], event["sentences"])
            self.clock.refresh()
            self._maybe_resume()
        elif kind == "translations":
            self.track.apply_translations(event["items"])
            self.clock.refresh()
            self._maybe_resume()
        elif kind == "error":
            log.error("worker: %s", event.get("detail") or event.get("message"))
            self.toast.emit(event.get("message", "Processing error"))

    def _set_coverage(self, coverage: list[tuple[float, float]], covered: float | None = None) -> None:
        self._coverage = coverage
        self._covered = covered if covered is not None else covered_seconds(coverage)
        self.progressChanged.emit()
        self._update_status()

    def _update_status(self) -> None:
        text = self._compose_status()
        if text != self._status_text:
            self._status_text = text
        self.statusChanged.emit()

    def _compose_status(self) -> str:
        if self._book is None:
            return ""
        if self._waiting:
            return "Waiting for subtitles…"
        if self._state == "loading":
            return "Loading models…"
        if self._state == "error":
            return f"Processing stopped · {self._status_message}"
        total = self._book.duration
        if self._state == "done" or self._covered >= total - 1:
            return f"All subtitles ready · {self.track.texts()} sentences"
        ahead = max(0.0, ready_until(self._coverage, self._position) - self._position)
        ahead_text = "under 1 min" if ahead < 60 else f"{int(ahead // 60)} min"
        return f"Transcribed {int(self._covered // 60)} of {max(1, round(total / 60))} min · {ahead_text} ahead"

    def _on_worker_crashed(self) -> None:
        now = time.monotonic()
        self._restarts = [t for t in self._restarts if now - t < 300] + [now]
        if len(self._restarts) > MAX_RESTARTS:
            self._state, self._status_message = "error", "the processing engine keeps stopping"
            self._update_status()
            return
        log.warning("worker process exited unexpectedly; restarting")
        self.worker.start()
        if self._book is not None:
            self._send_open(self.clock.position)

    # -- overlay ------------------------------------------------------------------------------
    @Slot()
    def toggleOverlay(self) -> None:
        self.overlay.toggleShown()

    @Slot()
    def toggleOverlayLock(self) -> None:
        if not self.overlay.shown:
            self.overlay.setShown(True)
        self.overlay.toggleLocked()

    # -- onboarding & models ------------------------------------------------------------------
    @Slot(str, str)
    def startModelDownloads(self, asr_id: str, mt_id: str) -> None:
        self.downloads.start([asr_id, mt_id])

    @Slot(str, str, str, str)
    def finishOnboarding(self, src: str, tgt: str, asr_id: str, mt_id: str) -> None:
        self.settings.update({"src_lang": src, "tgt_lang": tgt, "asr_model": asr_id, "mt_model": mt_id,
                              "onboarded": True})
        self.modelsChanged.emit()
        if self._deferred_open:
            path, self._deferred_open = self._deferred_open, None
            self.openBook(path)

    def _on_downloads_finished(self, ok: bool, error: str) -> None:
        self.modelsChanged.emit()
        if not ok:
            self.toast.emit(error)
        elif self._book is None and self._deferred_open and self.settings["onboarded"]:
            path, self._deferred_open = self._deferred_open, None
            self.openBook(path)

    # -- settings & hotkeys -------------------------------------------------------------------
    def _on_setting(self, key: str, value) -> None:
        if key in ("src_lang", "asr_model"):
            if self._book is not None and self._models_ready():
                self._reopen()
        elif key in ("tgt_lang", "mt_model"):
            if self._book is not None and self._cache is not None and self._models_ready():
                self.track.load(self._cache.subtitles(self.settings["tgt_lang"], self.settings["mt_model"]))
                self.clock.refresh()
                mt = models.get_model(self.settings["mt_model"])
                self.worker.send({"type": "set_target", "tgt": self.settings["tgt_lang"], "mt_model": mt.id,
                                  "mt_dir": str(models.model_dir(mt))})
        elif key == "appearance":
            self.theme.set_appearance(value)
        elif key == "volume":
            self.player.set_volume(value)
        elif key.startswith("hotkey_"):
            self._register_hotkeys()

    def _register_hotkeys(self) -> None:
        self.hotkeys.unregister_all()
        errors: dict[str, str] = {}
        for action in HOTKEY_ACTIONS:
            sequence = self.settings[f"hotkey_{action}"]
            if not sequence:
                continue
            if not self.hotkeys.supported:
                errors[action] = "Global hotkeys aren't available on this platform yet."
            elif not self.hotkeys.register(action, sequence):
                errors[action] = f"{sequence} is taken by another app. Choose another shortcut."
        self._hotkey_errors = errors
        self.hotkeyErrorsChanged.emit()

    @Slot()
    def suspendHotkeys(self) -> None:
        """While a shortcut is being recorded, so pressing it doesn't trigger the old action."""
        self.hotkeys.unregister_all()

    @Slot()
    def resumeHotkeys(self) -> None:
        self._register_hotkeys()

    # -- windows ------------------------------------------------------------------------------
    @Slot(QObject, result=bool)
    def registerWindow(self, window) -> bool:
        """Give a QML window the OS material (Mica / blur). Returns False if unavailable."""
        if window not in self._windows:
            self._windows.append(window)
        return native.apply_backdrop(int(window.winId()), "mica", self.theme.dark)

    def _restyle_windows(self) -> None:
        for window in self._windows:
            native.apply_backdrop(int(window.winId()), "mica", self.theme.dark)

    @Slot()
    def showPlayer(self) -> None:
        self.showPlayerRequested.emit()

    @Slot()
    def showLibrary(self) -> None:
        """Bring back the main window on the library, e.g. from the floating player."""
        self.library.refresh()
        self.showLibraryRequested.emit()

    @Slot()
    def showSettings(self) -> None:
        self.showSettingsRequested.emit("")

    @Slot()
    def quit(self) -> None:
        QApplication.quit()

    def _on_command(self, line: str) -> None:
        command, _, argument = line.partition(" ")
        if command == "open" and argument:
            self.showPlayer()
            self.openBook(argument)
            return
        {
            "play-pause": self.togglePlay,
            "back-sentence": self.backSentence,
            "toggle-overlay": self.toggleOverlay,
            "lock-overlay": self.toggleOverlayLock,
            "show": self.showPlayer,
            "quit": self.quit,
        }.get(command, lambda: log.warning("unknown command %r", line))()
