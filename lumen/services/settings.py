"""Persistent settings, exposed to QML as one live map.

QML reads `Settings.values.overlay_font_size` (bindings update on every change) and writes
with `Settings.set("overlay_font_size", 32)`. Values are coerced to the type of their
default, then saved atomically (debounced) as JSON in the config folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from .. import paths

DEFAULTS: dict[str, Any] = {
    "onboarded": False,
    "src_lang": "fr",
    "tgt_lang": "ar",
    "asr_model": "",
    "mt_model": "nllb-600m",
    "appearance": "system",
    # Not Ctrl+Alt+Space: other apps commonly claim it globally (it was taken on the dev machine).
    "hotkey_play_pause": "Ctrl+Alt+P",
    "hotkey_back_sentence": "Ctrl+Alt+Left",
    "hotkey_toggle_overlay": "Ctrl+Alt+H",
    "hotkey_lock_overlay": "Ctrl+Alt+L",
    "overlay_visible": True,
    "overlay_font_size": 28,
    "overlay_text_color": "#FFFFFF",
    "overlay_backing_opacity": 0.62,
    "overlay_position": "bottom",  # bottom | top | custom
    "overlay_x": -1,
    "overlay_y": -1,
    "overlay_width": 960,
    "playback_rate": 1.0,
    "volume": 1.0,
    "pause_when_not_ready": False,
    "close_to_tray": False,  # closing the main window quits; True keeps Lumen in the tray
    "floating_y": -1.0,  # floating player's spot along the right edge (0…1); -1 = default
    "last_book": "",
}

HOTKEY_ACTIONS = ("play_pause", "back_sentence", "toggle_overlay", "lock_overlay")


def _coerce(key: str, value: Any) -> Any:
    default = DEFAULTS[key]
    try:
        if isinstance(default, bool):
            return bool(value)
        if isinstance(default, int):
            return int(round(float(value)))
        if isinstance(default, float):
            return float(value)
        return "" if value is None else str(value)
    except (TypeError, ValueError):
        return default


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


class SettingsStore(QObject):
    valuesChanged = Signal()
    changed = Signal(str, "QVariant")  # key, new value

    def __init__(self, folder: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        folder = folder or paths.config_dir()
        self._path = folder / "settings.json"
        self._positions_path = folder / "positions.json"
        stored = _read_json(self._path)
        self._values = {k: _coerce(k, stored.get(k, v)) for k, v in DEFAULTS.items()}
        self._positions: dict[str, float] = {
            k: float(v) for k, v in _read_json(self._positions_path).items() if isinstance(v, (int, float))
        }
        self._names_path = folder / "names.json"
        self._names: dict[str, str] = {
            k: v for k, v in _read_json(self._names_path).items() if isinstance(v, str)
        }
        self._save_timer = QTimer(self, singleShot=True, interval=300, timeout=self.flush)

    @Property("QVariantMap", notify=valuesChanged)
    def values(self) -> dict:
        return self._values

    @Slot(str, result="QVariant")
    def get(self, key: str) -> Any:
        return self._values[key]

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    @Slot(str, "QVariant")
    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS:
            raise KeyError(key)
        value = _coerce(key, value)
        if self._values.get(key) == value:
            return
        self._values = {**self._values, key: value}  # new dict so QML sees a changed map
        self.valuesChanged.emit()
        self.changed.emit(key, value)
        self._save_timer.start()

    @Slot(str)
    def reset(self, key: str) -> None:
        self.set(key, DEFAULTS[key])

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    # -- per-book resume positions ------------------------------------------------------------
    def position(self, book: str) -> float:
        return self._positions.get(book, 0.0)

    def save_position(self, book: str, seconds: float) -> None:
        self._positions[book] = round(float(seconds), 2)
        self._save_timer.start()

    # -- per-book character names (a Whisper spelling hint) -----------------------------------
    def book_names(self, book: str) -> str:
        return self._names.get(book, "")

    def set_book_names(self, book: str, names: str) -> None:
        if names:
            self._names[book] = names
        else:
            self._names.pop(book, None)
        self._save_timer.start()

    @Slot()
    def flush(self) -> None:
        self._save_timer.stop()
        _write_json(self._path, self._values)
        _write_json(self._positions_path, self._positions)
        _write_json(self._names_path, self._names)
