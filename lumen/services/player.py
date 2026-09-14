"""Audio playback with QtMultimedia (FFmpeg backend: MP3, M4A/M4B, WAV, FLAC, OGG…).

The output follows the Windows default audio device. When you plug in an HDMI monitor or
headphones and Windows switches to them, the sound moves there; unplug them and it moves
back. Without this, the output stays bound to the device Lumen started on, and playback
stalls when that device disappears.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

MIN_RATE, MAX_RATE = 0.5, 2.0
DEVICE_POLL_MS = 2000  # also catches a default changed in Windows sound settings


def choose_output(current: bytes | None, default: bytes | None) -> bytes | None:
    """The output device to switch to, or None to stay: always follow the system default."""
    if not default or default == current:
        return None
    return default


class PlayerService(QObject):
    positionChanged = Signal(float)  # seconds, as reported by the backend
    durationChanged = Signal(float)
    playingChanged = Signal(bool)
    rateChanged = Signal(float)
    seeked = Signal(float)
    loaded = Signal()
    finished = Signal()  # the book played to its end
    outputChanged = Signal(str)  # name of the audio device now in use
    error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        if hasattr(self._player, "setPitchCompensation"):  # Qt 6.10+: keep voices natural at 0.5–2×
            self._player.setPitchCompensation(True)
        self._player.positionChanged.connect(lambda ms: self.positionChanged.emit(ms / 1000.0))
        self._player.durationChanged.connect(lambda ms: self.durationChanged.emit(ms / 1000.0))
        self._player.playbackStateChanged.connect(
            lambda state: self.playingChanged.emit(state == QMediaPlayer.PlaybackState.PlayingState)
        )
        self._player.playbackRateChanged.connect(self.rateChanged.emit)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(lambda _err, message: self.error.emit(message))

        self._output_id = b""
        self._devices = QMediaDevices(self)
        self._devices.audioOutputsChanged.connect(self._schedule_output_check)
        self._check_output()  # bind to the current default
        self._device_poll = QTimer(self, interval=DEVICE_POLL_MS, timeout=self._check_output)
        self._device_poll.start()

    @property
    def pitch_compensated(self) -> bool:
        return hasattr(self._player, "pitchCompensation") and bool(self._player.pitchCompensation())

    @property
    def output_name(self) -> str:
        return self._audio.device().description()

    @property
    def position(self) -> float:
        return self._player.position() / 1000.0

    @property
    def duration(self) -> float:
        return self._player.duration() / 1000.0

    @property
    def playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def rate(self) -> float:
        return self._player.playbackRate()

    def load(self, path: str | Path, start_at: float = 0.0, autoplay: bool = False) -> None:
        self._pending_seek = max(0.0, start_at)
        self._autoplay = autoplay  # start only after the resume seek, so it never blips from 0:00
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def _on_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            if getattr(self, "_pending_seek", 0.0):
                self.seek(self._pending_seek)
                self._pending_seek = 0.0
            self.loaded.emit()
            if getattr(self, "_autoplay", False):
                self._autoplay = False
                self.play()
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.playingChanged.emit(False)
            self.finished.emit()

    # -- output device ------------------------------------------------------------------------
    def _schedule_output_check(self) -> None:
        # Windows updates its default device a moment after the device list changes.
        for delay in (250, 1200):
            QTimer.singleShot(delay, self._check_output)

    def _check_output(self) -> None:
        default = QMediaDevices.defaultAudioOutput()
        default_id = bytes(default.id().data()) if not default.isNull() else None
        target = choose_output(self._output_id or None, default_id)
        if target is None:
            return
        first = not self._output_id
        was_playing = self.playing
        position = self._player.position()
        self._audio.setDevice(default)
        self._output_id = target
        if first:
            return
        self.outputChanged.emit(default.description())
        if was_playing:
            QTimer.singleShot(200, lambda: self._resume_after_switch(position))

    def _resume_after_switch(self, position_ms: int) -> None:
        # Losing the old device can stop playback: carry on from where it was.
        if not self.playing:
            self._player.setPosition(position_ms)
            self._player.play()

    # -- transport ----------------------------------------------------------------------------
    def play(self) -> None:
        if self._player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self.seek(0.0)  # a finished book starts over, as in music players
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def toggle(self) -> None:
        self.pause() if self.playing else self.play()

    def seek(self, seconds: float) -> None:
        seconds = max(0.0, min(seconds, self.duration or seconds))
        self._player.setPosition(int(seconds * 1000))
        self.seeked.emit(seconds)

    def skip(self, delta: float) -> None:
        self.seek(self.position + delta)

    def set_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(min(MAX_RATE, max(MIN_RATE, round(rate, 2))))

    def set_volume(self, volume: float) -> None:
        self._audio.setVolume(min(1.0, max(0.0, volume)))

    def stop(self) -> None:
        self._player.stop()
