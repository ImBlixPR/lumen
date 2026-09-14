"""Lucide icons (ISC license), tinted and rasterised at the exact size requested.

QML asks for `image://icon/<name>/<color>`, for example "image://icon/play/#FF1D1D1F", and
the tray asks `tinted_icon(name, color)`. The SVGs use `currentColor`, which is replaced
before rendering, so every icon follows the theme with no second asset set.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import unquote

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

from .. import paths


@lru_cache(maxsize=None)
def _svg(name: str) -> str:
    return paths.asset("icons", f"{name}.svg").read_text(encoding="utf-8")


def render(name: str, color: QColor, size: QSize, stroke: float | None = None) -> QImage:
    # "heart:fill" draws the outline icon filled with the same colour (e.g. a favourited heart).
    name, _, variant = name.partition(":")
    svg = _svg(name).replace("currentColor", color.name(QColor.NameFormat.HexRgb))
    if variant == "fill":
        svg = svg.replace('fill="none"', f'fill="{color.name(QColor.NameFormat.HexRgb)}"', 1)
    if stroke is not None:
        svg = svg.replace('stroke-width="2"', f'stroke-width="{stroke:g}"')
    if color.alpha() < 255:
        svg = svg.replace("<svg", f'<svg opacity="{color.alphaF():.3f}"', 1)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size.width(), size.height()))
    painter.end()
    return image


def tinted_icon(name: str, color: QColor, size: int = 32) -> QIcon:
    return QIcon(QPixmap.fromImage(render(name, color, QSize(size, size))))


def app_icon_image(size: int) -> QImage:
    """The Lumen mark: a white captions glyph on an accent squircle."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, 0, size)
    gradient.setColorAt(0.0, QColor("#4DA3FF"))
    gradient.setColorAt(1.0, QColor("#0066CC"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    inset = size * 0.04
    painter.drawRoundedRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset), size * 0.23, size * 0.23)
    glyph = size * 0.58
    offset = (size - glyph) / 2
    stroke = 2.0 if size >= 48 else 2.6
    painter.drawImage(QRectF(offset, offset, glyph, glyph),
                      render("captions", QColor("#FFFFFF"), QSize(int(glyph), int(glyph)), stroke))
    painter.end()
    return image


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(app_icon_image(size)))
    return icon


class IconProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, icon_id: str, size: QSize, requested: QSize) -> QImage:
        # id: "<name>/<color>" with an optional "/<stroke>"
        parts = unquote(icon_id).split("/")
        name = parts[0]
        color = QColor(parts[1]) if len(parts) > 1 else QColor("#000000")
        stroke = float(parts[2]) if len(parts) > 2 else None
        target = requested if requested.isValid() and not requested.isEmpty() else QSize(48, 48)
        return render(name, color, target, stroke)
