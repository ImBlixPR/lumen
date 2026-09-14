"""The floating orbital player.

Once a book is playing and the library window is put away, the book floats at the right edge
of the screen as a glass disc with its progress arc and three orbiting controls. It has no
frame and no background.

It docks to the right edge, a third of the way down, rather than the top-right corner. That
corner is where every maximized window keeps its minimize, maximize and close buttons. The
default spot stays below the top 64 px (title bars, browser tabs), and you can drag the disc
up or down the edge; the spot is remembered as the `floating_y` setting.

It is only a presentation layer. Every value comes from AppController (the same
PlayerService, book and settings the library window uses), and every button calls back into
AppController. There is no second audio system.

States (`state` property; QML animates between them):
  hidden     fully off-screen (entrance / exit)
  collapsed  about a third of the disc peeks out of the right edge; no controls
  peek       the cursor is near: more of the disc slides in
  expanded   the cursor is on it: full disc, arc, timestamp, controls and info

Cursor proximity is watched by polling the global cursor position, not with an invisible
hover zone, so the edge never swallows clicks meant for the apps underneath. The window's
mask is clipped to the visible disc (and, when expanded, the controls), so clicks on its
transparent parts pass through.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import Property, QMetaObject, QObject, QRect, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication, QRegion
from PySide6.QtQuick import QQuickWindow

from .. import native
from .screens import screen_watcher

# Angles are clockwise from 12 o'clock. The controls orbit the side that faces into the screen.
SETTINGS_ANGLE = 322.0
LIBRARY_ANGLE = 270.0
PLAY_ANGLE = 218.0
TIMESTAMP_ANGLE = 0.0

TITLE_BAR_ZONE = 64  # px at the top of the screen kept clear by default (title bars, tabs)
DEFAULT_CENTER = 0.32  # default disc height, as a fraction of the screen height

PLAY_SIZE = 54
BUTTON_SIZE = 40
POPOVER_WIDTH = 280
POPOVER_HEIGHT = 244
INFO_WIDTH = 248
INFO_HEIGHT = 64

POLL_MS = 50
COLLAPSE_DELAY_MS = 900
SETTLE_MS = 460  # longest state animation; the mask shrinks only after it


@dataclass(frozen=True)
class OrbitLayout:
    """Geometry of the floating player in window coordinates (logical pixels)."""

    width: int
    height: int
    disc: int
    arc_radius: float
    orbit_radius: float
    expanded: tuple[float, float]
    peek: tuple[float, float]
    collapsed: tuple[float, float]
    hidden: tuple[float, float]

    def center(self, state: str) -> tuple[float, float]:
        return {"expanded": self.expanded, "peek": self.peek, "collapsed": self.collapsed}.get(state, self.hidden)

    def orbit_point(self, angle: float, radius: float | None = None) -> tuple[float, float]:
        cx, cy = self.expanded
        r = self.orbit_radius if radius is None else radius
        a = math.radians(angle)
        return cx + r * math.sin(a), cy - r * math.cos(a)

    def info_rect(self) -> QRect:
        px, py = self.orbit_point(PLAY_ANGLE)
        x = max(8.0, min(px - INFO_WIDTH / 2, self.width - INFO_WIDTH - 8.0))
        return QRect(round(x), round(py + PLAY_SIZE / 2 + 12), INFO_WIDTH, INFO_HEIGHT)

    def popover_rect(self) -> QRect:
        sx, sy = self.orbit_point(SETTINGS_ANGLE)
        x = sx - BUTTON_SIZE / 2 - 14 - POPOVER_WIDTH
        y = max(8.0, sy - 28)
        return QRect(round(max(8.0, x)), round(y), POPOVER_WIDTH, POPOVER_HEIGHT)

    def to_qml(self) -> dict:
        def point(p: tuple[float, float]) -> list[float]:
            return [p[0], p[1]]

        info, pop = self.info_rect(), self.popover_rect()
        return {
            "width": self.width, "height": self.height, "disc": self.disc,
            "arcRadius": self.arc_radius, "orbitRadius": self.orbit_radius,
            "centers": {s: point(self.center(s)) for s in ("hidden", "collapsed", "peek", "expanded")},
            "play": point(self.orbit_point(PLAY_ANGLE)),
            "library": point(self.orbit_point(LIBRARY_ANGLE)),
            "settings": point(self.orbit_point(SETTINGS_ANGLE)),
            "timestamp": point(self.orbit_point(TIMESTAMP_ANGLE, self.arc_radius + 20)),
            "playSize": PLAY_SIZE, "buttonSize": BUTTON_SIZE,
            "info": [info.x(), info.y(), info.width(), info.height()],
            "popover": [pop.x(), pop.y(), pop.width(), pop.height()],
        }


def orbit_layout(screen_w: int, screen_h: int) -> OrbitLayout:
    """Responsive layout for a player docked to the right edge of the screen.

    The disc scales with the screen (clamped to 120–200 px) and slides horizontally between
    states: its height never changes, so it glides straight out of the edge.
    """
    disc = round(min(200.0, max(120.0, min(screen_h * 0.15, screen_w * 0.12))))
    r = disc / 2
    arc = r + 12
    orbit = arc + 38
    right_margin = arc + 22

    def left_of_center(angle: float, extra: float) -> float:
        return -orbit * math.sin(math.radians(angle)) + extra

    width = math.ceil(right_margin + max(
        left_of_center(LIBRARY_ANGLE, BUTTON_SIZE / 2 + 8),
        left_of_center(SETTINGS_ANGLE, BUTTON_SIZE / 2 + 14 + POPOVER_WIDTH + 12),
        left_of_center(PLAY_ANGLE, INFO_WIDTH / 2 + 8),
    ))
    settings_rise = orbit * math.cos(math.radians(SETTINGS_ANGLE))
    cy = math.ceil(max(arc + 20 + 18, settings_rise + BUTTON_SIZE / 2 + 8))
    below = orbit * abs(math.cos(math.radians(PLAY_ANGLE))) + PLAY_SIZE / 2 + 12 + INFO_HEIGHT + 12
    popover_bottom = max(8.0, cy - settings_rise - 28) + POPOVER_HEIGHT + 12
    height = math.ceil(max(cy + below, popover_bottom))
    return OrbitLayout(
        width=width, height=height, disc=disc, arc_radius=arc, orbit_radius=orbit,
        expanded=(width - right_margin, cy),
        peek=(width - 0.25 * r, cy),       # about two thirds of the disc shows
        collapsed=(width + 0.3 * r, cy),   # a crescent: about a third of the disc shows
        hidden=(width + arc + 48, cy),
    )


def window_top(area_top: int, area_height: int, height: int, center_y: float, fraction: float) -> int:
    """Top of the player window on a screen area.

    `fraction` (0…1) is where the user dragged the player along the edge. A negative value means
    the default: the disc a third of the way down, and the whole player below the title-bar zone.
    """
    lowest = area_top + max(0, area_height - height)
    if fraction < 0:
        top = max(area_top + area_height * DEFAULT_CENTER - center_y, area_top + TITLE_BAR_ZONE)
    else:
        top = area_top + min(1.0, fraction) * (lowest - area_top)
    return round(min(max(top, area_top), lowest))


class FloatingPlayerController(QObject):
    stateChanged = Signal()
    layoutChanged = Signal()
    shownChanged = Signal()
    settingsOpenChanged = Signal()

    def __init__(self, app_controller, parent: QObject | None = None):
        super().__init__(parent)
        self._app = app_controller
        self._window: QQuickWindow | None = None
        self._library = None
        self._state = "hidden"
        self._shown = False
        self._settings_open = False
        self._drag: tuple[float, int] | None = None  # (press global y, window top at press)
        self._layout = orbit_layout(1920, 1080)
        self._poll = QTimer(self, interval=POLL_MS, timeout=self._track_cursor)
        self._collapse = QTimer(self, singleShot=True, interval=COLLAPSE_DELAY_MS,
                                timeout=lambda: self._set_state("collapsed"))
        self._settle = QTimer(self, singleShot=True, interval=SETTLE_MS, timeout=self._after_settle)
        self._top = QTimer(self, interval=2000, timeout=self._keep_on_top)
        app_controller.playingChanged.connect(self._on_playing)
        app_controller.bookChanged.connect(self._sync_visibility)

    # -- QML API ------------------------------------------------------------------------------
    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(bool, notify=shownChanged)
    def shown(self) -> bool:
        return self._shown

    @Property(bool, notify=settingsOpenChanged)
    def settingsOpen(self) -> bool:
        return self._settings_open

    @Property("QVariantMap", notify=layoutChanged)
    def geometry(self) -> dict:
        return self._layout.to_qml()

    @Slot()
    def playPause(self) -> None:
        self._app.togglePlay()

    @Slot()
    def openLibrary(self) -> None:
        self.closeSettings()
        self._app.showLibrary()  # the main window's library; playback carries on

    @Slot()
    def toggleSettings(self) -> None:
        self._settings_open = not self._settings_open
        self.settingsOpenChanged.emit()
        self._apply_mask()

    @Slot()
    def closeSettings(self) -> None:
        if self._settings_open:
            self._settings_open = False
            self.settingsOpenChanged.emit()
            self._apply_mask()

    @Slot(float)
    def seekFraction(self, fraction: float) -> None:
        duration = self._app.duration
        if duration > 0:
            self._app.seek(max(0.0, min(1.0, fraction)) * duration)

    @Slot(float)
    def beginDrag(self, global_y: float) -> None:
        """Press on the disc: it may become a drag up or down the edge."""
        if self._window is not None:
            self._drag = (global_y, self._window.y())
            self._collapse.stop()

    @Slot(float)
    def dragTo(self, global_y: float) -> None:
        if self._drag is None or self._window is None:
            return
        area = QGuiApplication.primaryScreen().availableGeometry()
        start_y, start_top = self._drag
        lowest = area.y() + max(0, area.height() - self._layout.height)
        self._window.setY(round(min(max(start_top + global_y - start_y, area.y()), lowest)))

    @Slot()
    def endDrag(self) -> None:
        if self._drag is None or self._window is None:
            return
        self._drag = None
        area = QGuiApplication.primaryScreen().availableGeometry()
        span = max(0, area.height() - self._layout.height)
        fraction = (self._window.y() - area.y()) / span if span else 0.0
        self._app.settings.set("floating_y", round(fraction, 4))

    @Slot()
    def reveal(self) -> None:
        """Pointer or keyboard activity on the player itself (a backup to cursor polling)."""
        if self._shown:
            self._collapse.stop()
            self._set_state("expanded")

    # -- lifecycle ----------------------------------------------------------------------------
    def attach(self, window: QQuickWindow, library_window) -> None:
        self._window = window
        self._library = library_window
        window.setFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )
        window.setColor(Qt.GlobalColor.transparent)
        library_window.visibleChanged.connect(lambda _v: self._sync_visibility())
        screen_watcher().changed.connect(self._place)  # monitors plugged in, unplugged, rescaled
        self._place()
        self._sync_visibility()

    def _place(self) -> None:
        if self._window is None:
            return
        area = QGuiApplication.primaryScreen().availableGeometry()
        self._layout = orbit_layout(area.width(), area.height())
        w, h = self._layout.width, self._layout.height
        top = window_top(area.y(), area.height(), h, self._layout.expanded[1], self._app.settings["floating_y"])
        self._window.setGeometry(area.x() + area.width() - w, top, w, h)  # docked to the right edge
        self.layoutChanged.emit()
        self._apply_mask()
        if self._window.isVisible():
            native.raise_topmost(int(self._window.winId()))

    def _sync_visibility(self) -> None:
        should_show = bool(self._app.hasBook) and self._library is not None and not self._library.isVisible()
        if should_show and not self._shown:
            self._show()
        elif not should_show and self._shown:
            self._hide()

    def _show(self) -> None:
        self._shown = True
        self.shownChanged.emit()
        self._state = "hidden"
        self.stateChanged.emit()
        self._window.show()
        native.raise_topmost(int(self._window.winId()))
        QTimer.singleShot(40, lambda: self._set_state("collapsed"))  # slide in from the corner
        self._poll.start()
        self._top.start()

    def _hide(self) -> None:
        self._shown = False
        self.shownChanged.emit()
        self.closeSettings()
        self._poll.stop()
        self._top.stop()
        self._collapse.stop()
        self._set_state("hidden")  # slides out; the window hides once it has settled

    def _on_playing(self, *_args) -> None:
        # Playback started from the library window: put the library away, float the player.
        if self._app.playing and self._library is not None and self._library.isVisible() and self._app.hasBook:
            QMetaObject.invokeMethod(self._library, "hideToFloating")

    # -- state & cursor -----------------------------------------------------------------------
    def _set_state(self, state: str) -> None:
        if state == self._state:
            return
        growing = state in ("peek", "expanded")
        self._state = state
        self.stateChanged.emit()
        if state != "expanded":
            self.closeSettings()
        if growing:
            self._apply_mask()  # enlarge the hit area before the disc moves into it
        self._settle.start()

    def _after_settle(self) -> None:
        self._apply_mask()
        if self._state == "hidden" and not self._shown and self._window is not None:
            self._window.hide()

    def _schedule_collapse(self) -> None:
        if not self._collapse.isActive():
            self._collapse.start()

    def _track_cursor(self) -> None:
        if not self._shown or self._window is None or self._state == "hidden" or self._drag is not None:
            return
        pos = self._window.mapFromGlobal(QCursor.pos())
        x, y = pos.x(), pos.y()
        layout = self._layout
        r = layout.disc / 2

        def distance(point: tuple[float, float]) -> float:
            return math.hypot(x - point[0], y - point[1])

        if self._state == "collapsed":
            if distance(layout.collapsed) < r * 1.7:
                self._set_state("peek")
        elif self._state == "peek":
            d = distance(layout.peek)
            if d < r * 1.02:
                self._collapse.stop()
                self._set_state("expanded")
            elif d > r * 2.2:
                self._schedule_collapse()
            else:
                self._collapse.stop()
        else:  # expanded
            inside = (
                distance(layout.expanded) < layout.orbit_radius + BUTTON_SIZE
                or layout.info_rect().contains(round(x), round(y))
                or (self._settings_open and layout.popover_rect().adjusted(-16, -16, 16, 16).contains(round(x), round(y)))
            )
            if inside:
                self._collapse.stop()
            else:
                self._schedule_collapse()

    def _mask_region(self) -> QRegion:
        layout = self._layout
        cx, cy = layout.center(self._state)
        if self._state == "expanded":
            radius = layout.orbit_radius + PLAY_SIZE / 2 + 8
        elif self._state == "peek":
            radius = layout.arc_radius + 14
        else:
            radius = layout.arc_radius + 8
        circle = QRect(round(cx - radius), round(cy - radius), round(radius * 2), round(radius * 2))
        region = QRegion(circle, QRegion.RegionType.Ellipse)
        if self._state == "expanded":
            region = region.united(QRegion(layout.info_rect()))
            tx, ty = layout.orbit_point(TIMESTAMP_ANGLE, layout.arc_radius + 20)
            region = region.united(QRegion(QRect(round(tx - 60), round(ty - 14), 120, 28)))
            if self._settings_open:
                region = region.united(QRegion(layout.popover_rect().adjusted(-12, -12, 12, 12)))
        return region.intersected(QRegion(QRect(0, 0, layout.width, layout.height)))

    def _apply_mask(self) -> None:
        if self._window is not None:
            self._window.setMask(self._mask_region())

    def _keep_on_top(self) -> None:
        if self._window is not None and self._window.isVisible():
            native.raise_topmost(int(self._window.winId()))
