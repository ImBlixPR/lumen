"""Design tokens → a `Theme` singleton for QML (and a stylesheet for the tray menu).

Colors follow the OS light/dark setting live (or a forced appearance from Settings).
Durations collapse to 0 when the OS asks for reduced motion.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication

from ... import languages, native

_TOKENS_FILE = Path(__file__).with_name("tokens.json")
_RGBA = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)")
_ARABIC_SCRIPT = {"ar", "fa", "ur"}


@lru_cache(maxsize=1)
def load_tokens() -> dict:
    return json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))


def to_qcolor(value: str) -> QColor:
    match = _RGBA.fullmatch(value.strip())
    if match:
        r, g, b = (int(float(match.group(i))) for i in (1, 2, 3))
        a = float(match.group(4)) if match.group(4) is not None else 1.0
        return QColor(r, g, b, round(a * 255))
    return QColor(value)


def to_qml_color(value: str) -> str:
    return to_qcolor(value).name(QColor.NameFormat.HexArgb)


def _first_installed(candidates: list[str]) -> str:
    installed = set(QFontDatabase.families())
    return next((f for f in candidates if f in installed), candidates[-1])


class Theme(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._tokens = load_tokens()
        self._appearance = "system"
        self._reduce_motion = native.reduce_motion()
        fonts = self._tokens["font"]
        self._families = {key: _first_installed(stack) for key, stack in fonts.items()}
        self._colors: dict[str, str] = {}
        self._rebuild()

        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _scheme: self._rebuild(notify=True))
        self._motion_poll = QTimer(self, interval=5000, timeout=self._poll_reduce_motion)
        self._motion_poll.start()

    # -- state --------------------------------------------------------------------------------
    def _system_dark(self) -> bool:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def _is_dark(self) -> bool:
        if self._appearance == "system":
            return self._system_dark()
        return self._appearance == "dark"

    def _rebuild(self, notify: bool = False) -> None:
        palette = self._tokens["color"]["dark" if self._is_dark() else "light"]
        self._colors = {name: to_qml_color(value) for name, value in palette.items()}
        if notify:
            self.changed.emit()

    def _poll_reduce_motion(self) -> None:
        value = native.reduce_motion()
        if value != self._reduce_motion:
            self._reduce_motion = value
            self.changed.emit()

    def set_appearance(self, mode: str) -> None:
        if mode not in ("system", "light", "dark"):
            mode = "system"
        if mode != self._appearance:
            self._appearance = mode
            self._rebuild(notify=True)

    def color(self, name: str) -> QColor:
        return QColor(self._colors[name])

    # -- QML API ------------------------------------------------------------------------------
    @Property(bool, notify=changed)
    def dark(self) -> bool:
        return self._is_dark()

    @Property("QVariantMap", notify=changed)
    def c(self) -> dict:
        return self._colors

    @Property("QVariantMap", constant=True)
    def overlay(self) -> dict:
        tokens = dict(self._tokens["overlay"])
        for key in ("text", "backing", "border", "unlockedBorder", "textShadow"):
            tokens[key] = to_qml_color(tokens[key])
        return tokens

    @Property("QVariantMap", constant=True)
    def type(self) -> dict:
        return self._tokens["type"]

    @Property("QVariantMap", constant=True)
    def space(self) -> dict:
        return self._tokens["space"]

    @Property("QVariantMap", constant=True)
    def radius(self) -> dict:
        return self._tokens["radius"]

    @Property("QVariantMap", constant=True)
    def size(self) -> dict:
        return self._tokens["size"]

    @Property("QVariantMap", constant=True)
    def window(self) -> dict:
        return self._tokens["window"]

    @Property("QVariantMap", constant=True)
    def shadow(self) -> dict:
        return self._tokens["shadow"]

    @Property("QVariantMap", constant=True)
    def blur(self) -> dict:
        return self._tokens["blur"]

    @Property("QVariantMap", constant=True)
    def spring(self) -> dict:
        return self._tokens["motion"]["spring"]

    @Property(bool, notify=changed)
    def reduceMotion(self) -> bool:
        return self._reduce_motion

    def _duration(self, name: str) -> int:
        return 0 if self._reduce_motion else int(self._tokens["motion"][name])

    @Property(int, notify=changed)
    def fast(self) -> int:
        return self._duration("fast")

    @Property(int, notify=changed)
    def base(self) -> int:
        return self._duration("base")

    @Property(int, notify=changed)
    def slow(self) -> int:
        return self._duration("slow")

    @Property(str, constant=True)
    def fontFamily(self) -> str:
        return self._families["ui"]

    @Property(str, constant=True)
    def displayFamily(self) -> str:
        return self._families["display"]

    @Property(str, constant=True)
    def arabicFamily(self) -> str:
        return self._families["arabic"]

    @Property(str, constant=True)
    def monoFamily(self) -> str:
        return self._families["mono"]

    @Slot(str, result=str)
    def familyFor(self, lang: str) -> str:
        return self._families["arabic"] if lang in _ARABIC_SCRIPT else self._families["ui"]

    @Slot(str, result=bool)
    def isRtl(self, lang: str) -> bool:
        return languages.is_rtl(lang)

    # -- tray menu ----------------------------------------------------------------------------
    def menu_stylesheet(self) -> str:
        c = {k: to_qcolor(v) for k, v in self._tokens["color"]["dark" if self._is_dark() else "light"].items()}

        def rgba(color: QColor) -> str:
            return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"

        r = self._tokens["radius"]
        s = self._tokens["space"]
        t = self._tokens["type"]["body"]
        return f"""
            QMenu {{
                background: {rgba(c['bgElevated'])};
                border: 1px solid {rgba(c['hairline'])};
                border-radius: {r['md']}px;
                padding: {s['xxs'] + 2}px;
                font-family: "{self._families['ui']}";
                font-size: {t['size'] - 1}px;
                color: {rgba(c['textPrimary'])};
            }}
            QMenu::item {{
                padding: {s['xs'] - 2}px {s['md']}px {s['xs'] - 2}px {s['sm']}px;
                border-radius: {r['sm']}px;
                background: transparent;
            }}
            QMenu::item:selected {{ background: {rgba(c['accentFill'])}; color: {rgba(c['onAccent'])}; }}
            QMenu::item:disabled {{ color: {rgba(c['textDisabled'])}; }}
            QMenu::separator {{ height: 1px; background: {rgba(c['hairline'])}; margin: {s['xxs']}px {s['xs']}px; }}
            QMenu::icon {{ padding-left: {s['xs']}px; }}
        """
