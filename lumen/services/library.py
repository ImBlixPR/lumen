"""Book metadata: title, author, cover art and chapters (MP4/M4B atoms, ID3 tags, CHAP frames)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import paths
from ..pipeline.decoder import probe_duration

SUPPORTED_SUFFIXES = (".mp3", ".m4a", ".m4b", ".mp4", ".aac", ".wav", ".flac", ".ogg", ".opus")


@dataclass
class Chapter:
    start: float
    title: str


@dataclass
class BookInfo:
    path: str
    key: str
    title: str
    author: str = ""
    cover: str = ""  # file URL, or "" for the generated placeholder
    duration: float = 0.0
    chapters: list[Chapter] = field(default_factory=list)

    def chapter_at(self, t: float) -> Chapter | None:
        current = None
        for chapter in self.chapters:
            if chapter.start <= t + 0.05:
                current = chapter
            else:
                break
        return current

    def to_qml(self) -> dict:
        return {
            "path": self.path, "title": self.title, "author": self.author, "cover": self.cover,
            "duration": self.duration,
            "chapters": [{"start": c.start, "title": c.title} for c in self.chapters],
        }


def _first(tags, *keys) -> str:
    for key in keys:
        value = tags.get(key) if tags is not None else None
        if value:
            item = value[0] if isinstance(value, list) else value
            text = getattr(item, "text", item)
            if isinstance(text, list):
                text = text[0] if text else ""
            if str(text).strip():
                return str(text).strip()
    return ""


def _trim_transparent_bars(data: bytes) -> bytes:
    """Crop fully transparent letterbox bars (e.g. a 16:9 video still padded to a square) so the
    artwork fills the round disc. Opaque borders are left alone: a dark cover is still a cover."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImage

    image = QImage.fromData(data)
    if image.isNull() or not image.hasAlphaChannel():
        return data
    w, h = image.width(), image.height()
    xs = range(0, w, max(1, w // 64))
    ys = range(0, h, max(1, h // 64))

    def clear_row(y: int) -> bool:
        return all(image.pixelColor(x, y).alpha() < 16 for x in xs)

    def clear_col(x: int) -> bool:
        return all(image.pixelColor(x, y).alpha() < 16 for y in ys)

    top, bottom, left, right = 0, h - 1, 0, w - 1
    while top < h - 1 and clear_row(top):
        top += 1
    while bottom > top and clear_row(bottom):
        bottom -= 1
    while left < w - 1 and clear_col(left):
        left += 1
    while right > left and clear_col(right):
        right -= 1
    cw, ch = right - left + 1, bottom - top + 1
    if (cw, ch) == (w, h) or cw < w * 0.3 or ch < h * 0.3:
        return data
    out = QByteArray()
    buffer = QBuffer(out)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.copy(left, top, cw, ch).save(buffer, "PNG")
    return bytes(out)


def _save_cover(key: str, data: bytes) -> str:
    folder = paths.cache_dir() / "covers"
    folder.mkdir(parents=True, exist_ok=True)
    data = _trim_transparent_bars(data)
    suffix = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
    target = folder / f"{key}-v2{suffix}"  # -v2: trimmed covers; older untrimmed files are ignored
    if not target.exists():
        target.write_bytes(data)
    return target.as_uri()


def _mp4(audio, key: str) -> tuple[str, str, str, list[Chapter]]:
    tags = audio.tags or {}
    title = _first(tags, "©nam", "©alb")
    author = _first(tags, "©ART", "aART", "©wrt")
    cover = _save_cover(key, bytes(tags["covr"][0])) if tags.get("covr") else ""
    chapters = [Chapter(float(c.start), c.title or f"Chapter {i + 1}")
                for i, c in enumerate(getattr(audio, "chapters", None) or [])]
    return title, author, cover, chapters


def _id3(tags, key: str) -> tuple[str, str, str, list[Chapter]]:
    title = _first(tags, "TIT2", "TALB")
    author = _first(tags, "TPE1", "TPE2", "TCOM")
    pictures = tags.getall("APIC") if tags is not None else []
    cover = _save_cover(key, pictures[0].data) if pictures else ""
    chapters = []
    for frame in sorted(tags.getall("CHAP") if tags is not None else [], key=lambda f: f.start_time):
        sub = frame.sub_frames.get("TIT2") if frame.sub_frames else None
        name = str(sub.text[0]) if sub and sub.text else f"Chapter {len(chapters) + 1}"
        chapters.append(Chapter(frame.start_time / 1000.0, name))
    return title, author, cover, chapters


def read_book(path: str | Path, key: str) -> BookInfo:
    path = Path(path)
    title = author = cover = ""
    chapters: list[Chapter] = []
    try:
        import mutagen
        from mutagen.id3 import ID3
        from mutagen.mp4 import MP4

        audio = mutagen.File(path)
        if isinstance(audio, MP4):
            title, author, cover, chapters = _mp4(audio, key)
        elif audio is not None and isinstance(getattr(audio, "tags", None), ID3):
            title, author, cover, chapters = _id3(audio.tags, key)
        elif audio is not None and audio.tags is not None:
            title = _first(audio.tags, "title", "album")
            author = _first(audio.tags, "artist", "albumartist")
    except Exception:
        pass  # unreadable tags never block playback
    return BookInfo(
        path=str(path), key=key, title=title or path.stem.replace("_", " "), author=author,
        cover=cover, duration=probe_duration(path), chapters=chapters,
    )
