"""Speech recognition with faster-whisper (CTranslate2 Whisper), language set explicitly."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import numpy as np

from .device import CPU, DeviceInfo, cpu_threads
from .sentences import Word

# Phrases Whisper invents over silence or music (learned from subtitle-heavy training data).
_HALLUCINATIONS = re.compile(
    r"amara\.org|subt[ií]tulos (realizados|por)|suscr[ií]bete|thanks for watching"
    r"|sous-titres|untertitel (im auftrag|der amara)|ترجمة نانسي|اشترك في القناة",
    re.IGNORECASE,
)


class Transcriber:
    def __init__(self, model_dir: Path, device: DeviceInfo):
        from faster_whisper import WhisperModel

        self.device = device
        try:
            self._model = WhisperModel(
                str(model_dir), device=device.device, compute_type=device.compute_type,
                cpu_threads=cpu_threads(),
            )
        except Exception:
            if device.device == "cpu":
                raise
            # CUDA present but unusable (missing cuDNN, out of memory…): fall back quietly.
            self.device = CPU
            self._model = WhisperModel(
                str(model_dir), device="cpu", compute_type=CPU.compute_type, cpu_threads=cpu_threads()
            )

    def transcribe(
        self,
        audio: np.ndarray,
        offset: float,
        language: str,
        prompt: str | None = None,
        on_progress: Callable[[float], None] | None = None,
        hotwords: str | None = None,
    ) -> list[Word]:
        """Timed words for `audio`, which starts `offset` seconds into the book.

        `prompt` only conditions the first 30 s segment (context isn't carried over, to avoid
        repetition loops), so character names also go in `hotwords`, which Whisper sees on
        every segment.
        """
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=5 if self.device.device == "cuda" else 2,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 700},
            condition_on_previous_text=False,
            initial_prompt=prompt or None,
            hotwords=hotwords or None,
        )
        words: list[Word] = []
        for segment in segments:  # lazy generator: decoding happens during iteration
            if on_progress is not None:
                on_progress(offset + segment.end)
            if segment.no_speech_prob > 0.6 and segment.avg_logprob < -1.0:
                continue
            if _HALLUCINATIONS.search(segment.text):
                continue
            for w in segment.words or ():
                words.append(Word(offset + w.start, offset + w.end, w.word))
        return words
