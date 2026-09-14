"""Win32 / DWM integration through ctypes: materials, topmost, click-through, hotkeys, motion."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

# -- signatures ---------------------------------------------------------------------------------
LONG_PTR = ctypes.c_ssize_t
user32.GetWindowLongPtrW.restype = LONG_PTR
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]


class MARGINS(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int), ("top", ctypes.c_int), ("bottom", ctypes.c_int)]


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_FRAMECHANGED, SWP_NOOWNERZORDER = 0x1, 0x2, 0x10, 0x20, 0x200

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW, DWMSBT_TRANSIENTWINDOW = 2, 3

WCA_ACCENT_POLICY = 19
ACCENT_DISABLED, ACCENT_ENABLE_BLURBEHIND = 0, 3

SPI_GETCLIENTAREAANIMATION = 0x1042
WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000

_BUILD = sys.getwindowsversion().build


def _hwnd(win_id: int) -> wintypes.HWND:
    return wintypes.HWND(int(win_id))


def _dwm_int(hwnd: wintypes.HWND, attribute: int, value: int) -> bool:
    data = ctypes.c_int(value)
    return dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)) == 0


# -- materials ----------------------------------------------------------------------------------
def backdrop_kind() -> str:
    if _BUILD >= 22621:  # Windows 11 22H2: documented system backdrops
        return "mica"
    if _BUILD >= 17134:  # Windows 10 1803+: accent blur-behind
        return "blur"
    return "none"


def set_dark_frame(win_id: int, dark: bool) -> None:
    _dwm_int(_hwnd(win_id), DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)


def _accent_blur(hwnd: wintypes.HWND, enabled: bool, tint_abgr: int) -> bool:
    fn = getattr(user32, "SetWindowCompositionAttribute", None)
    if fn is None:
        return False
    policy = ACCENT_POLICY(ACCENT_ENABLE_BLURBEHIND if enabled else ACCENT_DISABLED, 2, tint_abgr, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(WCA_ACCENT_POLICY, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p),
                                       ctypes.sizeof(policy))
    return bool(fn(hwnd, ctypes.byref(data)))


def apply_backdrop(win_id: int, material: str, dark: bool) -> bool:
    """Mica (main windows) or Acrylic behind a translucent window. Requires Qt's OpenGL backend:
    with Direct3D 11 the window is composited over white and the material never shows."""
    hwnd = _hwnd(win_id)
    set_dark_frame(win_id, dark)
    kind = backdrop_kind()
    if kind == "mica":
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        backdrop = DWMSBT_TRANSIENTWINDOW if material == "acrylic" else DWMSBT_MAINWINDOW
        return _dwm_int(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, backdrop)
    if kind == "blur":
        tint = 0x40202020 if dark else 0x40F0F0F0  # ABGR: a light wash so text stays legible
        return _accent_blur(hwnd, True, tint)
    return False


# -- overlay behaviour --------------------------------------------------------------------------
def raise_topmost(win_id: int) -> None:
    user32.SetWindowPos(_hwnd(win_id), HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER)


def set_click_through(win_id: int, enabled: bool) -> None:
    """Toggle mouse transparency in place. Qt's flag would work too, but may rebuild the frame."""
    hwnd = _hwnd(win_id)
    style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    style = (style | WS_EX_TRANSPARENT | WS_EX_LAYERED) if enabled else (style & ~WS_EX_TRANSPARENT)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_NOOWNERZORDER)


def reduce_motion() -> bool:
    enabled = wintypes.BOOL(True)
    if not user32.SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0):
        return False
    return not enabled.value


# -- global hotkeys -----------------------------------------------------------------------------
_NAMED_KEYS = {
    "space": 0x20, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pgup": 0x21, "pageup": 0x21, "pgdown": 0x22, "pagedown": 0x22,
    "ins": 0x2D, "insert": 0x2D, "del": 0x2E, "delete": 0x2E, "backspace": 0x08, "tab": 0x09,
    "return": 0x0D, "enter": 0x0D, "esc": 0x1B, "escape": 0x1B,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA, "'": 0xDE, "[": 0xDB, "]": 0xDD, "\\": 0xDC,
    "-": 0xBD, "=": 0xBB, "`": 0xC0,
    "media play": 0xB3, "media pause": 0xB3, "toggle media play/pause": 0xB3,
    "media previous": 0xB1, "media next": 0xB0,
}
_MODIFIERS = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT,
              "meta": MOD_WIN, "win": MOD_WIN}


def parse_sequence(sequence: str) -> tuple[int, int] | None:
    """"Ctrl+Alt+Space" → (modifiers, virtual key). Handles "+" as the key ("Ctrl++")."""
    text = sequence.strip()
    if not text:
        return None
    parts = text.split("+")
    if text.endswith("++"):
        parts = [*parts[:-2], "+"]
    *mods, key = [p.strip() for p in parts]
    modifiers = 0
    for mod in mods:
        flag = _MODIFIERS.get(mod.lower())
        if flag is None:
            return None
        modifiers |= flag
    lower = key.lower()
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif lower in _NAMED_KEYS:
        vk = _NAMED_KEYS[lower]
    elif key == "+":
        vk = 0xBB
    elif lower.startswith("f") and lower[1:].isdigit() and 1 <= int(lower[1:]) <= 24:
        vk = 0x70 + int(lower[1:]) - 1
    else:
        return None
    return modifiers, vk


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey: Callable[[int], None]):
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self._on_hotkey(int(msg.wParam))
                return True, 0
        return False, 0


class Win32Hotkeys:
    """RegisterHotKey-based hotkeys: no keyboard hook, no special permissions."""

    def __init__(self, emit: Callable[[str], None]):
        self._emit = emit
        self._actions: dict[int, str] = {}
        self._next_id = 0xB000
        self._filter = _HotkeyFilter(self._dispatch)
        QCoreApplication.instance().installNativeEventFilter(self._filter)

    def _dispatch(self, hotkey_id: int) -> None:
        action = self._actions.get(hotkey_id)
        if action:
            self._emit(action)

    def register(self, action: str, sequence: str) -> bool:
        parsed = parse_sequence(sequence)
        if parsed is None:
            return False
        modifiers, vk = parsed
        self._next_id += 1
        if not user32.RegisterHotKey(None, self._next_id, modifiers | MOD_NOREPEAT, vk):
            return False  # usually: another app already owns this combination
        self._actions[self._next_id] = action
        return True

    def unregister_all(self) -> None:
        for hotkey_id in self._actions:
            user32.UnregisterHotKey(None, hotkey_id)
        self._actions.clear()
