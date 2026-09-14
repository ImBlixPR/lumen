"""One signal for "the monitors changed".

Plugging in or unplugging a monitor, changing the main display, or changing a screen's
resolution or scaling all emit `changed`, once, after things settle. The subtitle overlay
and the floating player re-place themselves on it; without this they keep the coordinates
of the screen layout Lumen started with.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QScreen

SETTLE_MS = 400  # Windows reports a monitor change as a burst of screen updates


class ScreenWatcher(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._settle = QTimer(self, singleShot=True, interval=SETTLE_MS, timeout=self.changed.emit)
        app = QGuiApplication.instance()
        app.screenAdded.connect(self._watch)
        app.screenAdded.connect(self._poke)
        app.screenRemoved.connect(self._poke)
        app.primaryScreenChanged.connect(self._poke)
        for screen in app.screens():
            self._watch(screen)

    def _watch(self, screen: QScreen) -> None:
        screen.geometryChanged.connect(self._poke)
        screen.availableGeometryChanged.connect(self._poke)
        screen.logicalDotsPerInchChanged.connect(self._poke)

    def _poke(self, *_args) -> None:
        self._settle.start()


_watcher: ScreenWatcher | None = None


def screen_watcher() -> ScreenWatcher:
    global _watcher
    if _watcher is None:
        _watcher = ScreenWatcher(QGuiApplication.instance())
    return _watcher
