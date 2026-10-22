"""
Camera intrinsics for the CV autopilot: focal length, principal point and lens
distortion.

The ground-plane calibration in cv_calibration maps pixels to the floor, which
answers "where is the thing at this pixel" only for things touching the floor.
How far away an upright object of known size is needs the focal length, and a
floor homography does not pin that down: on a real car the two ways of
recovering it from the homography disagreed by 40%, because the wide-angle lens
is distorted and the board covers a small patch of floor.

So this is a separate, optional calibration, solved the standard OpenCV way
from many views of a board held up at different angles. It is kept in its own
file because it describes the camera, lens and resolution, not how the camera
is mounted: re-doing the floor calibration after a bump must not lose it.

One limit, recorded so it can be checked: a swapped lens on the same camera
type at the same resolution cannot be detected. `stale_reasons` catches a
changed resolution or camera type, which is all the config can say.
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

from donkeycar.parts.cv_calibration import (
    DEFAULT_PATTERN,
    DEFAULT_SQUARE_INCHES,
    CalibrationError,
    board_object_points,
)

logger = logging.getLogger(__name__)

# The car config is populated by exec'ing the car's config.py, so its attributes
# do not exist statically.
CarConfig = Any

INTRINSICS_FILENAME = "camera_intrinsics.json"

# OpenCV suggests 10-20 views. This is the floor below which a solve is refused,
# not a target: more views, tilted more ways, constrain the distortion better.
MIN_VIEWS = 12
# A good capture at 320x240 lands well under this. Over it, the distances the
# calibration produces are confidently wrong, which is worse than none.
MAX_RMS_PX = 1.0
# OpenCV's standard model: k1, k2, p1, p2, k3.
DISTORTION_COEFFICIENTS = 5

_REQUIRED = {"fx", "fy", "cx", "cy", "distortion", "image_w", "image_h", "camera_type"}


class IntrinsicsRefused(CalibrationError):
    """
    A capture solve_intrinsics will not accept. `view_errors` carries each
    view's error when the solve got far enough to measure them, so a refused
    capture can still be recorded view by view.
    """

    def __init__(self, message: str, view_errors: list[float] | None = None) -> None:
        super().__init__(message)
        self.view_errors = view_errors


@dataclass
class CameraIntrinsics:
    """
    A camera calibration plus the settings it was captured under.

    `fx` and `fy` are the focal length in pixels and `cx`, `cy` the principal
    point, all at `image_w` x `image_h`. `distortion` is OpenCV's five
    coefficients, k1, k2, p1, p2, k3.
    """

    fx: float
    fy: float
    cx: float
    cy: float
    distortion: list[float]
    image_w: int
    image_h: int
    camera_type: str
    rms_error_px: float | None = None
    view_count: int = 0
    captured_at: float = field(default_factory=time.time)
    # Where this calibration was read from. Reported, never saved.
    loaded_from: str | None = None

    # ------------------------------------------------------------- persistence

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        saved = self.to_dict()
        del saved["loaded_from"]
        with open(path, "w") as handle:
            json.dump(saved, handle, indent=2, sort_keys=True)
        logger.info("Wrote camera intrinsics to %s", path)

    @classmethod
    def load(cls, path: str) -> CameraIntrinsics:
        try:
            with open(path) as handle:
                raw = json.load(handle)
        except OSError as exc:
            raise CalibrationError(f"Could not read camera intrinsics {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"{path} is not valid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise CalibrationError(f"{path} must contain a JSON object, got {type(raw).__name__}")

        known = set(cls.__dataclass_fields__) - {"loaded_from"}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise CalibrationError(f"{path}: unknown field(s) {unknown}")
        missing = sorted(_REQUIRED - set(raw))
        if missing:
            raise CalibrationError(f"{path}: missing required field(s) {missing}")

        distortion = raw["distortion"]
        if (
            not isinstance(distortion, list)
            or len(distortion) != DISTORTION_COEFFICIENTS
            or not all(isinstance(k, (int, float)) for k in distortion)
        ):
            raise CalibrationError(f"{path}: 'distortion' must be a list of {DISTORTION_COEFFICIENTS} numbers")
        for name in ("fx", "fy"):
            if not isinstance(raw[name], (int, float)) or raw[name] <= 0:
                raise CalibrationError(f"{path}: '{name}' must be a positive number")

        return cls(**raw, loaded_from=os.path.abspath(path))

    # ---------------------------------------------------------------- staleness

    def stale_reasons(self, cfg: CarConfig) -> list[str]:
        """
        Which capture settings no longer match the car's configuration.

        The focal length in pixels scales with the resolution, so intrinsics
        captured at another size describe a different camera.
        """
        reasons = []
        for attr, name in (("IMAGE_W", "image_w"), ("IMAGE_H", "image_h")):
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

    def camera_matrix(self) -> np.ndarray:
        return np.array([[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]], dtype=np.float64)

    def distortion_array(self) -> np.ndarray:
        return np.asarray(self.distortion, dtype=np.float64)

    def undistort_points(self, points: np.ndarray) -> np.ndarray:
        """
        Pixel coordinates to undistorted normalised image coordinates.

        A normalised point (x, y) is the ray through (x, y, 1) in the camera's
        frame, so x * fx + cx is where it would land through a perfect lens.
        Iterated to convergence rather than OpenCV's fixed few passes, which
        leave a visible residual on a strongly distorted wide-angle lens.
        """
        pts = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)
        criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 100, 1e-10)
        undistorted = cv2.undistortPoints(
            pts, self.camera_matrix(), self.distortion_array(), None, None, None, criteria
        )
        return undistorted.reshape(-1, 2)


def missing_quadrants(corner_sets: list[np.ndarray], image_w: int, image_h: int) -> list[str]:
    """
    Quadrants of the frame that no view's corners reach.

    Distortion is strongest toward the corners of the frame, so views that never
    go there leave it unconstrained -- and the edges are where a sign usually is
    when the car first sees it.
    """
    points = np.vstack([np.asarray(c, dtype=np.float64).reshape(-1, 2) for c in corner_sets])
    left = points[:, 0] < image_w / 2
    top = points[:, 1] < image_h / 2
    quadrants = {
        "top-left": left & top,
        "top-right": ~left & top,
        "bottom-left": left & ~top,
        "bottom-right": ~left & ~top,
    }
    return [name for name, inside in quadrants.items() if not inside.any()]


def solve_intrinsics(
    corner_sets: list[np.ndarray],
    image_w: int,
    image_h: int,
    camera_type: str,
    pattern: tuple[int, int] = DEFAULT_PATTERN,
    square_inches: float = DEFAULT_SQUARE_INCHES,
) -> tuple[CameraIntrinsics, list[float]]:
    """
    Solve for the camera from the board corners found in each view.

    Returns the intrinsics and each view's RMS reprojection error in pixels, in
    the order given, so a capture can say which views fit badly. Refuses, with
    the reason, too few views, a frame quadrant no view reaches, or an overall
    error above MAX_RMS_PX; the last carries the view errors too.
    """
    if len(corner_sets) < MIN_VIEWS:
        raise IntrinsicsRefused(
            f"{len(corner_sets)} view(s) collected; at least {MIN_VIEWS} are needed, "
            f"so add {MIN_VIEWS - len(corner_sets)} more, tilting the board a different way each time."
        )

    expected = pattern[0] * pattern[1]
    for index, corners in enumerate(corner_sets):
        if len(corners) != expected:
            raise IntrinsicsRefused(
                f"View {index + 1} has {len(corners)} corners; a {pattern[0]}x{pattern[1]} board has {expected}."
            )

    empty = missing_quadrants(corner_sets, image_w, image_h)
    if empty:
        raise IntrinsicsRefused(
            f"No view reaches the {', '.join(empty)} of the frame. Add views with the board there: "
            "distortion is strongest near the corners, and an uncovered one is left unconstrained."
        )

    board = board_object_points(pattern, square_inches)
    object_points = np.hstack([board, np.zeros((len(board), 1))]).astype(np.float32)
    object_sets = [object_points] * len(corner_sets)
    image_sets = [np.asarray(c, dtype=np.float32).reshape(-1, 1, 2) for c in corner_sets]

    rms, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(object_sets, image_sets, (image_w, image_h), None, None)

    view_errors = []
    for obj, img, rvec, tvec in zip(object_sets, image_sets, rvecs, tvecs, strict=True):
        projected, _ = cv2.projectPoints(obj, rvec, tvec, matrix, distortion)
        residual = projected.reshape(-1, 2) - img.reshape(-1, 2)
        view_errors.append(float(np.sqrt(np.mean(np.sum(residual**2, axis=1)))))

    if rms > MAX_RMS_PX:
        worst = int(np.argmax(view_errors))
        raise IntrinsicsRefused(
            f"RMS reprojection error {rms:.2f} px is over {MAX_RMS_PX} px. The worst view is "
            f"{worst + 1} ({view_errors[worst]:.2f} px): a blurred or moving board is the usual cause.",
            view_errors,
        )

    intrinsics = CameraIntrinsics(
        fx=float(matrix[0, 0]),
        fy=float(matrix[1, 1]),
        cx=float(matrix[0, 2]),
        cy=float(matrix[1, 2]),
        distortion=[float(k) for k in distortion.reshape(-1)[:DISTORTION_COEFFICIENTS]],
        image_w=int(image_w),
        image_h=int(image_h),
        camera_type=str(camera_type),
        rms_error_px=float(rms),
        view_count=len(corner_sets),
    )
    return intrinsics, view_errors


# ---------------------------------------------------------------------- lookup


def find_intrinsics_file(car_dir: str | None) -> str | None:
    if not car_dir:
        return None
    path = os.path.join(os.path.expanduser(car_dir), INTRINSICS_FILENAME)
    return path if os.path.exists(path) else None


def load_intrinsics(car_dir: str | None, cfg: CarConfig) -> CameraIntrinsics | None:
    """The camera intrinsics for this car, or None when it has not been captured."""
    path = find_intrinsics_file(car_dir or getattr(cfg, "CAR_PATH", None))
    return CameraIntrinsics.load(path) if path else None
