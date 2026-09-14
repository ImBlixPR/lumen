from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QImage

from lumen.services.library import _trim_transparent_bars


def png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def test_transparent_letterbox_bars_are_trimmed():
    # Like the test book's cover: a 16:9 still padded to a square with transparent bars.
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    for y in range(22, 78):
        for x in range(100):
            image.setPixelColor(x, y, QColor(120, 121, 117))
    out = QImage.fromData(_trim_transparent_bars(png(image)))
    assert (out.width(), out.height()) == (100, 56)


def test_opaque_dark_cover_is_left_alone():
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0))
    for y in range(45, 55):
        for x in range(20, 80):
            image.setPixelColor(x, y, QColor(255, 255, 255))
    data = png(image)
    assert _trim_transparent_bars(data) == data


def test_cover_without_bars_is_left_alone():
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(QColor(200, 80, 40))
    data = png(image)
    assert _trim_transparent_bars(data) == data
