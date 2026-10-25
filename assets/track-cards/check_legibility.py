"""
How well can the car's camera read the track cards?

    python assets/track-cards/check_legibility.py

Two kinds of check, so a card is held to numbers rather than judged by eye on a
monitor (which is how the first set came out pastel on cream):

* Drawing rules, from each card's SVG source: a white background, every colour
  from the palette below, no translucent fills, a black outline, and nothing
  too thin or too small to survive 320x240.
* A camera simulation, for the cards whose job is to be measured or told apart
  by colour -- the stop signs and the traffic lights. The card is drawn at the
  size it would appear at 2 and 4 feet through the car's own lens, then
  dimmed, blurred and JPEG-compressed, and the stop sign is boxed the two ways
  an agent's helper would: by colour alone, and by colour refined to the edge.

Exits non-zero when any card misses a target, so a redrawn card is checked by
running this. It needs only OpenCV and NumPy: the simulated cards are drawn
from their polygons, circles and rectangles directly, without a browser.
"""

from __future__ import annotations

import colorsys
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CARDS_HTML = HERE / "track-cards.html"
LARGE_SIGN_HTML = HERE / "stop-sign-large.html"

# --------------------------------------------------------------------- palette
#
# Every colour on a card comes from here. Red, amber and green are reserved for
# the stop sign and the three lamps, so a colour mask for one cannot catch
# another prop. OpenCV hue is 0..179; the car's yellow tape window is 17..37.

PALETTE: dict[str, str] = {
    "#ffffff": "white: backgrounds, lettering, number panels",
    "#111111": "black: outlines, lettering, housings",
    "#3c3c3c": "dark grey: tyres, shadows",
    "#7a7a7a": "mid grey: roads, posts, details",
    "#b4b4b4": "light grey: unlit lamps (dark grey ones read the same blue as the housing)",
    "#e3170a": "signal red, reserved: stop sign, red lamp (hue 2)",
    "#ff7000": "amber, reserved: yellow lamp (hue 13, 4 below the tape window)",
    "#00b050": "green, reserved: green lamp (hue 74)",
    "#1e5bd6": "blue: car, clothing (hue 110)",
    "#009a9a": "teal: truck, clothing (hue 90)",
    "#7b3f12": "brown: hair, dog, wood (hue 13, too dark for the tape window)",
    "#e0a070": "skin (hue 12; below the saturation floor on purpose: skin must look like skin)",
}
NEUTRAL = {"#ffffff", "#111111", "#3c3c3c", "#7a7a7a", "#b4b4b4"}
EXEMPT_SATURATION = {"#e0a070"}
TAPE_HUE = (17, 37)

MIN_SATURATION = 0.70
MAX_COLOUR_LUMINANCE = 0.85  # of white's; a colour this light reads as white under room light
MIN_STROKE_UNITS = 6.0  # of a 300-unit, 3-inch face: 0.06 in
MIN_OUTLINE_UNITS = 8.0
MIN_TEXT_UNITS = 40.0
# The stop signs are red to the edge on purpose: a black or dark rim drops out
# of a red colour mask and boxes the sign small (plan D3).
OUTLINE_EXEMPT = {"art-stop", "art-stop-large"}
# After the camera, a stop sign's face must stay clear of purple and magenta,
# which the venue's decorations share and the old crimson drifted toward.
FACE_HUE_FORBIDDEN = (140.0, 170.0)
# Below this an octagon is a dozen coloured pixels, and their hue is mostly noise
# (a 3 in card at 4 ft at 320x240 is 6.8 px); only its size is checked.
MIN_FACE_HUE_PX = 10.0
# Below this a red or amber lamp blurs into its black housing, which room light
# turns blue, and hue alone cannot tell it: at 5.4 px (a 3 in card at 4 ft at
# 640x480) red read as hue 100. Every lamp read right at 10.8 px.
MIN_LAMP_PX = 8.0
# The lit lamp must out-saturate the most saturated unlit lamp by this much
# (of 255) after the camera, or which lamp is lit is a guess.
MIN_LAMP_MARGIN = 60.0

# --------------------------------------------------------------------- camera
#
# The car's measured lens at 640x480 (fx 315); at 320x240 it is half that.

FOCAL_640 = 315.0
RESOLUTIONS = {"640x480": (640, 480, FOCAL_640), "320x240": (320, 240, FOCAL_640 / 2)}
DISTANCES_IN = (24.0, 48.0)
BLUR_SIGMA_640 = 1.0  # px at 640x480; measured edges on the car are about this soft
JPEG_QUALITY = 75

# The camera's colour response, per BGR channel in linear light: out = flare + gain * printed.
# Fitted to the O7 frame of the printed large stop sign at 24 in under room light
# (2026-10-24): the white card came out blue (gray 153, hue 101, saturation 96 of 255),
# the crimson face hue 172, and the dark red border lost its red entirely (hue 110-160,
# saturation 61-85) -- which is why a red mask boxed the sign 3-5 px small. "dim" is the
# same light at 60%.
LIGHTS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "room": ((0.035, 0.018, 0.0), (0.466, 0.352, 0.20)),
    "dim": ((0.021, 0.011, 0.0), (0.280, 0.211, 0.12)),
}


@dataclass
class Card:
    """One card face: its SVG elements, viewBox, and the inches its viewBox spans."""

    name: str
    viewbox: tuple[float, float, float, float]
    root: ET.Element
    face_inches: float
    background: str | None = None
    problems: list[str] = field(default_factory=list)


ViewBox = tuple[float, float, float, float]


def _symbols(html: str) -> dict[str, tuple[ViewBox, ET.Element]]:
    found: dict[str, tuple[ViewBox, ET.Element]] = {}
    for match in re.finditer(r'<symbol id="([^"]+)" viewBox="([^"]+)">(.*?)</symbol>', html, re.S):
        name, box, body = match.groups()
        x, y, w, h = (float(v) for v in box.split())
        found[name] = ((x, y, w, h), ET.fromstring(f"<g>{body}</g>"))
    return found


def _num(element: ET.Element, name: str, default: float = 0.0) -> float:
    value = element.get(name)
    return default if value is None else float(value)


def load_cards(cards_html: Path = CARDS_HTML, large_html: Path = LARGE_SIGN_HTML) -> list[Card]:
    cards = []
    for name, (box, root) in _symbols(cards_html.read_text()).items():
        card = Card(name, box, root, face_inches=3.0)
        first = root.find("rect")
        if first is not None and first.get("width") == str(int(box[2])) and first.get("height") == str(int(box[3])):
            card.background = (first.get("fill") or "").lower()
        cards.append(card)
    if large_html.exists():
        text = large_html.read_text()
        for name, (box, root) in _symbols(text).items():
            # The large sign's symbol is the octagon alone; its background is the page's
            page = re.search(r"\.page\s*\{[^}]*background:\s*(#[0-9a-fA-F]{3,6})", text)
            sign = re.search(r"\.sign\s*\{[^}]*width:\s*([0-9.]+)in", text)
            if sign is None:
                raise ValueError(f"{large_html}: no .sign width, so the octagon's size is unknown")
            background = page.group(1).lower() if page else None
            cards.append(Card(name, box, root, face_inches=float(sign.group(1)), background=background))
    return cards


# ------------------------------------------------------------------- the rules


def _colour(value: str | None) -> str | None:
    if not value or value == "none":
        return None
    value = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(c * 2 for c in value[1:])
    return value


def _luminance(hex_colour: str) -> float:
    """Relative luminance, 0 for black to 1 for white: how bright a colour looks, not its largest channel."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _hsv(hex_colour: str) -> tuple[float, float, float]:
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 180, s, v * 255


def check_rules(card: Card) -> list[str]:
    """Every rule the SVG source breaks, in words."""
    problems = []
    scale = 300.0 / card.viewbox[2]  # express sizes as units of a 300-unit face
    if card.background != "#ffffff":
        problems.append(f"background {card.background or 'not found'}, not white")
    outlined = False
    for element in card.root.iter():
        for attr in ("fill", "stroke"):
            colour = _colour(element.get(attr))
            if colour is None or not colour.startswith("#"):
                continue
            if colour not in PALETTE:
                problems.append(f"{attr} {colour} is not in the palette")
                continue
            if colour not in NEUTRAL and colour not in EXEMPT_SATURATION:
                _hue, sat, _val = _hsv(colour)
                if sat < MIN_SATURATION:
                    problems.append(f"{attr} {colour} saturation {sat:.0%} under {MIN_SATURATION:.0%}")
                if _luminance(colour) > MAX_COLOUR_LUMINANCE:
                    problems.append(f"{attr} {colour} too close to white")
        if element.get("opacity") not in (None, "1"):
            problems.append(f"translucent <{element.tag}> (opacity {element.get('opacity')})")
        width = element.get("stroke-width")
        if width is not None and _colour(element.get("stroke")):
            units = float(width) * scale
            if units < MIN_STROKE_UNITS:
                problems.append(f"stroke-width {width} ({units:.0f} units) under {MIN_STROKE_UNITS:.0f}")
            if _colour(element.get("stroke")) == "#111111" and units >= MIN_OUTLINE_UNITS:
                outlined = True
        size = element.get("font-size")
        if size is not None and float(size) * scale < MIN_TEXT_UNITS:
            problems.append(f"text {size} units tall, under {MIN_TEXT_UNITS:.0f}")
    if not outlined and card.name not in OUTLINE_EXEMPT:
        problems.append(f"no black (#111111) outline of at least {MIN_OUTLINE_UNITS:.0f} units")
    return sorted(set(problems))


# ------------------------------------------------------------------ rendering


def _bgr(hex_colour: str) -> tuple[int, int, int]:
    return int(hex_colour[5:7], 16), int(hex_colour[3:5], 16), int(hex_colour[1:3], 16)


def render(card: Card, size_px: int, supersample: int = 4, pad_px: int = 0) -> np.ndarray:
    """
    The card face as BGR pixels, size_px across, drawn from its rects, circles,
    ellipses and polygons. Paths and text are left out: the cards simulated here
    are measured by their outer shapes, which are never paths.
    """
    big = size_px * supersample
    pad = pad_px * supersample
    x0, y0, w, _h = card.viewbox
    s = big / w
    canvas = np.full((big + 2 * pad, big + 2 * pad, 3), _bgr(card.background or "#ffffff"), np.uint8)

    def pt(x: float, y: float) -> tuple[int, int]:
        return round((x - x0) * s) + pad, round((y - y0) * s) + pad

    for el in card.root.iter():
        fill, stroke = _colour(el.get("fill")), _colour(el.get("stroke"))
        sw = max(1, round(float(el.get("stroke-width", "0")) * s)) if stroke else 0
        if el.tag == "polygon":
            nums = [float(v) for v in re.split(r"[ ,]+", el.get("points", "").strip())]
            poly = np.array([pt(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)], np.int32)
            if fill:
                cv2.fillPoly(canvas, [poly], _bgr(fill), cv2.LINE_AA)
            if stroke:
                cv2.polylines(canvas, [poly], True, _bgr(stroke), sw, cv2.LINE_AA)
        elif el.tag == "circle":
            c, r = pt(_num(el, "cx"), _num(el, "cy")), round(_num(el, "r") * s)
            if fill:
                cv2.circle(canvas, c, r, _bgr(fill), -1, cv2.LINE_AA)
            if stroke:
                cv2.circle(canvas, c, r, _bgr(stroke), sw, cv2.LINE_AA)
        elif el.tag == "rect" and el is not card.root.find("rect"):
            a = pt(_num(el, "x"), _num(el, "y"))
            b = pt(_num(el, "x") + _num(el, "width"), _num(el, "y") + _num(el, "height"))
            if fill:
                cv2.rectangle(canvas, a, b, _bgr(fill), -1, cv2.LINE_AA)
            if stroke:
                cv2.rectangle(canvas, a, b, _bgr(stroke), sw, cv2.LINE_AA)
    out = size_px + 2 * pad_px
    return cv2.resize(canvas, (out, out), interpolation=cv2.INTER_AREA)


def octagon_extent_units(card: Card) -> float:
    """The stop sign's outer width across the flats, stroke included, in viewBox units."""
    outer = card.root.find("polygon")
    if outer is None:
        raise ValueError(f"{card.name} has no polygon to measure")
    nums = [float(v) for v in re.split(r"[ ,]+", outer.get("points", "").strip())]
    xs = nums[0::2]
    stroke = float(outer.get("stroke-width", "0")) if _colour(outer.get("stroke")) else 0.0
    return max(xs) - min(xs) + stroke


def simulate(face: np.ndarray, width: int, height: int, light: str, seed: int = 0) -> np.ndarray:
    """
    The face as the camera would deliver it: centred in a dim room, through the
    measured colour response for `light`, then blurred, noised and
    JPEG-compressed.
    """
    rng = np.random.default_rng(seed)
    scene = np.full((height, width, 3), (70, 80, 90), np.float64)  # a dim, warm-grey room
    fh, fw = face.shape[:2]
    top, left = (height - fh) // 2, (width - fw) // 2
    scene[top : top + fh, left : left + fw] = face
    flare, gain = (np.array(v) for v in LIGHTS[light])
    linear = flare + gain * (scene / 255.0) ** 2.2
    srgb = np.clip(linear, 0, 1) ** (1 / 2.2) * 255
    blurred = cv2.GaussianBlur(srgb, (0, 0), BLUR_SIGMA_640 * width / 640)
    noisy = np.clip(blurred + rng.normal(0, 3.0, blurred.shape), 0, 255).astype(np.uint8)
    _ok, jpeg = cv2.imencode(".jpg", noisy, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return np.asarray(cv2.imdecode(jpeg, cv2.IMREAD_COLOR))


# ------------------------------------------------------------- finding the sign


def red_mask(bgr: np.ndarray) -> np.ndarray:
    """
    What a helper script would call red: the thresholds that found the sign in
    the field once the strict ones (saturation 90) had boxed a shelf instead.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    low = cv2.inRange(hsv, (0, 60, 30), (8, 255, 255))
    high = cv2.inRange(hsv, (160, 60, 30), (180, 255, 255))
    return np.asarray(cv2.bitwise_or(low, high))


def colour_box(bgr: np.ndarray) -> tuple[float, float, float, float] | None:
    """
    The bounding box of the largest red blob, its pieces either side of the
    white ring joined: the simplest box an agent's helper draws.
    """
    mask = cv2.morphologyEx(red_mask(bgr), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _a = stats[i]
    return float(x), float(y), float(x + w), float(y + h)


def _inward(profile: np.ndarray, thr: float, start: int, step: int, stop: int) -> float | None:
    """Sub-pixel position where the profile first drops below thr, walking from start toward stop."""
    i = start
    while (i + step - stop) * step <= 0:
        a, b = profile[i], profile[i + step]
        if a >= thr > b:
            return i + step * (a - thr) / (a - b)
        i += step
    return None


def edge_box(bgr: np.ndarray) -> tuple[float, float, float, float] | None:
    """
    The colour box refined to the sign's true outer edge. Along its middle row
    and column, walk inward from the white card around it and take the first
    drop to halfway between the card and the sign: the octagon's outer edge,
    whatever colour its rim is. Walking inward means the white ring and
    lettering inside the sign cannot be mistaken for the card.
    """
    seed = colour_box(bgr)
    if seed is None:
        return None
    x0, y0, x1, y1 = (int(v) for v in seed)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(float)
    cy = (y0 + y1) // 2
    # Columns a little right of centre: still on the octagon's flat top and
    # bottom (the middle 40% of its width), but clear of a post below it.
    cx = (x0 + x1) // 2 + max(1, round(0.12 * (x1 - x0)))
    # The colour box can sit well inside the sign when its rim is not red, so
    # start far enough out to be on the card, and judge the card by its
    # brightest pixels: beyond a small card's margin is the darker room.
    margin = max(4, (x1 - x0) // 2)
    row, col = g[cy], g[:, cx]
    ring = np.concatenate(
        [
            row[max(0, x0 - margin) : x0],
            row[x1 + 1 : x1 + margin + 1],
            col[max(0, y0 - margin) : y0],
            col[y1 + 1 : y1 + margin + 1],
        ]
    )
    card = np.percentile(ring, 90)
    sign = np.percentile(row[x0 : x1 + 1], 10)  # the sign's darker tones, not its white ring or letters
    thr = (card + sign) / 2
    mid = (x0 + x1) // 2
    box = (
        _inward(row, thr, max(0, x0 - margin), 1, mid),
        _inward(col, thr, max(0, y0 - margin), 1, cy),
        _inward(row, thr, min(len(row) - 1, x1 + margin), -1, mid),
        _inward(col, thr, min(len(col) - 1, y1 + margin), -1, cy),
    )
    left, top, right, bottom = box
    if left is None or top is None or right is None or bottom is None:
        return None
    return left, top, right, bottom


def measure_sign(card: Card, resolution: str, distance_in: float, light: str) -> dict[str, float | None]:
    """Draw the sign at this range, simulate the camera, and box it both ways."""
    width, height, focal = RESOLUTIONS[resolution]
    px_per_unit = focal * card.face_inches / distance_in / card.viewbox[2]
    face_px = max(8, round(card.viewbox[2] * px_per_unit))
    true_px = octagon_extent_units(card) * px_per_unit
    frame = simulate(render(card, face_px, pad_px=max(6, face_px // 3)), width, height, light)
    out: dict[str, float | None] = {"true_px": true_px}
    for name, finder in (("colour", colour_box), ("edge", edge_box)):
        box = finder(frame)
        out[name] = None if box is None else ((box[2] - box[0]) + (box[3] - box[1])) / 2 - true_px
    out["face_hue"] = face_hue(frame)
    return out


def face_hue(bgr: np.ndarray) -> float | None:
    """The stop sign face's hue after the camera: the circular mean over its red pixels."""
    box = colour_box(bgr)
    if box is None:
        return None
    x0, y0, x1, y1 = (int(v) for v in box)
    hsv = cv2.cvtColor(bgr[y0 : y1 + 1, x0 : x1 + 1], cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(float)
    # The face's saturated core only: blurred edge pixels are part white card,
    # and the card is blue under room light, so they drag the hue toward purple.
    reddish = hsv[hsv[:, 1] >= 60]
    if len(reddish) == 0:
        return None
    red = reddish[reddish[:, 1] >= np.percentile(reddish[:, 1], 67)]
    angle = red[:, 0] * np.pi / 90
    return float((np.degrees(np.arctan2(np.sin(angle).mean(), np.cos(angle).mean())) / 2) % 180)


# ------------------------------------------------------------------- the lamps


def lamp_colour(hue: float) -> str:
    # Room light pulls amber down toward red, so the split between them is at 5:
    # red reads 173-179 or 0-2 through the camera, amber 9 and up.
    for name, (lo, hi) in {"red": (0, 5), "amber": (5, 25), "green": (50, 100)}.items():
        if lo <= hue < hi:
            return name
    return "red" if hue >= 165 else "unknown"


def lit_lamp(card: Card, resolution: str, distance_in: float, light: str) -> tuple[float | None, float, float]:
    """
    The lit lamp's hue after the camera simulation, the lamp's diameter in
    pixels, and how much more saturated the lit lamp is than the most
    saturated unlit one (0..255). The lamps are found the way a helper that
    knows the housing would find them: each of the three is sampled on its own
    and the lit one is the most saturated. Room light turns every grey blue
    (the white card reads saturation 96 of 255 in the field), and the amber
    lamp comes out barely more saturated than that, so saturation is judged
    after balancing the frame on the card's own white beside the housing. The
    hue reported is the unbalanced one, as the car's tape mask would see it.
    """
    width, height, focal = RESOLUTIONS[resolution]
    px_per_unit = focal * card.face_inches / distance_in / card.viewbox[2]
    face_px = round(card.viewbox[2] * px_per_unit)
    lamps = [c for c in card.root.iter("circle") if _num(c, "r") >= 30]
    lamp_px = 2 * max(_num(c, "r") for c in lamps) * px_per_unit
    frame = simulate(render(card, face_px), width, height, light)
    top, left = (height - face_px) // 2, (width - face_px) // 2
    # White card between its left edge and the housing (x 10..50 of 300)
    white = frame[
        top + round(100 * px_per_unit) : top + round(200 * px_per_unit),
        left + round(10 * px_per_unit) : left + round(50 * px_per_unit),
    ]
    white_bgr = white.reshape(-1, 3).astype(float).mean(axis=0)
    balanced = np.clip(frame * (white_bgr.max() / white_bgr), 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    balanced_sat = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)[:, :, 1]
    ys, xs = np.mgrid[0:height, 0:width]
    sampled, saturation = [], []
    for lamp in lamps:
        cx = left + _num(lamp, "cx") * px_per_unit
        cy = top + _num(lamp, "cy") * px_per_unit
        # The middle 60% of the lamp, clear of the housing blurred over its rim
        inside = (xs - cx) ** 2 + (ys - cy) ** 2 <= (0.6 * _num(lamp, "r") * px_per_unit) ** 2
        sampled.append(hsv[inside].astype(float))
        saturation.append(float(np.median(balanced_sat[inside])) if inside.any() else 0.0)
    if any(len(s) < 4 for s in sampled):
        return None, lamp_px, 0.0
    order = np.argsort(saturation)
    lit = sampled[order[-1]]
    margin = saturation[order[-1]] - saturation[order[-2]]
    # Hue is circular; average it as an angle so reds near 0 and 179 agree
    angle = lit[:, 0] * np.pi / 90
    hue = float((np.degrees(np.arctan2(np.sin(angle).mean(), np.cos(angle).mean())) / 2) % 180)
    return hue, lamp_px, margin


# ------------------------------------------------------------------- the report


def run(cards: list[Card]) -> int:
    failures = 0
    print(f"{'card':22s} drawing rules")
    for card in cards:
        card.problems = check_rules(card)
        failures += bool(card.problems)
        print(f"{card.name:22s} {'ok' if not card.problems else '; '.join(card.problems)}")

    signs = [c for c in cards if c.name.startswith("art-stop")]
    print("\nstop sign: box error in px (measured minus true), by colour alone and refined to the edge")
    for card in signs:
        for res in RESOLUTIONS:
            for dist in DISTANCES_IN:
                for light in LIGHTS:
                    m = measure_sign(card, res, dist, light)
                    hue = m["face_hue"]
                    too_small = (m["true_px"] or 0.0) < MIN_FACE_HUE_PX
                    in_purple = hue is None or FACE_HUE_FORBIDDEN[0] <= hue <= FACE_HUE_FORBIDDEN[1]
                    hue_ok = too_small or not in_purple
                    edge_ok = m["edge"] is not None and abs(m["edge"]) <= 1.0 and hue_ok
                    failures += not edge_ok
                    fmt = lambda v: "none" if v is None else f"{v:+.1f}"  # noqa: E731
                    print(
                        f"{card.name:16s} {res} {dist:3.0f} {light:4s}: true {m['true_px']:5.1f}  "
                        f"colour {fmt(m['colour'])}  edge {fmt(m['edge'])}  "
                        f"face hue {'too small' if too_small else fmt(hue)}  "
                        f"{'ok' if edge_ok else 'MISS'}"
                    )

    lights = {"art-red": "red", "art-yellow": "amber", "art-green": "green"}
    print("\ntraffic lights: the lit lamp's hue after the camera, and what hue alone calls it")
    for card in cards:
        if card.name not in lights:
            continue
        for res in RESOLUTIONS:
            for dist in DISTANCES_IN:
                for light in LIGHTS:
                    hue, lamp_px, margin = lit_lamp(card, res, dist, light)
                    if lamp_px < MIN_LAMP_PX:
                        print(f"{card.name:12s} {res} {dist:3.0f} {light:4s}: lamp {lamp_px:4.1f} px, too small  ok")
                        continue
                    called = "unknown" if hue is None else lamp_colour(hue)
                    in_tape = hue is not None and TAPE_HUE[0] <= hue <= TAPE_HUE[1]
                    ok = called == lights[card.name] and not in_tape and margin >= MIN_LAMP_MARGIN
                    failures += not ok
                    shown = "none" if hue is None else f"{hue:5.1f}"
                    verdict = "ok" if ok else "MISS"
                    where = f"{card.name:12s} {res} {dist:3.0f} {light:4s}"
                    label = f"{called:7s} by {margin:3.0f} sat"
                    print(f"{where}: lamp {lamp_px:4.1f} px, hue {shown} -> {label}  {verdict}")

    print(f"\n{failures} miss(es)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(load_cards()))
