"""
How far away is an object of known size, from its bounding box?

The agent sees a stop sign, draws a box round it, and knows the sign is six
inches tall. With the camera's intrinsics that is enough for a distance: the
box's top and bottom edges are two rays out of the camera, the angle between
them is how big the sign looks, and a six-inch sign that looks that big is that
far away.

Measured as an angle between rays rather than as a span on the image plane, so
the answer does not depend on how far the camera is pitched down. A span on the
image plane shrinks with the pitch -- by 6% at 20 degrees -- for an upright sign
seen by a camera that is not; the angle it subtends does not.

What is assumed, and said to the agent with every answer: the object is upright
and turned roughly toward the camera, the box is tight, and the box's edges are
where the object's edges are. A box is axis-aligned, so on a tilted camera it
cannot say which row of the object set its width, which is why the width
estimate is the weaker of the two close up.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, NamedTuple

import cv2
import numpy as np

from donkeycar.parts.camera_intrinsics import CameraIntrinsics
from donkeycar.parts.cv_calibration import Calibration

#: How wrong each box edge is assumed to be, for the uncertainty reported
EDGE_ERROR_PX = 1.0

BOX_KEYS = ("x_min", "y_min", "x_max", "y_max")

NOTE = (
    "Assumes the object is upright and turned roughly toward the camera, and that the box is tight "
    "round it. Accuracy falls toward the frame edges and for small boxes. range_uncertainty_inches "
    f"assumes each box edge is within {EDGE_ERROR_PX:g} px; widen it if your box is rougher than that."
)


class Box(NamedTuple):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)


def parse_box(raw: object) -> Box:
    """A box from the agent's `{x_min, y_min, x_max, y_max}`, or a ValueError saying what is wrong."""
    if not isinstance(raw, dict):
        raise ValueError(f"box must be an object with {', '.join(BOX_KEYS)}, in pixels")
    missing = [key for key in BOX_KEYS if key not in raw]
    unknown = sorted(set(raw) - set(BOX_KEYS))
    if missing or unknown:
        problems = []
        if missing:
            problems.append(f"missing {', '.join(missing)}")
        if unknown:
            problems.append(f"unknown {', '.join(unknown)}")
        raise ValueError(f"box needs exactly {', '.join(BOX_KEYS)}; {'; '.join(problems)}")
    try:
        box = Box(*(float(raw[key]) for key in BOX_KEYS))
    except (TypeError, ValueError) as exc:
        raise ValueError("box coordinates must be numbers, in pixels") from exc
    if box.x_max <= box.x_min or box.y_max <= box.y_min:
        raise ValueError(
            "box must have x_max > x_min and y_max > y_min: a box with no width or height measures nothing"
        )
    return box


def check_sizes(width_inches: float | None, height_inches: float | None) -> None:
    if width_inches is None and height_inches is None:
        raise ValueError("Give the object's real size: width_inches, height_inches, or both.")
    for name, value in (("width_inches", width_inches), ("height_inches", height_inches)):
        if value is not None and not value > 0:
            raise ValueError(f"{name} must be positive")


def check_in_frame(box: Box, image_w: int, image_h: int) -> None:
    if box.x_min < 0 or box.y_min < 0 or box.x_max > image_w or box.y_max > image_h:
        raise ValueError(
            f"box ({box.x_min:g}, {box.y_min:g})-({box.x_max:g}, {box.y_max:g}) "
            f"is outside the {image_w}x{image_h} frame"
        )


def _rays(intrinsics: CameraIntrinsics, pixels: list[tuple[float, float]]) -> np.ndarray:
    """Unit rays out of the camera through these pixels, lens distortion removed."""
    normalised = intrinsics.undistort_points(np.asarray(pixels, dtype=np.float64))
    rays = np.hstack([normalised, np.ones((len(normalised), 1))])
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)


def _range_from_span(
    intrinsics: CameraIntrinsics, a: tuple[float, float], b: tuple[float, float], size: float
) -> float:
    """Distance at which `size` inches subtends the angle between the rays through `a` and `b`."""
    ray_a, ray_b = _rays(intrinsics, [a, b])
    angle = math.acos(float(np.clip(ray_a @ ray_b, -1.0, 1.0)))
    return size / (2 * math.tan(angle / 2))


def _ranges(box: Box, intrinsics: CameraIntrinsics, width: float | None, height: float | None) -> dict[str, float]:
    cx, cy = box.centre
    found = {}
    if width is not None:
        found["width"] = _range_from_span(intrinsics, (box.x_min, cy), (box.x_max, cy), width)
    if height is not None:
        found["height"] = _range_from_span(intrinsics, (cx, box.y_min), (cx, box.y_max), height)
    return found


def _uncertainty(box: Box, intrinsics: CameraIntrinsics, size: float, along: str) -> float:
    """How far the range moves when each of the two edges it uses is EDGE_ERROR_PX out."""
    base = _ranges(box, intrinsics, size if along == "width" else None, size if along == "height" else None)[along]
    shifts = []
    lo, hi = ("x_min", "x_max") if along == "width" else ("y_min", "y_max")
    for edge, sign in ((lo, -1), (hi, 1)):
        moved = box._replace(**{edge: getattr(box, edge) + sign * EDGE_ERROR_PX})
        shifted = _ranges(moved, intrinsics, size if along == "width" else None, size if along == "height" else None)
        shifts.append(shifted[along] - base)
    return math.sqrt(sum(s * s for s in shifts))


def camera_pose_on_ground(ground: Calibration, intrinsics: CameraIntrinsics) -> tuple[np.ndarray, np.ndarray] | None:
    """
    The camera's rotation and translation relative to the floor, or None.

    The floor homography maps pixels to the floor and the intrinsics say how
    the lens bends rays; together they fix where the camera is. Solved by
    sampling floor points the homography knows, in the band of the image where
    the board was laid, and fitting the camera to them with its real lens.
    """
    if ground.homography is None:
        return None
    rows = np.linspace(min(ground.scan_y, ground.image_h - 1), ground.image_h - 1, 8)
    cols = np.linspace(ground.image_w * 0.2, ground.image_w * 0.8, 8)
    pixels, floor = [], []
    for v in rows:
        for u in cols:
            lateral, forward = ground.image_to_ground(float(u), float(v))
            if np.isfinite(lateral) and np.isfinite(forward):
                pixels.append((u, v))
                floor.append((lateral, forward, 0.0))
    if len(pixels) < 6:
        return None
    ok, rvec, tvec = cv2.solvePnP(
        np.asarray(floor, dtype=np.float64),
        np.asarray(pixels, dtype=np.float64),
        intrinsics.camera_matrix(),
        intrinsics.distortion_array(),
    )
    if not ok:
        return None
    rotation, _ = cv2.Rodrigues(rvec)
    return rotation, tvec.reshape(3)


def unknown(reason: str) -> dict[str, Any]:
    """The answer when there is no usable camera calibration: not an error, just not known."""
    return {
        "known": False,
        "reason": reason,
        "range_inches": None,
        "range_from_width_inches": None,
        "range_from_height_inches": None,
        "size_disagreement": None,
        "range_uncertainty_inches": None,
        "forward_inches": None,
        "lateral_inches": None,
    }


def measure_object(
    box: Box,
    intrinsics: CameraIntrinsics,
    width_inches: float | None = None,
    height_inches: float | None = None,
    ground: Calibration | None = None,
) -> dict[str, Any]:
    """
    The object's distance from the camera, from its box and its real size.

    With both sizes, each gives its own range and they are combined weighted
    by how precisely each was measured, so a big span counts for more than a
    small one. Their disagreement is reported: a large one means the box is
    loose or the object is turned away. With a floor calibration as well, the
    point on the floor beneath the object is given too.
    """
    check_sizes(width_inches, height_inches)
    check_in_frame(box, intrinsics.image_w, intrinsics.image_h)

    ranges = _ranges(box, intrinsics, width_inches, height_inches)
    sigmas = {}
    if width_inches is not None:
        sigmas["width"] = _uncertainty(box, intrinsics, width_inches, "width")
    if height_inches is not None:
        sigmas["height"] = _uncertainty(box, intrinsics, height_inches, "height")

    weights = {k: 1.0 / max(sigmas[k], 1e-9) ** 2 for k in ranges}
    total = sum(weights.values())
    range_inches = sum(ranges[k] * weights[k] for k in ranges) / total
    uncertainty = 1.0 / math.sqrt(total)

    disagreement = None
    if len(ranges) == 2:
        disagreement = abs(ranges["width"] - ranges["height"]) / ((ranges["width"] + ranges["height"]) / 2)

    forward = lateral = None
    pose = camera_pose_on_ground(ground, intrinsics) if ground is not None else None
    if pose is not None:
        rotation, translation = pose
        in_camera = range_inches * _rays(intrinsics, [box.centre])[0]
        on_floor = rotation.T @ (in_camera - translation)
        lateral, forward = float(on_floor[0]), float(on_floor[1])

    return {
        "known": True,
        "range_inches": round(range_inches, 2),
        "range_from_width_inches": round(ranges["width"], 2) if "width" in ranges else None,
        "range_from_height_inches": round(ranges["height"], 2) if "height" in ranges else None,
        "size_disagreement": round(disagreement, 3) if disagreement is not None else None,
        "range_uncertainty_inches": round(uncertainty, 2),
        "forward_inches": round(forward, 2) if forward is not None else None,
        "lateral_inches": round(lateral, 2) if lateral is not None else None,
        "note": NOTE,
    }


# ------------------------------------------------------------------- speed


SPEED_NOTE = (
    "closing_speed_inches_per_s is how fast the range to the object is shrinking: positive means "
    "getting closer. It assumes the object is standing still, so it is the car's speed toward it. "
    "Use frames at least half a second apart; closer together, box noise swamps the movement."
)


#: Frames closer together than this are warned about whatever the numbers say:
#: noise on a short span inflates the measured speed as well as its error, so
#: the two can look consistent while both are wrong.
MIN_SPAN_S = 0.5
#: Warned about past this: a speed known only to within half of itself is not
#: one to brake on.
MAX_RELATIVE_UNCERTAINTY = 0.5


class Observation(NamedTuple):
    timestamp: float
    box: Box


def parse_observations(raw: object) -> list[Observation]:
    """The agent's `[{timestamp, box}, ...]`, oldest first, or a ValueError saying what is wrong."""
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(
            "observations must be a list of at least two {timestamp, box}, one per frame; a speed needs two positions"
        )
    parsed = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {"timestamp", "box"}:
            raise ValueError(f"observation {index + 1} must be exactly {{timestamp, box}}")
        try:
            timestamp = float(item["timestamp"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"observation {index + 1}: timestamp must be a number, in seconds") from exc
        try:
            box = parse_box(item["box"])
        except ValueError as exc:
            raise ValueError(f"observation {index + 1}: {exc}") from exc
        parsed.append(Observation(timestamp, box))

    parsed.sort(key=lambda o: o.timestamp)
    for earlier, later in itertools.pairwise(parsed):
        if later.timestamp == earlier.timestamp:
            raise ValueError(
                f"Two observations share timestamp {later.timestamp}: the same frame twice tells nothing "
                "about speed. Use the timestamp get_vehicle_state returned with each frame."
            )
    return parsed


def unknown_speed(reason: str) -> dict[str, Any]:
    return {
        "known": False,
        "reason": reason,
        "closing_speed_inches_per_s": None,
        "closing_speed_uncertainty_inches_per_s": None,
        "span_s": None,
        "observations": None,
    }


def estimate_speed(
    observations: list[Observation],
    intrinsics: CameraIntrinsics,
    width_inches: float | None = None,
    height_inches: float | None = None,
) -> dict[str, Any]:
    """
    The rate the range to a stationary object is closing, from two or more frames.

    Each frame is ranged as measure_object does, then a straight line is fitted
    through range against time, each point weighted by its own uncertainty, so
    a far, small box counts for less than a near, big one. The slope's
    uncertainty comes from the per-frame uncertainties; with three or more
    frames it is widened when the points scatter more than those allow, so a
    noisy box shows up as a noisy speed rather than a confident wrong one.
    """
    check_sizes(width_inches, height_inches)
    measured = []
    for index, observation in enumerate(observations):
        try:
            result = measure_object(observation.box, intrinsics, width_inches, height_inches)
        except ValueError as exc:
            raise ValueError(f"observation {index + 1}: {exc}") from exc
        measured.append((observation.timestamp, result["range_inches"], result["range_uncertainty_inches"]))

    t0 = measured[0][0]
    times = np.array([t - t0 for t, _, _ in measured])
    ranges = np.array([r for _, r, _ in measured])
    weights = 1.0 / np.maximum(np.array([s for _, _, s in measured]), 1e-6) ** 2

    total, by_t, by_tt = weights.sum(), (weights * times).sum(), (weights * times**2).sum()
    spread = total * by_tt - by_t**2
    slope = (total * (weights * times * ranges).sum() - by_t * (weights * ranges).sum()) / spread
    intercept = ((weights * ranges).sum() - slope * by_t) / total
    slope_sigma = math.sqrt(total / spread)

    if len(measured) > 2:
        residuals = ranges - (intercept + slope * times)
        reduced_chi2 = float((weights * residuals**2).sum()) / (len(measured) - 2)
        slope_sigma *= math.sqrt(max(1.0, reduced_chi2))

    speed = -float(slope)
    answer: dict[str, Any] = {
        "known": True,
        "closing_speed_inches_per_s": round(speed, 2),
        "closing_speed_uncertainty_inches_per_s": round(slope_sigma, 2),
        "span_s": round(float(times[-1]), 3),
        "observations": [{"timestamp": t, "range_inches": r, "range_uncertainty_inches": s} for t, r, s in measured],
        "note": SPEED_NOTE,
    }
    span = float(times[-1])
    if span < MIN_SPAN_S:
        answer["warning"] = (
            f"These frames span only {span:.2f} s, under {MIN_SPAN_S} s: too close together for the movement to "
            "stand out from box noise, which inflates the speed and its uncertainty alike. Use frames further apart."
        )
    elif slope_sigma > MAX_RELATIVE_UNCERTAINTY * abs(speed):
        answer["warning"] = (
            f"The uncertainty ({slope_sigma:.1f} in/s) is more than half the speed ({speed:.1f} in/s): the boxes "
            "are too rough, or the object too far, to tell. Use frames further apart, or more of them."
        )
    return answer
