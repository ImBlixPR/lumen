"""Which translated sentence belongs on screen right now.

`SubtitleTrack` is a sorted, in-memory copy of the cached subtitles, updated as the worker
delivers new regions. `SubtitleClock` samples a smoothed playback position every frame
(16 ms) while playing, looks the sentence up by binary search, and emits only when the
text actually changes. The overlay's crossfade therefore starts the same frame the
sentence does and never delays it.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from ..pipeline.cache import Subtitle
from ..pipeline.scheduler import EPS

HOLD_GAP = 2.0  # keep a sentence up through pauses shorter than this
LINGER = 0.8  # …and this long after it ends when the pause is longer
MIN_VISIBLE = 1.2  # never flash a short sentence for less than this
BACK_RESTART = 1.5  # "back" restarts the current sentence if we're this far into it
MAX_EXTRAPOLATION = 1.5  # seconds the clock may run past the backend's last position report


@dataclass(slots=True)
class _Entry:
    id: int
    start: float
    end: float
    text: str | None


class SubtitleTrack:
    def __init__(self) -> None:
        self._entries: list[_Entry] = []
        self._starts: list[float] = []
        self._by_id: dict[int, _Entry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self.load([])

    def load(self, subtitles: list[Subtitle]) -> None:
        self._entries = [_Entry(s.id, s.start, s.end, s.text) for s in subtitles]
        self._reindex()

    def _reindex(self) -> None:
        self._entries.sort(key=lambda e: e.start)
        self._starts = [e.start for e in self._entries]
        self._by_id = {e.id: e for e in self._entries}

    def apply_region(self, start: float, end: float, rows: list[list]) -> None:
        """Mirror the cache: sentences starting inside [start, end) are replaced by `rows`."""
        kept = [e for e in self._entries if not (start - EPS <= e.start < end - EPS)]
        kept.extend(_Entry(int(r[0]), float(r[1]), float(r[2]), r[3]) for r in rows)
        self._entries = kept
        self._reindex()

    def apply_translations(self, items: list[list]) -> None:
        for sid, text in items:
            entry = self._by_id.get(int(sid))
            if entry is not None:
                entry.text = text

    def index_at(self, t: float) -> int:
        """Index of the last sentence starting at or before t, or -1."""
        return bisect_right(self._starts, t + 1e-3) - 1

    def visible_at(self, t: float) -> _Entry | None:
        i = self.index_at(t)
        if i < 0:
            return None
        entry = self._entries[i]
        next_start = self._entries[i + 1].start if i + 1 < len(self._entries) else float("inf")
        until = next_start if next_start - entry.end < HOLD_GAP else entry.end + LINGER
        until = max(until, min(entry.start + MIN_VISIBLE, next_start))
        return entry if t < until else None

    def pending_at(self, t: float) -> bool:
        """True while t is inside a sentence that is transcribed but not yet translated."""
        i = self.index_at(t)
        return i >= 0 and self._entries[i].text is None and t <= self._entries[i].end

    def back_target(self, t: float) -> float:
        """Where "back one sentence" should jump from position t."""
        i = self.index_at(t)
        if i < 0:
            return 0.0
        if t - self._entries[i].start > BACK_RESTART or i == 0:
            return self._entries[i].start
        return self._entries[i - 1].start

    def texts(self) -> int:
        return sum(1 for e in self._entries if e.text)


class SubtitleClock(QObject):
    textChanged = Signal(str)
    tick = Signal(float)  # smoothed position, every frame while playing

    def __init__(self, track: SubtitleTrack, parent: QObject | None = None):
        super().__init__(parent)
        self.track = track
        self._reported = 0.0
        self._output = 0.0
        self._rate = 1.0
        self._playing = False
        self._since_report = QElapsedTimer()
        self._since_report.start()
        self._text = ""
        self._ended = False  # the book finished: show nothing until playback moves again
        self._timer = QTimer(self, interval=16, timeout=self._update)
        self._timer.setTimerType(self._timer.timerType().PreciseTimer)

    @property
    def text(self) -> str:
        return self._text

    @property
    def position(self) -> float:
        return self._output

    def report(self, seconds: float) -> None:
        """Position from the media backend (it reports coarsely; we interpolate between)."""
        predicted = self._predict()
        self._reported = seconds
        self._since_report.restart()
        if abs(seconds - predicted) > 0.3:  # a seek or a stall: jump, don't glide
            self._output = seconds
        self._update()

    def seeked(self, seconds: float) -> None:
        self._ended = False
        self._reported = self._output = seconds
        self._since_report.restart()
        self._update()

    def finish(self) -> None:
        """The audio ended. Clear the subtitle rather than freezing on the last sentence,
        and ignore the player's final position reports until it plays or seeks again."""
        self._ended = True
        self._playing = False
        self._timer.stop()
        self._update(force=True)

    def set_playing(self, playing: bool) -> None:
        if playing:
            self._ended = False
        self._reported = self._predict()
        self._since_report.restart()
        self._playing = playing
        self._timer.start() if playing else self._timer.stop()
        self._update()

    def set_rate(self, rate: float) -> None:
        self._reported = self._predict()
        self._since_report.restart()
        self._rate = rate

    def refresh(self) -> None:
        self._update(force=True)

    def _elapsed_ms(self) -> int:
        return self._since_report.elapsed()

    def _predict(self) -> float:
        if not self._playing:
            return self._reported
        # Glide between the backend's position reports, but never far: if the audio stalls (its
        # output device was unplugged, say) the subtitles must wait for it, not run ahead.
        elapsed = min(self._elapsed_ms() / 1000.0, MAX_EXTRAPOLATION)
        return self._reported + elapsed * self._rate

    def _update(self, force: bool = False) -> None:
        predicted = self._predict()
        # Never run backwards through small reporting jitter while playing.
        self._output = max(self._output, predicted) if self._playing and predicted >= self._output - 0.3 else predicted
        # Subtitles show only while the audio plays: pausing (or the book ending) clears the
        # overlay, and resuming brings back the sentence at the current position.
        entry = None if (self._ended or not self._playing) else self.track.visible_at(self._output)
        text = (entry.text or "") if entry else ""
        if force or text != self._text:
            self._text = text
            self.textChanged.emit(text)
        if self._playing:
            self.tick.emit(self._output)
