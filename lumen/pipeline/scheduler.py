"""Decide which slice of the book to process next, and what to keep from it.

Coverage is the set of time intervals that are already transcribed. Work always goes to the
first gap at or after the playhead, so subtitles stay ahead of what you hear. Once the rest
of the book is done, it wraps around and backfills from the start.

Each window keeps only complete sentences. The last one may be cut off by the window edge,
so it is dropped and the next window starts just before it. When a window runs into
existing coverage (typically after a seek), it decodes a little past the seam and splices
the two transcriptions at a sentence boundary both agree on. That replaces the fragment the
seek-started chunk began with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .sentences import Sentence

Interval = tuple[float, float]

EPS = 0.05
SEAM_OVERLAP = 15.0  # seconds decoded past a seam so the straddling sentence completes
TRAILING_SILENCE = 2.0  # a window ending in this much silence has no cut-off sentence
BOUNDARY_TOLERANCE = 0.3
MAX_BOUNDARY_GAP = 1.5


def merge_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(intervals):
        if end - start <= 0:
            continue
        if merged and start <= merged[-1][1] + EPS:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def covered_seconds(coverage: Sequence[Interval]) -> float:
    return sum(end - start for start, end in coverage)


def first_gap(coverage: Sequence[Interval], at: float, duration: float) -> float | None:
    """Earliest unprocessed time at or after `at`, or None if everything after it is done."""
    t = max(0.0, at)
    for start, end in coverage:
        if end <= t:
            continue
        if start > t + EPS:
            break
        t = end
    return t if t < duration - EPS else None


def ready_until(coverage: Sequence[Interval], at: float) -> float:
    """End of the contiguous processed stretch containing `at` (or `at` if it is a gap)."""
    t = at
    for start, end in coverage:
        if start <= t + EPS < end + EPS:
            t = max(t, end)
    return t


@dataclass(frozen=True, slots=True)
class Window:
    start: float
    end: float  # decode up to here
    boundary: float | None  # start of existing coverage this window runs into
    at_eof: bool


def next_window(
    coverage: Sequence[Interval], playhead: float, duration: float, length: float
) -> Window | None:
    start = first_gap(coverage, playhead, duration)
    if start is None:
        start = first_gap(coverage, 0.0, duration)
        if start is None:
            return None
    limit = next((s for s, _ in coverage if s > start + EPS), duration)
    if start + length < limit:
        return Window(start, start + length, None, False)
    if limit >= duration - EPS:
        return Window(start, duration, None, True)
    return Window(start, min(limit + SEAM_OVERLAP, duration), limit, False)


@dataclass(frozen=True, slots=True)
class Commit:
    sentences: list[Sentence] = field(default_factory=list)
    region_end: float = 0.0  # coverage grows to [window.start, region_end]


def plan_commit(
    sentences: Sequence[Sentence], window: Window, existing: Sequence[Sentence] = ()
) -> Commit:
    """Choose the sentences to store from a processed window.

    `existing` holds already-cached sentences that start within [boundary, window.end]. It
    matters only when the window has a boundary.
    """
    sents = [s for s in sentences if s.end > window.start + EPS]
    if window.boundary is not None:
        return _resolve_seam(sents, window.boundary, existing)
    if window.at_eof or not sents:
        return Commit(sents, window.end)

    last = sents[-1]
    if window.end - last.end >= TRAILING_SILENCE:
        return Commit(sents, (last.end + window.end) / 2)

    committed = sents[:-1]
    if not committed:
        # A lone sentence reaching the window edge: store it so processing always advances.
        return Commit(sents, max(last.end, window.start + EPS * 2))
    region_end = max(committed[-1].end, (committed[-1].end + last.start) / 2)
    return Commit(committed, region_end)


def _resolve_seam(sents: list[Sentence], boundary: float, existing: Sequence[Sentence]) -> Commit:
    for old in sorted(existing, key=lambda s: s.start):
        if old.start < boundary - EPS:
            continue
        cut = old.start
        straddles = any(
            n.start < cut - BOUNDARY_TOLERANCE and n.end > cut + BOUNDARY_TOLERANCE for n in sents
        )
        touches = any(cut - MAX_BOUNDARY_GAP <= n.end <= cut + BOUNDARY_TOLERANCE for n in sents)
        if touches and not straddles:
            keep = [n for n in sents if n.end <= cut + BOUNDARY_TOLERANCE]
            return Commit(keep, max(cut, boundary))
    # No boundary both transcriptions agree on: keep what cleanly precedes the seam.
    keep = [n for n in sents if n.start < boundary - EPS and n.end <= boundary + BOUNDARY_TOLERANCE]
    return Commit(keep, boundary)
