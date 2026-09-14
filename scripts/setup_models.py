"""Download Lumen's speech and translation models once (the onboarding screen does the same).

    uv run python scripts/setup_models.py                      # auto: GPU → large-v3-turbo, CPU → small
    uv run python scripts/setup_models.py --asr medium --mt nllb-1.3b
    uv run python scripts/setup_models.py --list
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lumen import models  # noqa: E402
from lumen.downloads import download  # noqa: E402
from lumen.pipeline.device import detect  # noqa: E402


def _bar(label: str):
    started = time.monotonic()

    def show(done: int, total: int) -> None:
        frac = done / total if total else 0.0
        filled = int(frac * 30)
        rate = done / max(time.monotonic() - started, 1e-6) / 1e6
        print(f"\r  {label:<18} [{'█' * filled}{'·' * (30 - filled)}] {frac:6.1%}  {done / 1e6:7.0f} / {total / 1e6:.0f} MB  {rate:5.1f} MB/s", end="", flush=True)

    return show


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asr", default="auto", help="speech model id, or 'auto'")
    parser.add_argument("--mt", default="auto", help="translation model id, or 'auto'")
    parser.add_argument("--list", action="store_true", help="list available models and exit")
    args = parser.parse_args()

    if args.list:
        for spec in (*models.ASR_MODELS, *models.MT_MODELS):
            state = "installed" if models.is_installed(spec) else f"{spec.size_mb} MB"
            print(f"{spec.kind:<4} {spec.id:<16} {spec.label:<18} {state:<10} {spec.note}")
        return 0

    device = detect()
    print(f"Compute device: {device.name} ({device.device}, {device.compute_type})")
    asr_id = models.default_asr(device.device == "cuda") if args.asr == "auto" else args.asr
    mt_id = models.default_mt(device.device == "cuda") if args.mt == "auto" else args.mt
    for spec in (models.get_model(asr_id), models.get_model(mt_id)):
        if models.is_installed(spec):
            print(f"  {spec.label:<18} already installed")
            continue
        download(spec, _bar(spec.label))
        print()
    print(f"Done. Models are in {models.model_dir(models.get_model(asr_id)).parent.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
