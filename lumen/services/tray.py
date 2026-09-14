"""Notification-area icon and menu, styled from the design tokens."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..ui.icons import app_icon, tinted_icon


class TrayService(QObject):
    def __init__(self, controller, theme, parent: QObject | None = None):
        super().__init__(parent)
        self._app = controller
        self._theme = theme
        self._menu = QMenu()
        # Translucent + frameless so the stylesheet's rounded corners aren't drawn on a square.
        self._menu.setWindowFlags(
            self._menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )
        self._menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._tray = QSystemTrayIcon(app_icon(), self)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

        self._play = self._action("Play", "play", controller.togglePlay)
        self._back = self._action("Back one sentence", "skip-back", controller.backSentence)
        self._menu.addSeparator()
        self._show_subs = self._action("Show subtitles", "captions", controller.toggleOverlay, checkable=True)
        self._lock = self._action("Unlock subtitles to move", "lock-open", controller.toggleOverlayLock, checkable=True)
        self._menu.addSeparator()
        self._action("Open player", "headphones", controller.showPlayer)
        self._action("Open book…", "folder-open", controller.openBookDialog)
        self._action("Settings…", "settings", controller.showSettings)
        self._menu.addSeparator()
        self._action("Quit Lumen", "power", controller.quit)

        controller.playingChanged.connect(self._refresh)
        controller.bookChanged.connect(self._refresh)
        controller.overlay.shownChanged.connect(self._refresh)
        controller.overlay.lockedChanged.connect(self._refresh)
        theme.changed.connect(self._restyle)
        self._restyle()
        self._refresh()
        self._tray.show()

    def _action(self, text: str, icon: str, slot, checkable: bool = False) -> QAction:
        action = QAction(text, self._menu)
        action.setData(icon)
        action.setCheckable(checkable)
        action.triggered.connect(lambda _checked=False: slot())
        self._menu.addAction(action)
        return action

    def _restyle(self) -> None:
        self._menu.setStyleSheet(self._theme.menu_stylesheet())
        color = self._theme.color("textPrimary")
        for action in self._menu.actions():
            if action.data():
                action.setIcon(tinted_icon(action.data(), color, 32))

    def _refresh(self) -> None:
        app = self._app
        playing = app.player.playing
        self._play.setText("Pause" if playing else "Play")
        self._play.setData("pause" if playing else "play")
        self._play.setIcon(tinted_icon(self._play.data(), self._theme.color("textPrimary"), 32))
        has_book = app.hasBook
        self._play.setEnabled(has_book)
        self._back.setEnabled(has_book)
        self._show_subs.setChecked(app.overlay.shown)
        self._lock.setChecked(not app.overlay.locked)
        title = app.book.get("title") if has_book else ""
        self._tray.setToolTip(f"Lumen · {title}" if title else "Lumen")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._app.showPlayer()

    def hide(self) -> None:
        self._tray.hide()
