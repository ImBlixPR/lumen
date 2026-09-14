# PyInstaller build for Windows:  uv run pyinstaller lumen.spec   →  dist\Lumen\Lumen.exe
# Models are not bundled; the app downloads them on first run into %LOCALAPPDATA%\Lumen\models.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

root = Path(SPECPATH)

datas = [
    (str(root / "lumen" / "ui" / "qml"), "lumen/ui/qml"),
    (str(root / "lumen" / "ui" / "theme" / "tokens.json"), "lumen/ui/theme"),
    (str(root / "lumen" / "assets"), "lumen/assets"),
]
datas += collect_data_files("faster_whisper")  # Silero VAD model

binaries = collect_dynamic_libs("ctranslate2")
for cuda_package in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc"):
    try:
        binaries += collect_dynamic_libs(cuda_package)
    except Exception:
        pass  # CPU-only environment: the build simply has no GPU support

a = Analysis(
    [str(root / "scripts" / "lumen_launcher.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2", "PySide6.QtMultimedia",
        "PySide6.QtSvg", "PySide6.QtNetwork", "lumen.pipeline.worker",
    ],
    excludes=["tkinter", "torch", "transformers", "matplotlib"],
    noarchive=False,
)
# Qt parts Lumen never uses (a web browser engine, PDF, 3D, charts, designer…): ~250 MB.
UNUSED_QT = (
    "webengine", "qt6pdf", "qtpdf", "qt63d", "qt3d", "quick3d", "qt6designer", "qtdesigner",
    "qt6charts", "qtcharts", "datavisualization", "qtdatavis", "qt6graphs", "qtgraphs",
    "qt6location", "qtlocation", "qt6scxml", "qtscxml", "virtualkeyboard", "qt6sensors",
    "qt6bluetooth", "qt6nfc", "qt6serialport", "texttospeech", "spatialaudio", "qt6webview",
    "qtwebview", "remoteobjects", "httpserver",
)


def _needed(entry) -> bool:
    names = " ".join(str(part).lower().replace("\\", "/") for part in entry[:2])
    return not any(unused in names for unused in UNUSED_QT)


a.binaries = [b for b in a.binaries if _needed(b)]
a.datas = [d for d in a.datas if _needed(d)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lumen",
    console=False,
    icon=str(root / "lumen" / "assets" / "lumen.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="Lumen")
