from lumen.pipeline.scheduler import (
    Window,
    first_gap,
    merge_intervals,
    next_window,
    plan_commit,
    ready_until,
)
from lumen.pipeline.sentences import Sentence


def test_merge_intervals_joins_touching_and_overlapping():
    assert merge_intervals([(5, 8), (0, 2), (2.01, 3), (7, 9)]) == [(0, 3), (5, 9)]


def test_first_gap_skips_covered_stretch():
    cov = [(0, 10), (20, 30)]
    assert first_gap(cov, 5, 100) == 10
    assert first_gap(cov, 15, 100) == 15
    assert first_gap(cov, 25, 30) is None


def test_ready_until():
    assert ready_until([(0, 10), (10, 25)], 3) == 25
    assert ready_until([(0, 10)], 12) == 12


def test_window_starts_at_playhead_then_wraps():
    assert next_window([], 100, 1000, 240) == Window(100, 340, None, False)
    assert next_window([(100, 400)], 150, 1000, 240).start == 400
    assert next_window([(100, 1000)], 500, 1000, 240).start == 0


def test_window_runs_into_coverage_with_seam_overlap():
    w = next_window([(300, 1000)], 0, 1000, 400)
    assert (w.start, w.boundary, w.end) == (0, 300, 315)


def test_window_at_end_of_file():
    assert next_window([], 900, 1000, 240) == Window(900, 1000, None, True)


def s(a, b, t="x."):
    return Sentence(a, b, t)


def test_commit_drops_cut_off_last_sentence():
    w = Window(0, 60, None, False)
    c = plan_commit([s(0, 5), s(6, 12), s(55, 60)], w)
    assert [x.start for x in c.sentences] == [0, 6]
    assert c.region_end == (12 + 55) / 2


def test_commit_keeps_last_sentence_when_window_ends_in_silence():
    c = plan_commit([s(0, 5), s(6, 12)], Window(0, 60, None, False))
    assert len(c.sentences) == 2 and c.region_end == 36


def test_commit_everything_at_eof():
    c = plan_commit([s(0, 5), s(6, 10)], Window(0, 10, None, True))
    assert len(c.sentences) == 2 and c.region_end == 10


def test_empty_window_is_marked_covered():
    assert plan_commit([], Window(0, 60, None, False)).region_end == 60


def test_seam_aligned_at_boundary_keeps_existing():
    w = Window(0, 115, 100, False)
    new = [s(0, 50), s(51, 99.5), s(100.2, 110)]
    existing = [s(100.1, 110)]
    c = plan_commit(new, w, existing)
    assert [x.start for x in c.sentences] == [0, 51]
    assert c.region_end == 100.1


def test_seam_replaces_fragment_from_seek_chunk():
    # The seek chunk started at 100 mid-sentence: the cached fragment is 100–104.
    # The new transcription has the whole sentence 95–104 and agrees on the boundary at 105.
    w = Window(0, 115, 100, False)
    new = [s(0, 94), s(95, 104), s(105, 112)]
    existing = [s(100, 104, "fragment."), s(105, 112)]
    c = plan_commit(new, w, existing)
    assert [x.start for x in c.sentences] == [0, 95]
    assert c.region_end == 105
