"""Decode MP3 / M4A / M4B / WAV (anything FFmpeg reads) to 16 kHz mono float32 for Whisper.

PyAV bundles its own FFmpeg, so no system install is needed. The decoder keeps the stream
open and remembers the tail of the last window. Consecutive windows, which overlap by the
dropped last sentence, therefore decode sequentially with sample-accurate timestamps and
only seek on a real jump.
"""

from __future__ import annotations

from os import PathLike

import av
import numpy as np

SAMPLE_RATE = 16_000
SEEK_PREROLL = 1.0  # seconds decoded before a seek target, then trimmed


def probe_duration(path: str | PathLike[str]) -> float:
    with av.open(str(path)) as container:
        if container.duration:
            return container.duration / av.time_base
        stream = container.streams.audio[0]
        if stream.duration and stream.time_base:
            return float(stream.duration * stream.time_base)
        return sum(frame.samples / frame.sample_rate for frame in container.decode(stream))


class AudioDecoder:
    def __init__(self, path: str | PathLike[str]):
        self._path = str(path)
        self._container: av.container.InputContainer | None = None
        self._frames = None
        self._resampler: av.AudioResampler | None = None
        self._buf = np.zeros(0, np.float32)
        self._buf_start: float | None = None
        self._eof = False

    @property
    def _buf_end(self) -> float:
        return (self._buf_start or 0.0) + len(self._buf) / SAMPLE_RATE

    def close(self) -> None:
        if self._container is not None:
            self._container.close()
        self._container = None
        self._frames = None

    def read(self, start: float, end: float) -> np.ndarray:
        """Samples for [start, end), zero-padded if the demuxer landed late after a seek."""
        if (
            self._container is None
            or self._buf_start is None
            or start < self._buf_start - 0.01
            or start > self._buf_end + SEEK_PREROLL
        ):
            self._seek(start)
        self._fill(end)

        origin = self._buf_start or 0.0
        a = int(round((start - origin) * SAMPLE_RATE))
        b = int(round((end - origin) * SAMPLE_RATE))
        out = self._buf[max(a, 0) : max(b, 0)].copy()
        if a < 0:
            out = np.concatenate([np.zeros(-a, np.float32), out])
        if a > 0:  # later windows never start before this one without a seek
            self._buf = self._buf[a:]
            self._buf_start = origin + a / SAMPLE_RATE
        return out

    def _seek(self, t: float) -> None:
        self.close()
        self._container = av.open(self._path)
        stream = self._container.streams.audio[0]
        target = max(0.0, t - SEEK_PREROLL)
        if target > 0:
            self._container.seek(int(target * av.time_base), backward=True, any_frame=False)
        self._resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
        self._frames = self._container.decode(stream)
        self._buf = np.zeros(0, np.float32)
        self._buf_start = None
        self._eof = False

    def _fill(self, end: float) -> None:
        assert self._resampler is not None and self._frames is not None
        pieces = [self._buf]
        n = len(self._buf)
        while not self._eof and (self._buf_start is None or self._buf_start + n / SAMPLE_RATE < end):
            try:
                frame = next(self._frames)
            except StopIteration:
                self._eof = True
                produced = self._resampler.resample(None)
            else:
                if self._buf_start is None:
                    self._buf_start = float(frame.time) if frame.time is not None else 0.0
                produced = self._resampler.resample(frame)
            for out in produced:
                samples = out.to_ndarray().reshape(-1).astype(np.float32, copy=False)
                pieces.append(samples)
                n += len(samples)
        if self._buf_start is None:
            self._buf_start = 0.0
        self._buf = np.concatenate(pieces) if len(pieces) > 1 else pieces[0]
