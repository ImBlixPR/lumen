"""Where Lumen keeps settings, models, caches and its bundled resources.

On Windows:
  settings  %APPDATA%\\Lumen
  models    %LOCALAPPDATA%\\Lumen\\models
  cache     %LOCALAPPDATA%\\Lumen\\Cache\\books
Set LUMEN_HOME to keep everything in one folder instead (portable installs, tests).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_cache_path, user_config_path, user_data_path, user_log_path

from . import APP_NAME


def _home() -> Path | None:
    value = os.environ.get("LUMEN_HOME")
    return Path(value).expanduser() if value else None


def config_dir() -> Path:
    home = _home()
    return home / "config" if home else user_config_path(APP_NAME, appauthor=False, roaming=True)


def data_dir() -> Path:
    home = _home()
    return home / "data" if home else user_data_path(APP_NAME, appauthor=False)


def models_dir() -> Path:
    return data_dir() / "models"


def cache_dir() -> Path:
    home = _home()
    return home / "cache" if home else user_cache_path(APP_NAME, appauthor=False) / "books"


def log_dir() -> Path:
    home = _home()
    return home / "logs" if home else user_log_path(APP_NAME, appauthor=False)


def resources_dir() -> Path:
    """The `lumen` package folder, also inside a PyInstaller bundle."""
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) / "lumen" if bundle else Path(__file__).resolve().parent


def asset(*parts: str) -> Path:
    return resources_dir().joinpath("assets", *parts)


def ensure_dirs() -> None:
    for folder in (config_dir(), models_dir(), cache_dir(), log_dir()):
        folder.mkdir(parents=True, exist_ok=True)
