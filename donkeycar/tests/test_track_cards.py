"""
Tests for assets/track-cards/check_legibility.py, the camera-legibility check.

They test the checker on small cards written here, not the real cards, so they
stay true while the cards are redrawn. Running the checker on the real cards is
how the cards themselves are checked.
"""

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "assets" / "track-cards" / "check_legibility.py"


@pytest.fixture(scope="module")
def cl():
    spec = importlib.util.spec_from_file_location("check_legibility", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_legibility"] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


OCTAGON = "108.6,40 191.4,40 250,98.6 250,181.4 191.4,240 108.6,240 50,181.4 50,98.6"
RING = "120.5,58 179.5,58 232,110.5 232,169.5 179.5,222 120.5,222 68,169.5 68,110.5"


def card(cl, body, background="#ffffff", inches=3.0):
    root = ET.fromstring(f'<g><rect width="300" height="300" fill="{background}"/>{body}</g>')
    return cl.Card("art-test", (0.0, 0.0, 300.0, 300.0), root, face_inches=inches, background=background)


def stop_sign(cl, rim, rim_width=6):
    return card(
        cl,
        f'<polygon points="{OCTAGON}" fill="#e3170a" stroke="{rim}" stroke-width="{rim_width}"/>'
        f'<polygon points="{RING}" fill="none" stroke="#ffffff" stroke-width="8"/>',
    )


# ------------------------------------------------------------- drawing rules


def test_a_card_that_follows_the_rules_passes(cl):
    good = card(cl, '<rect x="60" y="60" width="180" height="180" fill="#1e5bd6" stroke="#111111" stroke-width="10"/>')
    assert cl.check_rules(good) == []


@pytest.mark.parametrize(
    ("body", "background", "problem"),
    [
        (
            '<rect x="60" y="60" width="180" height="180" fill="#1e5bd6" stroke="#111111" stroke-width="10"/>',
            "#fdf7ee",
            "background #fdf7ee, not white",
        ),
        (
            '<circle cx="150" cy="150" r="60" fill="#3d8bd6" stroke="#111111" stroke-width="10"/>',
            "#ffffff",
            "fill #3d8bd6 is not in the palette",
        ),
        (
            '<circle cx="150" cy="150" r="60" fill="#1e5bd6" stroke="#111111" stroke-width="3"/>',
            "#ffffff",
            "stroke-width 3 (3 units) under 6",
        ),
        (
            '<circle cx="150" cy="150" r="60" fill="#1e5bd6" stroke="#7a7a7a" stroke-width="10"/>',
            "#ffffff",
            "no black (#111111) outline",
        ),
        (
            '<circle cx="150" cy="150" r="60" fill="#1e5bd6" opacity=".3" stroke="#111111" stroke-width="10"/>',
            "#ffffff",
            "translucent <circle>",
        ),
        (
            '<rect x="60" y="60" width="180" height="180" fill="#ffffff" stroke="#111111" stroke-width="10"/>'
            '<text font-size="24">12</text>',
            "#ffffff",
            "text 24 units tall",
        ),
    ],
)
def test_each_rule_is_reported(cl, body, background, problem):
    problems = cl.check_rules(card(cl, body, background))
    assert any(problem in p for p in problems), problems


def test_every_palette_colour_passes_its_own_rules(cl):
    """The palette must not contain a colour the rules would reject."""
    for colour in cl.PALETTE:
        body = f'<circle cx="150" cy="150" r="60" fill="{colour}" stroke="#111111" stroke-width="10"/>'
        assert cl.check_rules(card(cl, body)) == [], colour


def test_only_the_amber_lamp_is_near_the_tape_window(cl):
    """The car follows yellow tape at OpenCV hue 17-37; nothing on a card may sit in that window."""
    for colour in cl.PALETTE:
        hue, sat, _val = cl._hsv(colour)
        if colour not in cl.NEUTRAL and sat > 0.2:
            assert not (cl.TAPE_HUE[0] <= hue <= cl.TAPE_HUE[1]), (colour, hue)


def test_the_real_cards_load(cl):
    names = {c.name for c in cl.load_cards()}
    assert {"art-stop", "art-red", "art-yellow", "art-green", "art-stop-large"} <= names
    assert len(names) == 14


# ---------------------------------------------------------- camera simulation


def test_a_dark_rim_drops_out_of_a_red_mask(cl):
    """
    The field result the simulation is fitted to: a stop sign with a dark red
    rim, boxed by colour, comes out several pixels small.
    """
    sign = stop_sign(cl, "#7a1119")
    result = cl.measure_sign(sign, "640x480", 24.0, "room")
    assert result["colour"] <= -2.0


def test_a_red_to_the_edge_sign_is_boxed_within_a_pixel(cl):
    sign = stop_sign(cl, "#e3170a")
    for resolution in cl.RESOLUTIONS:
        for distance in cl.DISTANCES_IN:
            result = cl.measure_sign(sign, resolution, distance, "room")
            assert result["edge"] is not None and abs(result["edge"]) <= 1.0, (resolution, distance, result)


def test_the_edge_box_is_not_fooled_by_a_post(cl):
    """The column walk must not run up the sign's post into the octagon."""
    sign = card(
        cl,
        '<rect x="140" y="196" width="20" height="92" fill="#7a7a7a" stroke="#111111" stroke-width="8"/>'
        f'<polygon points="{OCTAGON}" fill="#e3170a" stroke="#e3170a" stroke-width="6"/>'
        f'<polygon points="{RING}" fill="none" stroke="#ffffff" stroke-width="8"/>',
    )
    result = cl.measure_sign(sign, "640x480", 24.0, "room")
    assert abs(result["edge"]) <= 1.0, result


def test_the_simulated_white_card_is_blue_as_in_the_field(cl):
    import cv2
    import numpy as np

    frame = cl.simulate(np.full((40, 40, 3), 255, np.uint8), 64, 48, "room")
    h, s, v = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[24, 32]
    # Field: hue 101, saturation 96, brightness 189
    assert 90 <= h <= 112 and 70 <= s <= 120 and 165 <= v <= 210, (h, s, v)


@pytest.mark.parametrize(
    ("hue", "called"), [(2.0, "red"), (176.0, "red"), (13.0, "amber"), (74.0, "green"), (110.0, "unknown")]
)
def test_lamp_colour_by_hue(cl, hue, called):
    assert cl.lamp_colour(hue) == called
