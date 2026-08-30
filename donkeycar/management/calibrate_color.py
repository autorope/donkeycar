"""
`donkey calibrate-color` -- work out the HSV window that isolates the tape.

The line follower finds the tape by thresholding hue, saturation and value, and
the default window is wide: hue 0-50 from saturation 50 up. That admits skin,
denim, ceiling lights and pale flooring, so a person walking past can capture
the histogram peak and swing the steering to full lock.

This measures the tape's actual colour in frames from your own car, in your own
lighting, and proposes a window around it -- then checks that window against
every frame you gave it, which is the part that tells you whether it will hold.

    donkey calibrate-color --images "~/frames/*.jpg"
    donkey calibrate-color --images "~/frames/*.jpg" --region 130,150,50,60
    donkey calibrate-color --images "~/frames/*.jpg" --pick
"""

from __future__ import annotations

import argparse
import glob
import itertools
import logging
import os
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Hue slack either side of the observed tape, in OpenCV's 0-179 scale.
DEFAULT_HUE_MARGIN = 7
# How far below the dimmest observed tape pixel to put the S/V floors. These
# floors are what reject the lighting, so they are the part worth tuning.
FLOOR_FRACTION = 0.80
# Percentiles used instead of min/max, so a few stray pixels cannot widen the
# window on their own.
LOW_PCT, HIGH_PCT = 1.0, 99.0


@dataclass(frozen=True)
class ColorStats:
    """What the sampled tape pixels actually look like."""

    pixels: int
    h_lo: int
    h_mid: int
    h_hi: int
    s_lo: int
    s_mid: int
    v_lo: int
    v_mid: int

    def describe(self) -> str:
        return (
            f"{self.pixels} sampled pixels\n"
            f"  hue        {self.h_lo}-{self.h_hi}  (median {self.h_mid})\n"
            f"  saturation {self.s_lo}+           (median {self.s_mid})\n"
            f"  value      {self.v_lo}+           (median {self.v_mid})"
        )


@dataclass(frozen=True)
class Threshold:
    low: tuple[int, int, int]
    high: tuple[int, int, int]

    def as_config(self) -> str:
        return f"COLOR_THRESHOLD_LOW  = {self.low}\nCOLOR_THRESHOLD_HIGH = {self.high}"


@dataclass(frozen=True)
class FrameResult:
    """How a threshold behaves on one frame."""

    name: str
    coverage: float  # percent of the scan band that matched
    peak_col: int | None  # where the histogram peak landed
    concentration: float  # percent of matches within +-20px of the peak
    status: str  # "ok" | "no-tape" | "occluded"

    @property
    def matched(self) -> bool:
        return self.status == "ok"

    def describe(self) -> str:
        if self.status == "occluded":
            return f"  {self.name:44s} scan band sits under the burned-in overlay -- cannot evaluate this frame"
        if self.status == "no-tape":
            return f"  {self.name:44s} no tape found (coverage {self.coverage:.1f}%)"
        return (
            f"  {self.name:44s} peak col {self.peak_col:3d}  "
            f"coverage {self.coverage:5.1f}%  concentration {self.concentration:5.1f}%"
        )


def to_hsv(bgr: np.ndarray) -> np.ndarray:
    """
    BGR file -> HSV the same way the follower sees it.

    LineFollower is handed RGB and converts with COLOR_RGB2HSV, so a file read
    by cv2 (BGR) has to go through RGB first or every hue comes out wrong.
    """
    return cv2.cvtColor(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), cv2.COLOR_RGB2HSV)


def detect_overlay_rows(bgr: np.ndarray, min_run: int = 4) -> tuple[int, int] | None:
    """
    Find a burned-in CV overlay band, if there is one.

    Frames captured with OVERLAY_IMAGE=True have the scan band replaced by the
    mask itself -- pure greyscale rows where the scene should be. Sampling those
    measures the follower's own previous output, so they are excluded and
    reported rather than silently used.
    """
    b, g, r = (bgr[:, :, i].astype(int) for i in range(3))
    grey = (np.abs(b - g) < 6) & (np.abs(g - r) < 6)
    rows = np.where(grey.mean(axis=1) > 0.90)[0]
    if rows.size < min_run:
        return None

    best: tuple[int, int] | None = None
    start = int(rows[0])
    for prev, cur in itertools.pairwise(rows):
        if cur != prev + 1:
            if best is None or (prev - start) > (best[1] - best[0]):
                best = (start, int(prev))
            start = int(cur)
    last = (start, int(rows[-1]))
    if best is None or (last[1] - last[0]) > (best[1] - best[0]):
        best = last
    return best if (best[1] - best[0] + 1) >= min_run else None


def auto_region(hsv: np.ndarray, skip_rows: tuple[int, int] | None = None) -> np.ndarray:
    """
    Pick the tape pixels without being told where they are.

    Tape is the strongly saturated, bright cluster; carpet and shadow are
    neither. Deliberately crude -- it only has to find enough true tape pixels
    for the percentiles to be meaningful, and `--region` exists for when it
    guesses wrong.
    """
    mask = np.ones(hsv.shape[:2], dtype=bool)
    if skip_rows is not None:
        mask[skip_rows[0] : skip_rows[1] + 1, :] = False
    # The top of the frame is usually horizon and lighting rather than floor.
    mask[: hsv.shape[0] // 3, :] = False

    s, v = hsv[:, :, 1], hsv[:, :, 2]
    strong = mask & (s > 120) & (v > 120)
    return hsv[strong]


def dominant_hue_cluster(pixels: np.ndarray, spread: int = 12) -> np.ndarray:
    """
    Keep only the pixels around the most common hue.

    A line-following scene usually holds more than one saturated colour --
    traffic cones, signage, a red jacket. Pooling them all pulls the hue window
    open until it admits everything, which is the problem this command exists to
    fix. The tape is the dominant coloured thing in view, so the histogram mode
    is a reasonable stand-in for "the tape" without hardcoding a colour.
    """
    hues = pixels[:, 0].astype(int)
    counts = np.bincount(hues, minlength=180)
    # Smooth first: a single noisy hue should not win over a broad true cluster.
    smoothed = np.convolve(counts, np.ones(5) / 5.0, mode="same")
    mode = int(np.argmax(smoothed))
    keep = np.abs(hues - mode) <= spread
    return pixels[keep]


def auto_region_all(
    frames: list[tuple[str, np.ndarray]],
) -> tuple[np.ndarray, list[str]]:
    """
    Gather tape pixels from every frame, not just the first.

    Sampling one frame makes the result hostage to whichever file sorts first --
    which may be a dark frame with no tape in it at all. Pooling also gives the
    percentiles more to work with, and spans whatever lighting variation the set
    happens to cover.

    Returns the pooled pixels and the frames that contributed.
    """
    pooled: list[np.ndarray] = []
    contributors: list[str] = []
    for name, bgr in frames:
        pixels = auto_region(to_hsv(bgr), skip_rows=detect_overlay_rows(bgr))
        if pixels.size:
            pooled.append(pixels)
            contributors.append(name)
    if not pooled:
        return np.empty((0, 3), dtype=np.uint8), []

    # Cluster once over everything, not per frame. Clustering each frame and
    # then pooling re-widens the window, because a frame whose dominant colour
    # is a traffic cone contributes its own cluster.
    return dominant_hue_cluster(np.concatenate(pooled, axis=0)), contributors


def region_pixels(hsv: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = region
    return hsv[y : y + h, x : x + w].reshape(-1, 3)


def measure(pixels: np.ndarray) -> ColorStats:
    """Summarise sampled pixels, using percentiles so outliers do not widen it."""
    if pixels.size == 0:
        raise ValueError(
            "No pixels to measure. Either no strongly coloured region was found, "
            "or the --region you gave is empty. Try --region or --pick."
        )
    h, s, v = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    return ColorStats(
        pixels=int(pixels.shape[0]),
        h_lo=int(np.percentile(h, LOW_PCT)),
        h_mid=int(np.percentile(h, 50)),
        h_hi=int(np.percentile(h, HIGH_PCT)),
        s_lo=int(np.percentile(s, LOW_PCT)),
        s_mid=int(np.percentile(s, 50)),
        v_lo=int(np.percentile(v, LOW_PCT)),
        v_mid=int(np.percentile(v, 50)),
    )


def propose(stats: ColorStats, hue_margin: int = DEFAULT_HUE_MARGIN) -> Threshold:
    """Turn measured tape colour into a threshold with a little slack."""
    h_lo = max(0, stats.h_lo - hue_margin)
    h_hi = min(179, stats.h_hi + hue_margin)
    s_lo = max(0, min(255, int(stats.s_lo * FLOOR_FRACTION)))
    v_lo = max(0, min(255, int(stats.v_lo * FLOOR_FRACTION)))
    return Threshold(low=(h_lo, s_lo, v_lo), high=(h_hi, 255, 255))


def evaluate(
    hsv: np.ndarray,
    threshold: Threshold,
    scan_y: int,
    scan_height: int,
    name: str = "",
    skip_rows: tuple[int, int] | None = None,
) -> FrameResult:
    """
    How the threshold behaves on the band the follower actually samples.

    Coverage alone says little: what matters is whether the matches cluster in
    one place. A wide threshold can match 20% of the band spread right across
    it, and the histogram peak then lands wherever the lighting happens to be
    brightest.
    """
    top = max(0, scan_y)
    bottom = min(hsv.shape[0], scan_y + scan_height)
    if skip_rows is not None:
        # Start below a burned-in overlay rather than measuring the old mask.
        top = max(top, skip_rows[1] + 1)
    if bottom <= top:
        # The requested band lies entirely under a burned-in overlay, so there
        # is nothing of the scene left to measure. Saying "no tape" here would
        # blame the threshold for a problem with the input.
        return FrameResult(name, 0.0, None, 0.0, "occluded")

    band = hsv[top:bottom, :, :]
    mask = cv2.inRange(band, np.asarray(threshold.low), np.asarray(threshold.high))
    coverage = float((mask > 0).mean() * 100.0)
    hist = mask.sum(axis=0)
    total = float(hist.sum())
    if total <= 0:
        return FrameResult(name, coverage, None, 0.0, "no-tape")

    peak = int(np.argmax(hist))
    near = float(hist[max(0, peak - 20) : peak + 21].sum()) / total
    return FrameResult(name, coverage, peak, near * 100.0, "ok")


def load_frames(pattern: str) -> list[tuple[str, np.ndarray]]:
    paths = sorted(glob.glob(os.path.expanduser(pattern)))
    frames = []
    for path in paths:
        bgr = cv2.imread(path)
        if bgr is None:
            logger.warning("Could not read %s, skipping", path)
            continue
        frames.append((os.path.basename(path), bgr))
    if not frames:
        raise ValueError(f"No readable images matched {pattern!r}")
    return frames


def pick_region(bgr: np.ndarray) -> tuple[int, int, int, int]:
    """Drag a box around the tape. Needs an OpenCV build with GUI support."""
    try:
        box = cv2.selectROI("Drag a box around the tape, then press ENTER", bgr, showCrosshair=True)
    except cv2.error as exc:  # pragma: no cover - depends on the OpenCV build
        raise ValueError(
            "This OpenCV build has no GUI support, so --pick is unavailable. Use --region X,Y,W,H instead."
        ) from exc
    finally:
        cv2.destroyAllWindows()
    if box[2] == 0 or box[3] == 0:
        raise ValueError("No region selected.")
    return (int(box[0]), int(box[1]), int(box[2]), int(box[3]))


def parse_region(text: str) -> tuple[int, int, int, int]:
    parts = text.split(",")
    if len(parts) != 4:
        raise ValueError(f"--region wants X,Y,W,H; got {text!r}")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"--region wants four whole numbers; got {text!r}") from exc
    if w <= 0 or h <= 0:
        raise ValueError(f"--region width and height must be positive; got {text!r}")
    return (x, y, w, h)


def run(args: list[str]) -> None:
    """Entry point for `donkey calibrate-color`."""
    try:
        _run(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _run(args: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="calibrate-color", usage="%(prog)s [options]")
    parser.add_argument("--images", required=True, help="glob of frames, e.g. '~/frames/*.jpg'")
    parser.add_argument("--region", default=None, help="sample this box on the first frame: X,Y,W,H")
    parser.add_argument("--pick", action="store_true", help="drag a box around the tape (needs an OpenCV GUI build)")
    parser.add_argument("--scan-y", type=int, default=100, help="SCAN_Y the car uses")
    parser.add_argument("--scan-height", type=int, default=20, help="SCAN_HEIGHT the car uses")
    parser.add_argument("--hue-margin", type=int, default=DEFAULT_HUE_MARGIN, help="hue slack either side")
    parser.add_argument("--compare", action="store_true", help="also show how the current defaults behave")
    parsed = parser.parse_args(args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    frames = load_frames(parsed.images)
    first = frames[0][1]

    with_overlay = [n for n, bgr in frames if detect_overlay_rows(bgr) is not None]
    if with_overlay:
        print(
            f"NOTE: {len(with_overlay)} of {len(frames)} frame(s) have a burned-in CV overlay.\n"
            f"      Those rows are the follower's own mask, not the scene, so they are\n"
            f"      excluded. For the cleanest result recapture with OVERLAY_IMAGE = False.\n"
        )

    hsv = to_hsv(first)
    if parsed.pick:
        pixels = dominant_hue_cluster(region_pixels(hsv, pick_region(first)))
    elif parsed.region:
        pixels = dominant_hue_cluster(region_pixels(hsv, parse_region(parsed.region)))
    else:
        pixels, contributors = auto_region_all(frames)
        if not contributors:
            raise ValueError(
                "No strongly coloured region found in any frame. Either none of them "
                "contain tape, or it is dimmer than the search expects. Point --region "
                "X,Y,W,H at the tape in one frame, or use --pick."
            )
        skipped = [n for n, _ in frames if n not in contributors]
        print(f"Sampled tape colour from {len(contributors)} of {len(frames)} frame(s).")
        if skipped:
            print(f"  no tape found in: {', '.join(skipped)}")
        print()

    stats = measure(pixels)
    threshold = propose(stats, parsed.hue_margin)

    print("Measured tape colour:")
    print(stats.describe())
    print("\nProposed threshold:\n")
    print(threshold.as_config())

    print(
        f"\nHow it behaves across {len(frames)} frame(s), on rows {parsed.scan_y}-{parsed.scan_y + parsed.scan_height}:"
    )
    print("(concentration is the share of matches within 20px of the peak -- higher is a tighter lock)")
    for fname, bgr in frames:
        skip = detect_overlay_rows(bgr)
        result = evaluate(to_hsv(bgr), threshold, parsed.scan_y, parsed.scan_height, fname, skip)
        print(result.describe())

    if parsed.compare:
        current = Threshold(low=(0, 50, 50), high=(50, 255, 255))
        print("\nFor comparison, the stock defaults (0,50,50)-(50,255,255):")
        for fname, bgr in frames:
            skip = detect_overlay_rows(bgr)
            result = evaluate(to_hsv(bgr), current, parsed.scan_y, parsed.scan_height, fname, skip)
            print(result.describe())

    print(
        "\nPaste the two lines above into your car's myconfig.py.\n"
        "The saturation and value floors are what reject lighting, so if tape in\n"
        "shadow stops being found, lower those before widening the hue."
    )
