import math

import pytest

from lumen.services.floating_player import TITLE_BAR_ZONE, orbit_layout, window_top

SCREENS = [(1280, 720), (1920, 1080), (2560, 1440), (3440, 1400), (3840, 2100)]


def visible_fraction(layout, center) -> float:
    """Share of the disc inside the window (the window's right edge = the screen's right edge)."""
    cx, cy = center
    r = layout.disc / 2
    inside = total = 0
    steps = 120
    for i in range(steps):
        for j in range(steps):
            x = cx - r + (i + 0.5) * 2 * r / steps
            y = cy - r + (j + 0.5) * 2 * r / steps
            if math.hypot(x - cx, y - cy) <= r:
                total += 1
                inside += 0 <= x <= layout.width and 0 <= y <= layout.height
    return inside / total


@pytest.mark.parametrize("screen", SCREENS)
def test_collapsed_shows_a_quarter_to_forty_percent(screen):
    layout = orbit_layout(*screen)
    assert 0.25 <= visible_fraction(layout, layout.collapsed) <= 0.40


@pytest.mark.parametrize("screen", SCREENS)
def test_disc_slides_straight_out_of_the_edge(screen):
    layout = orbit_layout(*screen)
    assert visible_fraction(layout, layout.expanded) == 1.0
    assert visible_fraction(layout, layout.collapsed) < visible_fraction(layout, layout.peek) < 1.0
    assert visible_fraction(layout, layout.hidden) == 0.0
    heights = {layout.center(s)[1] for s in ("hidden", "collapsed", "peek", "expanded")}
    assert len(heights) == 1  # moves horizontally only


def test_disc_scales_with_the_screen_within_bounds():
    assert orbit_layout(800, 600).disc == 120
    assert orbit_layout(1920, 1080).disc == 162
    assert orbit_layout(5120, 2880).disc == 200


@pytest.mark.parametrize("screen", SCREENS)
def test_controls_popover_and_info_fit_inside_the_window(screen):
    layout = orbit_layout(*screen)
    q = layout.to_qml()
    for name, size in (("play", q["playSize"]), ("library", q["buttonSize"]), ("settings", q["buttonSize"])):
        x, y = q[name]
        assert size / 2 <= x <= layout.width - size / 2 and size / 2 <= y <= layout.height - size / 2, name
    for name in ("popover", "info"):
        x, y, w, h = q[name]
        assert x >= 0 and y >= 0 and x + w <= layout.width and y + h <= layout.height, name
    tx, ty = q["timestamp"]
    assert ty - 14 >= 0 and tx + 60 <= layout.width


def test_controls_stay_outside_the_disc():
    layout = orbit_layout(1920, 1080)
    cx, cy = layout.expanded
    q = layout.to_qml()
    for name in ("play", "library", "settings"):
        x, y = q[name]
        assert math.hypot(x - cx, y - cy) > layout.arc_radius + q["buttonSize"] / 2 - 1, name


@pytest.mark.parametrize("screen", SCREENS)
def test_default_spot_keeps_clear_of_title_bars(screen):
    layout = orbit_layout(*screen)
    area_h = screen[1] - 40  # minus the taskbar
    top = window_top(0, area_h, layout.height, layout.expanded[1], -1.0)
    assert top >= TITLE_BAR_ZONE                 # nothing in the title-bar / tab zone
    assert top + layout.height <= area_h          # and never below the screen
    disc_center = top + layout.expanded[1]
    assert 0.2 * area_h <= disc_center <= 0.5 * area_h


def test_dragged_spot_is_clamped_to_the_screen():
    layout = orbit_layout(1920, 1080)
    area_h = 1040
    assert window_top(0, area_h, layout.height, layout.expanded[1], 0.0) == 0
    assert window_top(0, area_h, layout.height, layout.expanded[1], 1.0) == area_h - layout.height
    assert window_top(0, area_h, layout.height, layout.expanded[1], 7.0) == area_h - layout.height
    middle = window_top(0, area_h, layout.height, layout.expanded[1], 0.5)
    assert middle == round((area_h - layout.height) / 2)
