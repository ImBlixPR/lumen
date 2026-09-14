"""Catalogue of downloadable speech and translation models.

All models are CTranslate2 conversions, so one runtime covers both, on CPU (int8) and on
NVIDIA GPUs (float16 / int8_float16). They are downloaded once during onboarding and then
loaded from disk with no network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import paths

_ASR_FILES = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)
_MT_FILES = ("config.json", "model.bin", "sentencepiece.bpe.model", "shared_vocabulary.txt")

COMPLETE_MARKER = ".complete"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: str
    kind: str  # "asr" or "mt"
    label: str
    repo: str
    size_mb: int
    speed: int  # 1 (slow) … 5 (fast), relative within its kind
    accuracy: int  # 1 … 5
    note: str
    patterns: tuple[str, ...]


ASR_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("tiny", "asr", "Tiny", "Systran/faster-whisper-tiny", 75, 5, 1,
              "Fastest. Misses names and fast speech.", _ASR_FILES),
    ModelSpec("base", "asr", "Base", "Systran/faster-whisper-base", 145, 5, 2,
              "Quick drafts on older computers.", _ASR_FILES),
    ModelSpec("small", "asr", "Small", "Systran/faster-whisper-small", 485, 4, 3,
              "The best balance without a GPU.", _ASR_FILES),
    ModelSpec("medium", "asr", "Medium", "Systran/faster-whisper-medium", 1530, 2, 4,
              "More accurate, needs a fast CPU or a GPU.", _ASR_FILES),
    ModelSpec("large-v3-turbo", "asr", "Large v3 Turbo", "dropbox-dash/faster-whisper-large-v3-turbo",
              1620, 3, 5, "Near-best accuracy at medium speed. Ideal with a GPU.", _ASR_FILES),
    ModelSpec("large-v3", "asr", "Large v3", "Systran/faster-whisper-large-v3", 3090, 1, 5,
              "Most accurate. Slow without a GPU.", _ASR_FILES),
)

MT_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("nllb-600m", "mt", "NLLB-200 · 600M", "JustFrederik/nllb-200-distilled-600M-ct2-int8",
              630, 4, 3, "Fast, natural translations for most languages.", _MT_FILES),
    ModelSpec("nllb-1.3b", "mt", "NLLB-200 · 1.3B", "JustFrederik/nllb-200-distilled-1.3B-ct2-int8",
              1390, 2, 4, "Better phrasing and rare words. About twice as slow.", _MT_FILES),
)

_ALL = {m.id: m for m in (*ASR_MODELS, *MT_MODELS)}


def get_model(model_id: str) -> ModelSpec:
    return _ALL[model_id]


def model_dir(spec: ModelSpec) -> Path:
    return paths.models_dir() / spec.kind / spec.id


def is_installed(spec: ModelSpec) -> bool:
    folder = model_dir(spec)
    return (folder / COMPLETE_MARKER).exists() and (folder / "model.bin").exists()


def default_asr(has_gpu: bool) -> str:
    return "large-v3-turbo" if has_gpu else "small"


def default_mt(has_gpu: bool) -> str:
    # Large v3 Turbo + NLLB 1.3B peaked at about 2.8 GB of GPU memory in testing (RTX 3050,
    # 4 GB), so the better translator fits alongside the recommended speech model.
    return "nllb-1.3b" if has_gpu else "nllb-600m"


DEFAULT_MT = "nllb-600m"
