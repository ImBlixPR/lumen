"""Render the Lumen mark into lumen/assets/lumen.ico (PNG-compressed, 16–256 px) for Windows builds."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def png_bytes(image) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, images: list[tuple[int, bytes]]) -> None:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, payload = b"", b""
    for size, png in images:
        edge = 0 if size >= 256 else size  # 0 means 256 in the ICO directory
        entries += struct.pack("<BBBBHHII", edge, edge, 0, 0, 1, 32, len(png), offset + len(payload))
        payload += png
    path.write_bytes(header + entries + payload)


def main() -> int:
    app = QGuiApplication(sys.argv[:1])  # noqa: F841  (QPainter needs a GUI application)
    from lumen.ui.icons import app_icon_image

    target = ROOT / "lumen" / "assets" / "lumen.ico"
    write_ico(target, [(size, png_bytes(app_icon_image(size))) for size in SIZES])
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
