"""Start Lumen: `uv run python -m lumen [book] [--cmd play-pause] [--cpu]`."""

from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import sys
from logging.handlers import RotatingFileHandler


def _parse(argv: list[str]) -> argparse.Namespace:
    from .commands import COMMANDS

    parser = argparse.ArgumentParser(prog="lumen", description="Audiobooks with translated subtitles.")
    parser.add_argument("book", nargs="?", help="audiobook file to open")
    parser.add_argument("--cmd", choices=COMMANDS, help="send a command to the running Lumen and exit")
    parser.add_argument("--cpu", action="store_true", help="never use the GPU")
    parser.add_argument("--reset-onboarding", action="store_true", help="show first-run setup again")
    return parser.parse_args(argv)


def _setup_logging() -> None:
    from . import paths

    paths.ensure_dirs()
    handler = RotatingFileHandler(paths.log_dir() / "lumen.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


def _load_fonts() -> None:
    """Register the bundled fonts. Arabic-script text selects IBM Plex Sans Arabic explicitly
    (Theme.familyFor), because PySide6 has no binding for Qt's per-script fallback API."""
    from PySide6.QtGui import QFontDatabase

    from . import paths

    for font in sorted(paths.asset("fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font))


def _quit_on_ctrl_c(app) -> None:
    """Ctrl+C in the terminal that started Lumen quits it cleanly. Python only runs signal
    handlers between bytecodes, and Qt's event loop is native code, so a timer wakes it."""
    import signal

    from PySide6.QtCore import QTimer

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if hasattr(signal, "SIGBREAK"):  # Ctrl+Break, and closing the console window on Windows
        signal.signal(signal.SIGBREAK, lambda *_: app.quit())
    timer = QTimer(app, interval=250)
    timer.timeout.connect(lambda: None)
    timer.start()


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args.cpu:
        os.environ["LUMEN_FORCE_CPU"] = "1"  # inherited by the worker process
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    # Qt logs a line per fallback font it probes for non-Latin language names; it's noise.
    os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font.db=false")

    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterSingletonInstance
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME, paths
    from .commands import send_to_running

    if sys.platform == "win32":
        # With the default Direct3D 11 backend, DWM composites translucent Qt Quick windows over
        # white, so Mica never shows through. OpenGL windows get real DWM composition.
        from PySide6.QtQuick import QSGRendererInterface

        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    QQuickWindow.setDefaultAlphaBuffer(True)  # translucent windows for Mica / Acrylic
    app = QApplication(sys.argv[:1])

    if args.cmd or args.book:
        message = args.cmd or f"open {os.path.abspath(args.book)}"
        if send_to_running(message):
            return 0
        if args.cmd:
            print("Lumen isn't running.")
            return 1

    _setup_logging()
    from .app import AppController
    from .services.settings import SettingsStore
    from .services.tray import TrayService
    from .ui.icons import IconProvider, app_icon
    from .ui.theme import Theme

    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # closing the player keeps Lumen in the tray
    app.setWindowIcon(app_icon())
    _load_fonts()

    settings = SettingsStore()
    if args.reset_onboarding:
        settings.set("onboarded", False)
    theme = Theme()
    theme.set_appearance(settings["appearance"])
    app.setFont(app.font().__class__(theme.fontFamily))

    controller = AppController(settings, theme)
    # Register the singletons BEFORE creating the engine. With PySide6 6.11, registering them
    # after an engine exists corrupts that engine's type checks: every child item then fails
    # with 'Cannot assign object of type … to list property "data"; expected "QObject"'.
    qmlRegisterSingletonInstance(type(theme), "Lumen", 1, 0, "Theme", theme)
    qmlRegisterSingletonInstance(type(settings), "Lumen", 1, 0, "Settings", settings)
    qmlRegisterSingletonInstance(type(controller), "Lumen", 1, 0, "App", controller)
    # Not "Overlay": that name is taken by QtQuick.Controls' attached Overlay type.
    qmlRegisterSingletonInstance(type(controller.overlay), "Lumen", 1, 0, "SubtitleOverlay", controller.overlay)
    qmlRegisterSingletonInstance(type(controller.floating), "Lumen", 1, 0, "FloatingPlayer", controller.floating)
    qmlRegisterSingletonInstance(type(controller.library), "Lumen", 1, 0, "Library", controller.library)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconProvider())

    qml = paths.resources_dir() / "ui" / "qml"
    engine.load(QUrl.fromLocalFile(str(qml / "Main.qml")))
    if not engine.rootObjects():
        logging.getLogger("lumen").error("Main.qml failed to load")
        return 1

    overlay_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Overlay.qml")))
    overlay_window = overlay_component.create()
    if overlay_window is None:
        for error in overlay_component.errors():
            logging.getLogger("lumen").error(error.toString())
        return 1
    controller.overlay.attach(overlay_window)

    floating_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "FloatingPlayer.qml")))
    floating_window = floating_component.create()
    if floating_window is None:
        for error in floating_component.errors():
            logging.getLogger("lumen").error(error.toString())
        return 1
    controller.floating.attach(floating_window, engine.rootObjects()[0])

    tray = TrayService(controller, theme)
    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(tray.hide)
    _quit_on_ctrl_c(app)
    controller.start(open_path=os.path.abspath(args.book) if args.book else None)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
