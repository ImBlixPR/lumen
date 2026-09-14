"""One-time model downloads from Hugging Face, with byte-level progress.

Progress comes from watching the bytes land in the target folder, including the
`.incomplete` files the hub writes while downloading. That works with every
huggingface_hub version, unlike its private progress-bar hooks.
"""

from __future__ import annotations

import fnmatch
import os
import threading
from pathlib import Path
from typing import Callable

from .models import COMPLETE_MARKER, ModelSpec, model_dir

ProgressFn = Callable[[int, int], None]  # (bytes done, bytes total)


class Cancelled(Exception):
    pass


def _hub():
    # Plain HTTP downloads write .incomplete files next to the target, which makes byte progress
    # observable. The optional Xet backend streams into a global chunk cache instead.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    import huggingface_hub

    return huggingface_hub


def remote_size(spec: ModelSpec) -> int:
    info = _hub().HfApi().model_info(spec.repo, files_metadata=True)
    return sum(
        s.size or 0
        for s in info.siblings or ()
        if any(fnmatch.fnmatch(s.rfilename, p) for p in spec.patterns)
    )


def _bytes_on_disk(folder: Path) -> int:
    total = 0
    for f in folder.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def download(
    spec: ModelSpec, on_progress: ProgressFn | None = None, cancel: threading.Event | None = None
) -> Path:
    """Download `spec` into the models folder. Interrupted downloads resume on the next call."""
    hub = _hub()
    target = model_dir(spec)
    target.mkdir(parents=True, exist_ok=True)
    total = remote_size(spec) or spec.size_mb * 1_000_000

    finished = threading.Event()
    errors: list[BaseException] = []

    def work() -> None:
        try:
            hub.snapshot_download(spec.repo, local_dir=str(target), allow_patterns=list(spec.patterns))
        except BaseException as exc:  # surfaced to the caller below
            errors.append(exc)
        finally:
            finished.set()

    threading.Thread(target=work, name=f"download-{spec.id}", daemon=True).start()
    while not finished.wait(0.25):
        if cancel is not None and cancel.is_set():
            raise Cancelled(spec.id)
        if on_progress is not None:
            on_progress(min(_bytes_on_disk(target), total), total)
    if errors:
        raise errors[0]
    (target / COMPLETE_MARKER).write_text(spec.repo, encoding="utf-8")
    if on_progress is not None:
        on_progress(total, total)
    return target
