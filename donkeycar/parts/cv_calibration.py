"""
Ground-plane calibration for the CV autopilot.

The line follower steers to a pixel column in one horizontal band of the image,
so a lane offset expressed in inches needs to know how many pixels an inch is
worth on the ground at that band. A checkerboard laid flat on the floor answers
that, and the same corners answer a more useful question for free: where on the
ground is the thing I can see at this pixel?

That second answer is what lets an agent brake for a stop sign. Without it the
only cue is apparent size, guessed over a network round trip while the car keeps
moving.

Two honest limits, both recorded with the calibration so they can be checked:

* It is a single homography, which assumes a pinhole camera. Wide-angle lenses
  have real barrel distortion, so accuracy falls off toward the frame edges. It
  is fine for the few-inch, near-centre offsets a lane change needs.
* It calibrates the camera's *mounting* as much as its lens. Anything that
  changes the camera's pitch invalidates it, which is why the capture settings
  are stored alongside and `is_stale` exists.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# The car config is populated by exec'ing the car's config.py, so its attributes
# do not exist statically. Naming the alias says "the car config" without
# promising a shape a type checker could verify.
CarConfig = Any

CALIBRATION_FILENAME = "cv_calibration.json"

# Inner-corner counts, not squares: a board of N x M squares has (N-1) x (M-1).
DEFAULT_PATTERN = (9, 6)
DEFAULT_SQUARE_INCHES = 1.0


class CalibrationError(ValueError):
    """Calibration could not be produced or read. The message says why."""


@dataclass
class Calibration:
    """
    A ground-plane calibration plus the settings it was captured under.

    `homography` maps image pixels to inches on the ground. The frame's origin
    is the board's first inner corner unless `origin_forward_inches` /
    `origin_lateral_inches` say where that corner sat relative to the car, in
    which case measurements come back in car coordinates.
    """

    pixels_per_inch: float
    scan_y: int
    image_w: int
    image_h: int
    camera_type: str
    source: str
    homography: list[list[float]] | None = None
    origin_forward_inches: float = 0.0
    origin_lateral_inches: float = 0.0
    captured_at: float = field(default_factory=time.time)
    reprojection_error_px: float | None = None
    note: str = ""

    # ------------------------------------------------------------- persistence

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        with open(path, "w") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
        logger.info("Wrote calibration to %s", path)

    @classmethod
    def load(cls, path: str) -> Calibration:
        try:
            with open(path) as handle:
                raw = json.load(handle)
        except OSError as exc:
            raise CalibrationError(f"Could not read calibration {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"{path} is not valid JSON: {exc}") from exc

        known = {f for f in cls.__dataclass_fields__}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise CalibrationError(f"{path}: unknown field(s) {unknown}")
        missing = sorted({"pixels_per_inch", "scan_y", "image_w", "image_h", "camera_type", "source"} - set(raw))
        if missing:
            raise CalibrationError(f"{path}: missing required field(s) {missing}")
        return cls(**raw)

    # ---------------------------------------------------------------- staleness

    def stale_reasons(self, cfg: CarConfig) -> list[str]:
        """
        Which capture settings no longer match the car's configuration.

        A calibration taken at a different scan line or image width describes a
        different measurement, and silently reusing it is how a lane change ends
        up in the wrong lane.
        """
        reasons = []
        for attr, name in (("SCAN_Y", "scan_y"), ("IMAGE_W", "image_w"), ("IMAGE_H", "image_h")):
            expected = getattr(cfg, attr, None)
            actual = getattr(self, name)
            if expected is not None and int(expected) != int(actual):
                reasons.append(f"{name} was {actual} at capture, config now says {expected}")
        camera = getattr(cfg, "CAMERA_TYPE", None)
        if camera is not None and str(camera) != self.camera_type:
            reasons.append(f"camera_type was {self.camera_type!r} at capture, config now says {str(camera)!r}")
        return reasons

    def is_stale(self, cfg: CarConfig) -> bool:
        return bool(self.stale_reasons(cfg))

    # -------------------------------------------------------------- geometry

    def homography_matrix(self) -> np.ndarray | None:
        if self.homography is None:
            return None
        return np.asarray(self.homography, dtype=np.float64)

    def image_to_ground(self, u: float, v: float) -> tuple[float, float]:
        """
        Where on the ground is the pixel (u, v)?

        Returns (lateral_inches, forward_inches): lateral is positive to the
        right, forward is positive away from the car.
        """
        matrix = self.homography_matrix()
        if matrix is None:
            raise CalibrationError(
                "This calibration has no homography, so it can only convert lane offsets, "
                "not measure points. Re-run `donkey calibrate-cv` with a checkerboard."
            )
        point = np.array([[[float(u), float(v)]]], dtype=np.float64)
        ground = cv2.perspectiveTransform(point, matrix)[0][0]
        return (
            float(ground[0]) + self.origin_lateral_inches,
            float(ground[1]) + self.origin_forward_inches,
        )


# --------------------------------------------------------------------- capture


def board_object_points(pattern: tuple[int, int], square_inches: float) -> np.ndarray:
    """Ground coordinates, in inches, of every inner corner of the board."""
    cols, rows = pattern
    points = np.zeros((cols * rows, 2), dtype=np.float64)
    points[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    return points * float(square_inches)


# Upscale factors to retry detection at when the native frame is too coarse.
# Not a smooth sweep on purpose: the detector's response to scale is lumpy --
# on a real 320x240 frame it failed at 1x, 2x and 4x but succeeded at 3x and 6x
# on the very same image, so this tries several rather than one "big enough" one.
DETECT_UPSCALES: tuple[int, ...] = (2, 3, 4, 6)


def detect_board(image: np.ndarray, pattern: tuple[int, int] = DEFAULT_PATTERN) -> np.ndarray | None:
    """
    Find the board's inner corners, or None.

    Uses findChessboardCornersSB: a board lying flat under a low, pitched camera
    is exactly the shallow, perspective-heavy case where the classic detector
    gets unreliable, and SB also copes with a partly visible board.

    Retries on an upscaled copy when the native frame fails. Donkeycar's stock
    camera is 320x240, and a board small enough to sit at the scan line is then
    only about 8 px per square -- below what the detector can resolve, even
    though the board is perfectly flat, sharp and well lit. Upscaling adds no
    information, but it does give the corner filters room to work: measured on a
    real frame, corners recovered at 3x and divided back down fitted a
    homography with 0.05 inch reprojection error. Interpolation is cubic so the
    corners land on sub-pixel positions rather than snapping to the upscaled
    grid.
    """
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image

    for scale in (1, *DETECT_UPSCALES):
        probe = gray if scale == 1 else cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        found, corners = cv2.findChessboardCornersSB(probe, pattern, flags=cv2.CALIB_CB_EXHAUSTIVE)
        if found and corners is not None:
            if scale != 1:
                logger.info("Board found at %dx upscale; the board is small in frame for a %s pattern", scale, pattern)
            # Back to native pixel coordinates: everything downstream -- the
            # homography, SCAN_Y, the lane offsets -- is in the camera's own
            # frame, so corners measured on a magnified copy must be divided
            # back or the calibration is wrong by exactly `scale`.
            return corners.reshape(-1, 2).astype(np.float64) / float(scale)

    return None


def solve_homography(
    corners: np.ndarray,
    pattern: tuple[int, int] = DEFAULT_PATTERN,
    square_inches: float = DEFAULT_SQUARE_INCHES,
) -> tuple[np.ndarray, float]:
    """Map image pixels to ground inches. Returns the matrix and its RMS error."""
    object_points = board_object_points(pattern, square_inches)
    if len(corners) != len(object_points):
        raise CalibrationError(
            f"Expected {len(object_points)} corners for a {pattern[0]}x{pattern[1]} board, got {len(corners)}"
        )

    matrix, _mask = cv2.findHomography(corners, object_points, cv2.RANSAC, 3.0)
    if matrix is None:
        raise CalibrationError("Could not fit a homography to those corners; try a flatter, better-lit board")

    projected = cv2.perspectiveTransform(corners.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    error = float(np.sqrt(np.mean(np.sum((projected - object_points) ** 2, axis=1))))
    return matrix, error


def pixels_per_inch_at_row(matrix: np.ndarray, row: int, image_w: int, span_px: int = 40) -> float:
    """
    How many pixels make an inch on the ground, along one image row.

    For a camera with no roll, a horizontal row maps to a line of constant
    distance on the ground, so this is a single number for that row. Measured
    across a span either side of centre rather than at a point, so lens noise
    does not dominate.
    """
    centre = image_w / 2.0
    left = max(0.0, centre - span_px / 2.0)
    right = min(float(image_w - 1), centre + span_px / 2.0)
    points = np.array([[[left, float(row)]], [[right, float(row)]]], dtype=np.float64)
    ground = cv2.perspectiveTransform(points, matrix).reshape(-1, 2)

    inches = float(np.hypot(*(ground[1] - ground[0])))
    if inches <= 1e-9:
        raise CalibrationError("Degenerate homography: the scan row maps to zero ground distance")
    return float(right - left) / inches


def calibrate_from_image(
    image: np.ndarray,
    cfg: CarConfig,
    pattern: tuple[int, int] = DEFAULT_PATTERN,
    square_inches: float = DEFAULT_SQUARE_INCHES,
    origin_forward_inches: float = 0.0,
    origin_lateral_inches: float = 0.0,
) -> Calibration:
    """Detect, solve, and package a calibration from one frame."""
    corners = detect_board(image, pattern)
    if corners is None:
        raise CalibrationError(
            f"No {pattern[0]}x{pattern[1]} checkerboard found. Lay the board flat on the floor so the "
            "scan line crosses it, and check the lighting."
        )

    matrix, error = solve_homography(corners, pattern, square_inches)
    height, width = image.shape[:2]
    scan_y = int(getattr(cfg, "SCAN_Y", height // 2))
    ppi = pixels_per_inch_at_row(matrix, scan_y, width)

    return Calibration(
        pixels_per_inch=ppi,
        scan_y=scan_y,
        image_w=width,
        image_h=height,
        camera_type=str(getattr(cfg, "CAMERA_TYPE", "unknown")),
        source="chessboard",
        homography=[[float(v) for v in row] for row in matrix],
        origin_forward_inches=origin_forward_inches,
        origin_lateral_inches=origin_lateral_inches,
        reprojection_error_px=error,
    )


def calibrate_from_tape(
    image: np.ndarray,
    cfg: CarConfig,
    separation_inches: float,
) -> Calibration:
    """
    Fallback: two strips of the follow-tape a known distance apart.

    No new detection code and no printer -- it reuses the same HSV threshold the
    controller itself uses, so it calibrates in the controller's own terms. It
    gives the scale only, not a homography, so `measure_ground_point` stays
    unavailable until a board capture is done.
    """
    if separation_inches <= 0:
        raise CalibrationError("separation_inches must be positive")

    height, width = image.shape[:2]
    scan_y = int(getattr(cfg, "SCAN_Y", height // 2))
    scan_height = int(getattr(cfg, "SCAN_HEIGHT", 20))

    band = image[scan_y : scan_y + scan_height, :, :]
    hsv = cv2.cvtColor(band, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(
        hsv,
        np.asarray(getattr(cfg, "COLOR_THRESHOLD_LOW", (0, 50, 50))),
        np.asarray(getattr(cfg, "COLOR_THRESHOLD_HIGH", (50, 255, 255))),
    )
    columns = np.where(mask.sum(axis=0) > 0)[0]
    if columns.size == 0:
        raise CalibrationError("No tape found in the scan band; check the colour thresholds and the lighting")

    # Two strips: split at the widest gap between lit columns.
    gaps = np.diff(columns)
    if gaps.size == 0 or gaps.max() <= 1:
        raise CalibrationError("Only one tape strip found; lay two strips a known distance apart")
    split = int(np.argmax(gaps))
    left_centre = float(np.mean(columns[: split + 1]))
    right_centre = float(np.mean(columns[split + 1 :]))

    separation_px = abs(right_centre - left_centre)
    return Calibration(
        pixels_per_inch=separation_px / float(separation_inches),
        scan_y=scan_y,
        image_w=width,
        image_h=height,
        camera_type=str(getattr(cfg, "CAMERA_TYPE", "unknown")),
        source="tape",
        homography=None,
        note=(
            f"Measured from two tape strips {separation_inches} inches apart. "
            "Scale only; run a checkerboard capture for ground measurements."
        ),
    )


# ---------------------------------------------------------------------- lookup


def find_calibration_file(car_dir: str | None) -> str | None:
    if not car_dir:
        return None
    path = os.path.join(os.path.expanduser(car_dir), CALIBRATION_FILENAME)
    return path if os.path.exists(path) else None


def load_calibration(car_dir: str | None, cfg: CarConfig) -> Calibration | None:
    """
    The calibration for this car, or None.

    Falls back to a hand-set CV_PIXELS_PER_INCH so the rest of the system is
    usable before anyone has run a capture.
    """
    path = getattr(cfg, "CV_CALIBRATION_FILE", None) or find_calibration_file(car_dir or getattr(cfg, "CAR_PATH", None))
    if path:
        return Calibration.load(path)

    manual = getattr(cfg, "CV_PIXELS_PER_INCH", None)
    if manual:
        return Calibration(
            pixels_per_inch=float(manual),
            scan_y=int(getattr(cfg, "SCAN_Y", 0)),
            image_w=int(getattr(cfg, "IMAGE_W", 0)),
            image_h=int(getattr(cfg, "IMAGE_H", 0)),
            camera_type=str(getattr(cfg, "CAMERA_TYPE", "unknown")),
            source="config",
            note="Set by hand as CV_PIXELS_PER_INCH; no homography, so points cannot be measured.",
        )
    return None


def overlay_calibration(
    image: np.ndarray,
    corners: np.ndarray | None,
    scan_y: int,
    scan_height: int,
) -> np.ndarray:
    """
    Draw the scan band and any detected corners.

    This is what turns lining the board up into "make the green line cross the
    board" instead of a geometry problem solved over SSH.
    """
    canvas = np.copy(image)
    height, width = canvas.shape[:2]
    top = max(0, min(scan_y, height - 1))
    bottom = max(0, min(scan_y + scan_height, height - 1))

    # The band the controller actually samples.
    cv2.rectangle(canvas, (0, top), (width - 1, bottom), (255, 0, 0), 1)
    cv2.line(canvas, (width // 2, 0), (width // 2, height - 1), (255, 0, 0), 1)

    if corners is not None:
        for point in corners:
            cv2.circle(canvas, (round(point[0]), round(point[1])), 2, (0, 255, 0), -1)
        label = f"BOARD OK ({len(corners)} corners)"
        colour = (0, 255, 0)
    else:
        label = "NO BOARD - lay it flat, cross the blue band"
        colour = (255, 0, 0)

    cv2.putText(canvas, label, (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour)
    return canvas
