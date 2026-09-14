"""Platform-specific window behaviour behind one small interface.

This version implements Windows (`windows.py`). On other platforms every call is a safe
no-op: windows still get Qt's portable always-on-top, frameless and click-through flags,
just without OS blur or global hotkeys. See ARCHITECTURE.md for the macOS and Linux porting
checklist.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Signal

if sys.platform == "win32":
    from . import windows as _impl
else:
    _impl = None


def backdrop_kind() -> str:
    """What the OS can put behind a translucent window: 'mica', 'acrylic', 'blur' or 'none'."""
    return _impl.backdrop_kind() if _impl else "none"


def apply_backdrop(win_id: int, material: str, dark: bool) -> bool:
    """Put a real OS material ('mica' for main windows, 'acrylic' for the overlay) behind a window."""
    return _impl.apply_backdrop(win_id, material, dark) if _impl else False


def set_dark_frame(win_id: int, dark: bool) -> None:
    if _impl:
        _impl.set_dark_frame(win_id, dark)


def raise_topmost(win_id: int) -> None:
    """Re-assert always-on-top, for when another topmost window has covered us."""
    if _impl:
        _impl.raise_topmost(win_id)


def set_click_through(win_id: int, enabled: bool) -> None:
    if _impl:
        _impl.set_click_through(win_id, enabled)


def reduce_motion() -> bool:
    return _impl.reduce_motion() if _impl else False


class HotkeyManager(QObject):
    """System-wide hotkeys. `activated` carries the action name bound with `register`."""

    activated = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._backend = _impl.Win32Hotkeys(self.activated.emit) if _impl else None

    @property
    def supported(self) -> bool:
        return self._backend is not None

    def register(self, action: str, sequence: str) -> bool:
        """Bind a Qt-style sequence such as "Ctrl+Alt+Space". Returns False if the OS refused it."""
        return self._backend.register(action, sequence) if self._backend else False

    def unregister_all(self) -> None:
        if self._backend:
            self._backend.unregister_all()
