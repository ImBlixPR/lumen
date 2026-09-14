from PySide6.QtCore import QCoreApplication

from lumen.pipeline.cache import Subtitle
from lumen.services.subtitle_clock import SubtitleClock, SubtitleTrack

LAST = "آخر جملة"


def make_clock(playing: bool = True) -> SubtitleClock:
    _app = QCoreApplication.instance() or QCoreApplication([])
    track = SubtitleTrack()
    track.load([Subtitle(1, 128.9, 130.4, LAST)])
    clock = SubtitleClock(track)
    clock.set_playing(playing)
    return clock


def test_subtitle_clears_when_the_book_ends():
    clock = make_clock()
    clock.report(129.5)
    assert clock.text == LAST

    clock.finish()
    assert clock.text == ""

    clock.report(130.0)  # a late position report from the player must not bring it back
    assert clock.text == ""


def test_playing_again_after_the_end_shows_subtitles_again():
    clock = make_clock()
    clock.finish()
    clock.seeked(129.0)
    assert clock.text == ""  # still paused after the end
    clock.set_playing(True)
    clock.report(129.2)
    assert clock.text == LAST
    clock.set_playing(False)


def test_pausing_hides_the_subtitle_and_resuming_shows_it():
    clock = make_clock()
    clock.report(129.5)
    assert clock.text == LAST

    clock.set_playing(False)
    assert clock.text == ""

    clock.seeked(129.0)  # seeking while paused shows nothing until playback resumes
    assert clock.text == ""

    clock.set_playing(True)
    assert clock.text == LAST
    clock.set_playing(False)


def test_clock_waits_for_stalled_audio(monkeypatch):
    # No position report for 10 s (e.g. the output device was unplugged): the clock may glide
    # a little past the last report, but must not run on ahead of the audio.
    clock = make_clock()
    clock.report(129.0)
    monkeypatch.setattr(clock, "_elapsed_ms", lambda: 10_000)
    clock.refresh()
    assert clock.position <= 129.0 + 1.5 + 1e-6
    clock.set_playing(False)


def test_nothing_shows_before_playback_starts():
    clock = make_clock(playing=False)
    clock.report(129.5)  # a book reopened paused at its resume position
    assert clock.text == ""
