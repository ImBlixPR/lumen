"""The subtitle overlay window: transparent, frameless, always on top, click-through.

Locked (the default), the window ignores the mouse, so it never blocks the apps beneath it.
Unlocked, you can drag it anywhere and pull its sides to resize. The chosen place is
remembered as a bottom-centre anchor, so larger fonts grow the subtitle upward, away from
the taskbar.

The glass behind the text is the tinted pill drawn in QML, not an OS blur. On Windows, DWM
Acrylic can't be clipped to the pill on a layered (click-through) window: it fills the
whole window rectangle as an opaque slab. The pill's tint is tuned to keep text at 4.5:1
over any background instead.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QPoint, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickWindow

from .. import native
from .screens import screen_watcher
from .settings import SettingsStore

LINES = 3
EDGE_MARGIN = 8  # transparent margin around the pill, logical px
MIN_WIDTH = 360


class OverlayController(QObject):
    textChanged = Signal()
    lockedChanged = Signal()
    shownChanged = Signal()
    anchorTopChanged = Signal()

    def __init__(self, settings: SettingsStore, theme, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._theme = theme
        self._window: QQuickWindow | None = None
        self._win_id = 0
        self._text = ""
        self._locked = True
        self._placing = False
        self._saving = False
        self._top_timer = QTimer(self, interval=2000, timeout=self._keep_on_top)
        self._save_timer = QTimer(self, singleShot=True, interval=500, timeout=self._save_geometry)
        settings.changed.connect(self._on_setting)

    # -- QML API ------------------------------------------------------------------------------
    @Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @Property(bool, notify=lockedChanged)
    def locked(self) -> bool:
        return self._locked

    @Property(bool, notify=shownChanged)
    def shown(self) -> bool:
        return bool(self._settings["overlay_visible"])

    @Property(bool, notify=anchorTopChanged)
    def anchorTop(self) -> bool:
        return self._settings["overlay_position"] == "top"

    @Slot(bool)
    def setLocked(self, locked: bool) -> None:
        if locked == self._locked:
            return
        self._locked = locked
        if self._window is not None:
            self._window.setFlag(Qt.WindowType.WindowTransparentForInput, locked)
            if self._win_id:
                native.set_click_through(self._win_id, locked)
        self.lockedChanged.emit()

    @Slot()
    def toggleLocked(self) -> None:
        self.setLocked(not self._locked)

    @Slot(bool)
    def setShown(self, shown: bool) -> None:
        self._settings.set("overlay_visible", shown)

    @Slot()
    def toggleShown(self) -> None:
        self.setShown(not self.shown)

    @Slot(str)
    def setPosition(self, preset: str) -> None:
        self._settings.set("overlay_position", preset)

    @Slot()
    def startMove(self) -> None:
        if self._window is not None and not self._locked:
            self._window.startSystemMove()

    @Slot(int)
    def startResize(self, edge: int) -> None:
        if self._window is not None and not self._locked:
            self._window.startSystemResize(Qt.Edge(edge))

    # -- lifecycle ----------------------------------------------------------------------------
    def attach(self, window: QQuickWindow) -> None:
        self._window = window
        window.setFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowTransparentForInput
        )
        window.setColor(Qt.GlobalColor.transparent)
        window.xChanged.connect(self._on_moved)
        window.yChanged.connect(self._on_moved)
        window.widthChanged.connect(self._on_moved)
        screen_watcher().changed.connect(self._on_screens_changed)
        self._place()
        if self.shown:
            self._show()

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.textChanged.emit()

    def _show(self) -> None:
        window = self._window
        window.show()
        self._win_id = int(window.winId())
        native.set_click_through(self._win_id, self._locked)
        native.raise_topmost(self._win_id)
        self._top_timer.start()

    def _hide(self) -> None:
        if self._window is not None:
            self._window.hide()
        self._top_timer.stop()

    def _on_screens_changed(self) -> None:
        # A monitor was plugged in or unplugged, or changed size or scaling. If the subtitle was
        # dragged onto a screen that's gone it returns to the main screen, and it goes back when
        # that screen does.
        self._place()
        if self._win_id and self.shown:
            native.raise_topmost(self._win_id)

    def _keep_on_top(self) -> None:
        if self._win_id and self._window is not None and self._window.isVisible():
            native.raise_topmost(self._win_id)

    # -- geometry -----------------------------------------------------------------------------
    def window_height(self) -> int:
        overlay_type = self._theme.type["overlay"]
        line = self._settings["overlay_font_size"] * overlay_type["line"] / overlay_type["size"]
        padding = self._theme.space["sm"]
        return int(LINES * line + 2 * padding + 2 * EDGE_MARGIN + 2)

    def _place(self) -> None:
        window = self._window
        if window is None:
            return
        s = self._settings
        height = self.window_height()
        position = s["overlay_position"]
        anchor = QPoint(s["overlay_x"], s["overlay_y"])
        screen = QGuiApplication.screenAt(anchor) if position == "custom" else None
        if screen is None:
            screen = QGuiApplication.primaryScreen()
            if position == "custom":
                position = "bottom"
        area = screen.availableGeometry()
        width = max(MIN_WIDTH, min(s["overlay_width"], area.width()))
        if position == "custom":
            x, y = anchor.x() - width // 2, anchor.y() - height
        elif position == "top":
            x, y = area.center().x() - width // 2, area.top() + int(area.height() * 0.05)
        else:
            x, y = area.center().x() - width // 2, area.bottom() - height - int(area.height() * 0.07)
        self._placing = True
        window.setGeometry(x, y, width, height)
        self._placing = False
        self.anchorTopChanged.emit()

    def _on_moved(self, *_args) -> None:
        if not self._placing and not self._locked:
            self._save_timer.start()

    def _save_geometry(self) -> None:
        window = self._window
        self._saving = True
        self._settings.update({
            "overlay_position": "custom",
            "overlay_x": window.x() + window.width() // 2,
            "overlay_y": window.y() + window.height(),
            "overlay_width": window.width(),
        })
        self._saving = False

    def _on_setting(self, key: str, _value) -> None:
        if key == "overlay_visible":
            if self._window is not None:
                self._show() if self.shown else self._hide()
            self.shownChanged.emit()
        elif key in ("overlay_font_size", "overlay_position", "overlay_x", "overlay_y", "overlay_width"):
            if not self._saving:
                self._place()
