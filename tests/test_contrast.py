"""Every text and control pairing in the design tokens must meet WCAG 2.2 AA."""

import json
import re
from pathlib import Path

import pytest

TOKENS = json.loads((Path(__file__).parents[1] / "lumen/ui/theme/tokens.json").read_text("utf-8"))


def rgba(value: str) -> tuple[float, float, float, float]:
    value = value.strip()
    if value.startswith("#"):
        h = value[1:]
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
    r, g, b, a = (float(x) for x in re.findall(r"[\d.]+", value))
    return r, g, b, a


def over(fg: str, bg: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b, a = rgba(fg)
    return tuple(a * c + (1 - a) * d for c, d in zip((r, g, b), bg))


def luminance(rgb) -> float:
    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


TEXT, UI = 4.5, 3.0

# (foreground, background, minimum). Backgrounds are composited over the window base.
PAIRS = [
    ("textPrimary", "bg", TEXT),
    ("textPrimary", "surface", TEXT),
    ("textPrimary", "surfaceStrong", TEXT),
    ("textSecondary", "bg", TEXT),
    ("textSecondary", "surface", TEXT),
    ("textSecondary", "surfaceSunken", TEXT),
    ("accent", "bg", TEXT),
    ("accent", "surface", TEXT),
    ("onAccent", "accentFill", TEXT),
    ("onAccent", "accentPressed", TEXT),
    ("danger", "bg", TEXT),
    ("controlBoundary", "bg", UI),
    ("controlBoundary", "surface", UI),
    ("controlBoundary", "bgElevated", UI),
    ("accentFill", "bg", UI),
]


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("fg,bg,minimum", PAIRS)
def test_token_pair_meets_wcag_aa(scheme, fg, bg, minimum):
    colors = TOKENS["color"][scheme]
    base = rgba(colors["bg"])[:3]
    background = over(colors[bg], base)
    foreground = over(colors[fg], background)
    ratio = contrast(foreground, background)
    assert ratio >= minimum, f"{scheme}: {fg} on {bg} is {ratio:.2f}:1, needs {minimum}:1"


@pytest.mark.parametrize("backdrop", ["#FFFFFF", "#000000", "#808080", "#FFEB3B"])
def test_default_overlay_is_readable_on_any_backdrop(backdrop):
    overlay = TOKENS["overlay"]
    r, g, b, _ = rgba(overlay["backing"])
    alpha = overlay["backingOpacity"]
    pill = over(f"rgba({r}, {g}, {b}, {alpha})", rgba(backdrop)[:3])
    assert contrast(rgba(overlay["text"])[:3], pill) >= TEXT
