"""
Tests for measuring an object's distance from its bounding box.

The scene is synthetic: a camera 8 inches up and pitched 10 degrees down, and
an upright sign turned toward it, projected through known intrinsics with and
without lens distortion. The box is the projected sign's bounding box, so the
measurement sees exactly what an ideal detector would draw.
"""

import cv2
import numpy as np
import pytest

from donkeycar.parts.camera_intrinsics import CameraIntrinsics
from donkeycar.parts.cv_calibration import Calibration
from donkeycar.parts.object_distance import (
    Box,
    camera_pose_on_ground,
    measure_object,
    parse_box,
    unknown,
)

IMAGE_W, IMAGE_H = 320, 240
K = np.array([[230.0, 0.0, 160.0], [0.0, 230.0, 120.0], [0.0, 0.0, 1.0]])
NO_LENS = np.zeros(5)
WIDE_LENS = np.array([-0.30, 0.09, 0.001, -0.001, -0.01])
CAMERA_HEIGHT = 8.0
PITCH_DEG = 10.0
SIGN = 6.0  # a six-inch-square sign card


def intrinsics(dist=NO_LENS):
    return CameraIntrinsics(
        fx=K[0, 0],
        fy=K[1, 1],
        cx=K[0, 2],
        cy=K[1, 2],
        distortion=list(dist),
        image_w=IMAGE_W,
        image_h=IMAGE_H,
        camera_type="MOCK",
    )


def camera_pose(height=CAMERA_HEIGHT, pitch_deg=PITCH_DEG):
    """
    Floor frame: x lateral (right), y forward, z up. The camera sits at
    (0, 0, height) looking forward, pitched down.
    """
    pitch = np.radians(pitch_deg)
    forward = np.array([0.0, np.cos(pitch), -np.sin(pitch)])
    right = np.array([1.0, 0.0, 0.0])
    down = np.cross(forward, right)
    rotation = np.vstack([right, down, forward])  # floor -> camera
    position = np.array([0.0, 0.0, height])
    return rotation, -rotation @ position, position


def sign_box(forward, lateral=0.0, base=4.0, width=SIGN, height=SIGN, dist=NO_LENS):
    """The bounding box of an upright sign turned to face the camera, and its true range."""
    rotation, translation, position = camera_pose()
    centre = np.array([lateral, forward, base + height / 2])
    to_camera = position - centre
    yaw = np.arctan2(to_camera[0], -to_camera[1])
    across = np.array([np.cos(yaw), np.sin(yaw), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    signs = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    corners = np.array([centre + sx * width / 2 * across + sy * height / 2 * up for sx, sy in signs])
    rvec, _ = cv2.Rodrigues(rotation)
    pixels, _ = cv2.projectPoints(corners, rvec, translation, K, dist)
    pixels = pixels.reshape(-1, 2)
    box = Box(pixels[:, 0].min(), pixels[:, 1].min(), pixels[:, 0].max(), pixels[:, 1].max())
    return box, float(np.linalg.norm(centre - position))


def ground_calibration():
    """An exact floor homography for the pinhole camera above, as calibrate-cv would store it."""
    rotation, translation, _ = camera_pose()
    rvec, _ = cv2.Rodrigues(rotation)
    xs, ys = np.meshgrid(np.linspace(-12, 12, 7), np.linspace(18, 60, 7))
    floor = np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], axis=1)
    pixels, _ = cv2.projectPoints(floor, rvec, translation, K, NO_LENS)
    matrix, _ = cv2.findHomography(pixels.reshape(-1, 2), floor[:, :2])
    return Calibration(
        pixels_per_inch=3.4,
        scan_y=120,
        image_w=IMAGE_W,
        image_h=IMAGE_H,
        camera_type="MOCK",
        source="test",
        homography=matrix.tolist(),
    )


# --------------------------------------------------------------------- range


@pytest.mark.parametrize("dist", [NO_LENS, WIDE_LENS], ids=["pinhole", "wide-angle"])
@pytest.mark.parametrize("lateral", [0.0, 6.0])
@pytest.mark.parametrize(("forward", "tolerance"), [(24, 0.05), (60, 0.03), (120, 0.03)])
def test_range_from_size_is_close_to_the_truth(dist, lateral, forward, tolerance):
    box, true_range = sign_box(forward, lateral, dist=dist)
    result = measure_object(box, intrinsics(dist), width_inches=SIGN, height_inches=SIGN)
    assert result["known"] is True
    assert result["range_inches"] == pytest.approx(true_range, rel=tolerance)
    for one in ("range_from_width_inches", "range_from_height_inches"):
        assert result[one] == pytest.approx(true_range, rel=tolerance)


def test_width_only_and_height_only_agree_with_both():
    box, _ = sign_box(60)
    both = measure_object(box, intrinsics(), width_inches=SIGN, height_inches=SIGN)
    width = measure_object(box, intrinsics(), width_inches=SIGN)
    height = measure_object(box, intrinsics(), height_inches=SIGN)
    assert width["range_from_height_inches"] is None and width["size_disagreement"] is None
    assert height["range_from_width_inches"] is None
    assert width["range_inches"] == both["range_from_width_inches"]
    assert height["range_inches"] == both["range_from_height_inches"]
    lo, hi = sorted((width["range_inches"], height["range_inches"]))
    assert lo <= both["range_inches"] <= hi
    assert both["size_disagreement"] == pytest.approx(abs(hi - lo) / ((hi + lo) / 2), abs=0.002)


def test_a_wrong_size_shows_up_as_disagreement():
    """Say the sign is twice as wide as it is, and the two estimates part company."""
    box, _ = sign_box(60)
    result = measure_object(box, intrinsics(), width_inches=2 * SIGN, height_inches=SIGN)
    assert result["size_disagreement"] > 0.5


def test_uncertainty_grows_with_distance():
    near = measure_object(sign_box(24)[0], intrinsics(), height_inches=SIGN)
    far = measure_object(sign_box(120)[0], intrinsics(), height_inches=SIGN)
    assert 0 < near["range_uncertainty_inches"] < far["range_uncertainty_inches"]
    # One pixel on a box ~20 px tall at ten feet is several percent
    assert far["range_uncertainty_inches"] / far["range_inches"] > 0.03


def test_uncertainty_covers_a_one_pixel_slip():
    box, _ = sign_box(60)
    result = measure_object(box, intrinsics(), height_inches=SIGN)
    slipped = measure_object(box._replace(y_max=box.y_max + 1), intrinsics(), height_inches=SIGN)
    assert abs(slipped["range_inches"] - result["range_inches"]) <= result["range_uncertainty_inches"]


# ---------------------------------------------------------------- refusals


def test_neither_size_given_is_refused_naming_both():
    box, _ = sign_box(60)
    with pytest.raises(ValueError, match="width_inches, height_inches, or both"):
        measure_object(box, intrinsics())


def test_a_non_positive_size_is_refused():
    box, _ = sign_box(60)
    with pytest.raises(ValueError, match="height_inches must be positive"):
        measure_object(box, intrinsics(), height_inches=0)


def test_a_box_outside_the_frame_is_refused():
    with pytest.raises(ValueError, match="outside the 320x240 frame"):
        measure_object(Box(300, 10, 330, 40), intrinsics(), height_inches=SIGN)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"x_min": 10, "y_min": 10, "x_max": 10, "y_max": 40}, "no width or height"),
        ({"x_min": 10, "y_min": 50, "x_max": 30, "y_max": 40}, "no width or height"),
        ({"x_min": 10, "y_min": 10, "x_max": 30}, "missing y_max"),
        ({"x_min": 10, "y_min": 10, "x_max": 30, "y_max": 40, "z": 1}, "unknown z"),
        ({"x_min": "a", "y_min": 10, "x_max": 30, "y_max": 40}, "must be numbers"),
        ([10, 10, 30, 40], "must be an object"),
    ],
)
def test_a_malformed_box_is_refused(raw, message):
    with pytest.raises(ValueError, match=message):
        parse_box(raw)


def test_unknown_has_every_value_null():
    answer = unknown("no camera calibration")
    assert answer["known"] is False and answer["reason"] == "no camera calibration"
    assert all(v is None for k, v in answer.items() if k not in ("known", "reason"))


# ------------------------------------------------------------- on the floor


def test_the_camera_pose_comes_out_of_the_floor_calibration():
    rotation, translation = camera_pose_on_ground(ground_calibration(), intrinsics())
    position = -rotation.T @ translation
    assert position[0] == pytest.approx(0.0, abs=0.1)
    assert position[1] == pytest.approx(0.0, abs=0.1)
    assert abs(position[2]) == pytest.approx(CAMERA_HEIGHT, rel=0.01)


def test_no_floor_position_without_a_homography():
    box, _ = sign_box(60)
    scale_only = Calibration(
        pixels_per_inch=3.4, scan_y=120, image_w=IMAGE_W, image_h=IMAGE_H, camera_type="MOCK", source="tape"
    )
    result = measure_object(box, intrinsics(), height_inches=SIGN, ground=scale_only)
    assert result["forward_inches"] is None and result["lateral_inches"] is None


@pytest.mark.parametrize(("forward", "lateral"), [(30, 0.0), (48, 4.0), (60, -5.0)])
def test_the_floor_position_agrees_with_measuring_the_base(forward, lateral):
    """A sign standing on the floor: its base pixel, through the floor homography, is the same place."""
    ground = ground_calibration()
    box, _ = sign_box(forward, lateral, base=0.0)
    result = measure_object(box, intrinsics(), width_inches=SIGN, height_inches=SIGN, ground=ground)
    base_lateral, base_forward = ground.image_to_ground(box.centre[0], box.y_max)
    assert result["forward_inches"] == pytest.approx(base_forward, rel=0.05)
    assert result["forward_inches"] == pytest.approx(forward, rel=0.05)
    assert result["lateral_inches"] == pytest.approx(lateral, abs=0.05 * forward)
    assert result["lateral_inches"] == pytest.approx(base_lateral, abs=0.05 * forward)
