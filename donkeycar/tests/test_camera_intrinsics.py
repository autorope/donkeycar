"""
Tests for the camera intrinsics calibration.

The board corners are projected through a camera whose focal length, centre
and distortion the test chooses, so the solver's answer can be checked against
the truth rather than against itself.
"""

import json

import cv2
import numpy as np
import pytest

from donkeycar.parts.camera_intrinsics import (
    INTRINSICS_FILENAME,
    MIN_VIEWS,
    CameraIntrinsics,
    find_intrinsics_file,
    load_intrinsics,
    missing_quadrants,
    solve_intrinsics,
)
from donkeycar.parts.cv_calibration import CalibrationError, board_object_points

COLS, ROWS = 9, 6
SQUARE_INCHES = 1.0
IMAGE_W, IMAGE_H = 320, 240

# A wide-angle camera at 320x240, like the Pi camera on a stock car: short focal
# length and strong barrel distortion.
TRUE_K = np.array([[200.0, 0.0, 163.0], [0.0, 200.0, 118.0], [0.0, 0.0, 1.0]])
TRUE_DIST = np.array([-0.30, 0.09, 0.001, -0.001, -0.01])


class Cfg:
    IMAGE_W = IMAGE_W
    IMAGE_H = IMAGE_H
    CAMERA_TYPE = "MOCK"


def _board_3d():
    board = board_object_points((COLS, ROWS), SQUARE_INCHES)
    return np.hstack([board, np.zeros((len(board), 1))])


def synthetic_views(count=16, noise_px=0.05, seed=1, region=None, k=TRUE_K, dist=TRUE_DIST):
    """
    Corner sets of the board held at varied positions and tilts.

    `region` limits where the board's centre may land, as (x_min, x_max) in
    pixels, to build captures that leave part of the frame uncovered.
    """
    rng = np.random.default_rng(seed)
    obj = _board_3d()
    centre = obj.mean(axis=0)
    views = []
    while len(views) < count:
        rvec = rng.uniform(-0.6, 0.6, 3)
        rvec[2] = rng.uniform(-0.3, 0.3)
        depth = rng.uniform(9.0, 16.0)
        tvec = np.array([rng.uniform(-6.0, 6.0), rng.uniform(-4.0, 4.0), depth])
        rotation, _ = cv2.Rodrigues(rvec)
        tvec = tvec - rotation @ centre  # place the board's centre, not its corner
        pts, _ = cv2.projectPoints(obj, rvec, tvec, k, dist)
        pts = pts.reshape(-1, 2)
        if not ((pts[:, 0] > 2).all() and (pts[:, 0] < IMAGE_W - 2).all()):
            continue
        if not ((pts[:, 1] > 2).all() and (pts[:, 1] < IMAGE_H - 2).all()):
            continue
        if region is not None:
            cx = pts[:, 0].mean()
            if not (region[0] <= cx <= region[1]) or pts[:, 0].max() > region[1]:
                continue
        views.append(pts + rng.normal(0.0, noise_px, pts.shape))
    return views


def _solve(views):
    return solve_intrinsics(views, IMAGE_W, IMAGE_H, "MOCK", (COLS, ROWS), SQUARE_INCHES)


# --------------------------------------------------------------------- solving


def test_recovers_the_true_camera():
    intrinsics, view_errors = _solve(synthetic_views())
    assert intrinsics.fx == pytest.approx(TRUE_K[0, 0], rel=0.01)
    assert intrinsics.fy == pytest.approx(TRUE_K[1, 1], rel=0.01)
    assert abs(intrinsics.cx - TRUE_K[0, 2]) < 2.0
    assert abs(intrinsics.cy - TRUE_K[1, 2]) < 2.0
    assert intrinsics.distortion[0] == pytest.approx(TRUE_DIST[0], abs=0.03)
    assert intrinsics.rms_error_px < 0.2
    assert intrinsics.view_count == 16
    assert len(view_errors) == 16 and max(view_errors) < 0.3


def test_too_few_views_is_refused_saying_how_many_more():
    with pytest.raises(CalibrationError, match=rf"at least {MIN_VIEWS}.*add 1 more"):
        _solve(synthetic_views(count=MIN_VIEWS - 1))


def test_an_uncovered_quadrant_is_refused_naming_it():
    """Views kept to the left half never constrain the right of the lens."""
    views = synthetic_views(count=MIN_VIEWS, region=(0, IMAGE_W / 2 - 1))
    with pytest.raises(CalibrationError, match="top-right, bottom-right"):
        _solve(views)


def test_a_poor_fit_is_refused_naming_the_worst_view():
    views = synthetic_views()
    views[3] = views[3] + np.random.default_rng(7).normal(0.0, 8.0, views[3].shape)
    with pytest.raises(CalibrationError, match=r"over 1\.0 px\. The worst view is 4 "):
        _solve(views)


def test_a_view_with_the_wrong_corner_count_is_refused():
    views = synthetic_views()
    views[0] = views[0][:-1]
    with pytest.raises(CalibrationError, match="View 1 has 53 corners"):
        _solve(views)


def test_missing_quadrants_reports_only_the_empty_ones():
    left_only = [np.array([[10.0, 10.0], [10.0, 200.0]])]
    assert missing_quadrants(left_only, IMAGE_W, IMAGE_H) == ["top-right", "bottom-right"]
    everywhere = [np.array([[10.0, 10.0], [300.0, 10.0], [10.0, 200.0], [300.0, 200.0]])]
    assert missing_quadrants(everywhere, IMAGE_W, IMAGE_H) == []


# ----------------------------------------------------------------- persistence


def _fresh():
    return CameraIntrinsics(
        fx=200.0,
        fy=201.0,
        cx=163.0,
        cy=118.0,
        distortion=[-0.3, 0.09, 0.001, -0.001, -0.01],
        image_w=IMAGE_W,
        image_h=IMAGE_H,
        camera_type="MOCK",
        rms_error_px=0.12,
        view_count=16,
    )


def test_saves_and_loads(tmp_path):
    path = tmp_path / INTRINSICS_FILENAME
    original = _fresh()
    original.save(str(path))
    loaded = CameraIntrinsics.load(str(path))
    assert loaded.fx == original.fx and loaded.distortion == original.distortion
    assert loaded.loaded_from == str(path)
    assert "loaded_from" not in json.loads(path.read_text())

    # Saving what was loaded must not write the path into the file either
    loaded.save(str(path))
    assert "loaded_from" not in json.loads(path.read_text())


def test_load_rejects_unknown_fields(tmp_path):
    path = tmp_path / INTRINSICS_FILENAME
    raw = _fresh().to_dict()
    del raw["loaded_from"]
    raw["focal_mm"] = 3.0
    path.write_text(json.dumps(raw))
    with pytest.raises(CalibrationError, match=r"unknown field.*focal_mm"):
        CameraIntrinsics.load(str(path))


def test_load_rejects_missing_fields(tmp_path):
    path = tmp_path / INTRINSICS_FILENAME
    raw = _fresh().to_dict()
    del raw["loaded_from"], raw["cx"]
    path.write_text(json.dumps(raw))
    with pytest.raises(CalibrationError, match=r"missing required field.*'cx'"):
        CameraIntrinsics.load(str(path))


@pytest.mark.parametrize("distortion", [[-0.3, 0.09], "none", [-0.3, 0.09, 0.0, 0.0, "x"]])
def test_load_rejects_a_bad_distortion_list(tmp_path, distortion):
    path = tmp_path / INTRINSICS_FILENAME
    raw = _fresh().to_dict()
    del raw["loaded_from"]
    raw["distortion"] = distortion
    path.write_text(json.dumps(raw))
    with pytest.raises(CalibrationError, match="list of 5 numbers"):
        CameraIntrinsics.load(str(path))


def test_load_rejects_a_non_positive_focal_length(tmp_path):
    path = tmp_path / INTRINSICS_FILENAME
    raw = _fresh().to_dict()
    del raw["loaded_from"]
    raw["fx"] = 0
    path.write_text(json.dumps(raw))
    with pytest.raises(CalibrationError, match="'fx' must be a positive number"):
        CameraIntrinsics.load(str(path))


def test_load_intrinsics_finds_the_file_in_the_car_directory(tmp_path):
    assert load_intrinsics(str(tmp_path), Cfg()) is None
    assert find_intrinsics_file(None) is None
    _fresh().save(str(tmp_path / INTRINSICS_FILENAME))
    loaded = load_intrinsics(str(tmp_path), Cfg())
    assert loaded is not None and loaded.fy == 201.0


# ------------------------------------------------------------------- staleness


def test_matching_settings_are_not_stale():
    assert _fresh().is_stale(Cfg()) is False


@pytest.mark.parametrize(
    ("attr", "value", "name"),
    [("IMAGE_W", 640, "image_w"), ("IMAGE_H", 480, "image_h"), ("CAMERA_TYPE", "PICAM", "camera_type")],
)
def test_a_changed_capture_setting_makes_it_stale(attr, value, name):
    class Changed(Cfg):
        pass

    setattr(Changed, attr, value)
    reasons = _fresh().stale_reasons(Changed())
    assert len(reasons) == 1 and reasons[0].startswith(name)


# -------------------------------------------------------------------- geometry


def test_undistort_points_inverts_the_lens():
    """Distort known rays through the true camera; undistorting must give them back."""
    intrinsics = CameraIntrinsics(
        fx=TRUE_K[0, 0],
        fy=TRUE_K[1, 1],
        cx=TRUE_K[0, 2],
        cy=TRUE_K[1, 2],
        distortion=list(TRUE_DIST),
        image_w=IMAGE_W,
        image_h=IMAGE_H,
        camera_type="MOCK",
    )
    # Rays spread to the corners of the frame, where the distortion is strongest
    xs, ys = np.meshgrid(np.linspace(-0.7, 0.7, 9), np.linspace(-0.55, 0.55, 7))
    rays = np.stack([xs.ravel(), ys.ravel(), np.ones(xs.size)], axis=1)
    distorted, _ = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), TRUE_K, TRUE_DIST)

    normalised = intrinsics.undistort_points(distorted.reshape(-1, 2))
    # Compare in pixels through a perfect lens, which is what 0.1 px is measured in
    error_px = (normalised - rays[:, :2]) * TRUE_K[0, 0]
    assert np.abs(error_px).max() < 0.1
