"""Sentence translation with NLLB-200 through CTranslate2, tokenized with SentencePiece.

No transformers or torch at runtime: the CT2 model directory ships the SentencePiece model,
and NLLB's language tokens are added by hand ([src] tokens </s> → [tgt] tokens).
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .device import CPU, DeviceInfo, cpu_threads

MAX_BATCH = 16


class Translator:
    def __init__(self, model_dir: Path, device: DeviceInfo):
        import ctranslate2
        import sentencepiece as spm

        self._sp = spm.SentencePieceProcessor(model_file=str(model_dir / "sentencepiece.bpe.model"))
        self.device = device
        try:
            self._model = ctranslate2.Translator(
                str(model_dir), device=device.device, compute_type=device.compute_type,
                intra_threads=cpu_threads(),
            )
        except Exception:
            if device.device == "cpu":
                raise
            self.device = CPU
            self._model = ctranslate2.Translator(
                str(model_dir), device="cpu", compute_type=CPU.compute_type, intra_threads=cpu_threads()
            )

    def translate(self, texts: Sequence[str], src_flores: str, tgt_flores: str) -> list[str]:
        if not texts:
            return []
        source = [[src_flores, *self._sp.encode(t, out_type=str), "</s>"] for t in texts]
        results = self._model.translate_batch(
            source,
            target_prefix=[[tgt_flores]] * len(source),
            beam_size=4,
            max_batch_size=MAX_BATCH,
            max_decoding_length=256,
            repetition_penalty=1.1,
            no_repeat_ngram_size=4,
        )
        out: list[str] = []
        for result in results:
            tokens = result.hypotheses[0]
            if tokens and tokens[0] == tgt_flores:
                tokens = tokens[1:]
            out.append(self._sp.decode(tokens).strip())
        return out
