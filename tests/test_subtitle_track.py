from lumen.pipeline.cache import Subtitle
from lumen.services.subtitle_clock import SubtitleTrack


def track(*rows):
    t = SubtitleTrack()
    t.load([Subtitle(i, s, e, text) for i, (s, e, text) in enumerate(rows, start=1)])
    return t


def test_sentence_holds_through_short_pause_and_hides_after_long_one():
    t = track((10, 14, "a"), (15, 18, "b"), (30, 33, "c"))
    assert t.visible_at(9.9) is None
    assert t.visible_at(12).text == "a"
    assert t.visible_at(14.5).text == "a"  # 1 s gap to "b": keep "a" up
    assert t.visible_at(18.5).text == "b"  # lingers 0.8 s after a long gap starts
    assert t.visible_at(19.5) is None
    assert t.visible_at(31).text == "c"


def test_short_sentence_stays_up_for_minimum_time():
    t = track((10, 10.3, "Oui."), (20, 22, "x"))
    assert t.visible_at(11.1).text == "Oui."


def test_back_target_restarts_current_or_goes_to_previous():
    t = track((10, 14, "a"), (15, 18, "b"))
    assert t.back_target(17.0) == 15  # 2 s into "b": restart it
    assert t.back_target(15.5) == 10  # just started "b": go to "a"
    assert t.back_target(11.0) == 10  # first sentence: restart
    assert t.back_target(5.0) == 0.0  # before any sentence


def test_region_replaces_sentences_starting_inside_it():
    t = track((10, 14, "old"), (15, 18, "keep"))
    t.apply_region(0, 14.9, [[99, 9.5, 14.2, "new"]])
    assert [e.text for e in (t.visible_at(12), t.visible_at(16))] == ["new", "keep"]


def test_pending_until_translation_arrives():
    t = track((10, 14, None))
    assert t.pending_at(12)
    assert t.visible_at(12).text is None
    t.apply_translations([[1, "مرحبا"]])
    assert not t.pending_at(12)
    assert t.visible_at(12).text == "مرحبا"
    assert t.texts() == 1
