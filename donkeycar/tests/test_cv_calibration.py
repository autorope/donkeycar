"""
Tests for ground-plane calibration.

The board is synthesised and warped through a known perspective, so these run
with no camera and no printed target while still exercising the real detector
and the real homography solve.
"""

import cv2
import numpy as np
import pytest

from donkeycar.parts.cv_calibration import (
    Calibration,
    CalibrationError,
    board_object_points,
    calibrate_from_image,
    calibrate_from_tape,
    detect_board,
    find_calibration_file,
    load_calibration,
    overlay_calibration,
    pixels_per_inch_at_row,
    solve_homography,
)

COLS, ROWS = 9, 6  # inner corners
SQUARE_INCHES = 1.0
IMAGE_W, IMAGE_H = 320, 240


class Cfg:
    SCAN_Y = 120
    SCAN_HEIGHT = 20
    IMAGE_W = IMAGE_W
    IMAGE_H = IMAGE_H
    CAMERA_TYPE = "MOCK"
    COLOR_THRESHOLD_LOW = (20, 100, 100)
    COLOR_THRESHOLD_HIGH = (40, 255, 255)


def board_image(cols=COLS, rows=ROWS, square_px=30, margin=60):
    """A top-down checkerboard with `cols` x `rows` inner corners."""
    width = (cols + 1) * square_px + 2 * margin
    height = (rows + 1) * square_px + 2 * margin
    img = np.full((height, width, 3), 255, np.uint8)
    for i in range(cols + 1):
        for j in range(rows + 1):
            if (i + j) % 2 == 0:
                x0, y0 = margin + i * square_px, margin + j * square_px
                img[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    return img


def camera_view(top_down=None):
    """The board as a pitched-down camera would see it: far edge compressed."""
    top_down = board_image() if top_down is None else top_down
    height, width = top_down.shape[:2]
    src = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    dst = np.float32(
        [
            [width * 0.30, height * 0.10],
            [width * 0.70, height * 0.10],
            [width * 1.02, height * 0.95],
            [width * -0.02, height * 0.95],
        ]
    )
    warped = cv2.warpPerspective(
        top_down, cv2.getPerspectiveTransform(src, dst), (width, height), borderValue=(255, 255, 255)
    )
    return cv2.resize(warped, (IMAGE_W, IMAGE_H))


# ------------------------------------------------------------------ detection


def test_detects_a_board_in_a_perspective_view():
    corners = detect_board(camera_view(), (COLS, ROWS))
    assert corners is not None
    assert corners.shape == (COLS * ROWS, 2)


def test_returns_none_when_there_is_no_board():
    assert detect_board(np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8), (COLS, ROWS)) is None


def test_returns_none_for_no_image():
    assert detect_board(None, (COLS, ROWS)) is None


def test_object_points_are_spaced_by_the_square_size():
    points = board_object_points((3, 2), 2.0)
    assert points.shape == (6, 2)
    assert sorted({float(x) for x, _ in points}) == [0.0, 2.0, 4.0]


# ------------------------------------------------------------------ homography


def test_homography_reprojects_the_corners_accurately():
    corners = detect_board(camera_view(), (COLS, ROWS))
    matrix, error = solve_homography(corners, (COLS, ROWS), SQUARE_INCHES)
    assert matrix.shape == (3, 3)
    # A tenth of an inch over a board of 1 inch squares.
    assert error < 0.1, error


def test_wrong_corner_count_is_rejected():
    with pytest.raises(CalibrationError, match="Expected"):
        solve_homography(np.zeros((10, 2)), (COLS, ROWS), SQUARE_INCHES)


def test_pixels_per_inch_is_positive_and_plausible():
    corners = detect_board(camera_view(), (COLS, ROWS))
    matrix, _ = solve_homography(corners, (COLS, ROWS), SQUARE_INCHES)
    ppi = pixels_per_inch_at_row(matrix, Cfg.SCAN_Y, IMAGE_W)
    assert ppi > 0
    # A 320px frame across a board of a handful of inches: tens of px per inch.
    assert 1.0 < ppi < 200.0, ppi


# ------------------------------------------------------------------- accuracy


def test_ground_measurement_round_trips():
    """
    A known board corner must map back to its true ground position. This is the
    property `measure_ground_point` rests on -- without it the agent's only
    distance cue is apparent size.
    """
    view = camera_view()
    calibration = calibrate_from_image(view, Cfg(), (COLS, ROWS), SQUARE_INCHES)
    corners = detect_board(view, (COLS, ROWS))
    expected = board_object_points((COLS, ROWS), SQUARE_INCHES)

    errors = []
    for (u, v), (x, y) in zip(corners, expected, strict=True):
        lateral, forward = calibration.image_to_ground(u, v)
        errors.append(abs(lateral - x))
        errors.append(abs(forward - y))

    assert max(errors) < 0.25, f"worst ground error {max(errors):.3f} in"


def test_origin_offsets_move_measurements_into_car_coordinates():
    view = camera_view()
    plain = calibrate_from_image(view, Cfg(), (COLS, ROWS), SQUARE_INCHES)
    shifted = calibrate_from_image(
        view, Cfg(), (COLS, ROWS), SQUARE_INCHES, origin_forward_inches=24.0, origin_lateral_inches=-3.0
    )
    a = plain.image_to_ground(160, 120)
    b = shifted.image_to_ground(160, 120)
    assert b[0] == pytest.approx(a[0] - 3.0)
    assert b[1] == pytest.approx(a[1] + 24.0)


def test_measuring_without_a_homography_says_why():
    calibration = Calibration(
        pixels_per_inch=4.0, scan_y=120, image_w=320, image_h=240, camera_type="MOCK", source="config"
    )
    with pytest.raises(CalibrationError, match="no homography"):
        calibration.image_to_ground(10, 10)


def test_calibrate_reports_a_missing_board_usefully():
    with pytest.raises(CalibrationError, match="flat on the floor"):
        calibrate_from_image(np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8), Cfg())


# ------------------------------------------------------------------ staleness


def _fresh():
    return Calibration(
        pixels_per_inch=8.0, scan_y=120, image_w=320, image_h=240, camera_type="MOCK", source="chessboard"
    )


def test_matching_config_is_not_stale():
    assert _fresh().is_stale(Cfg()) is False


def test_changing_scan_y_makes_it_stale():
    class Moved(Cfg):
        SCAN_Y = 100

    calibration = _fresh()
    assert calibration.is_stale(Moved()) is True
    assert any("scan_y" in reason for reason in calibration.stale_reasons(Moved()))


def test_changing_image_width_makes_it_stale():
    class Wider(Cfg):
        IMAGE_W = 640

    assert _fresh().is_stale(Wider()) is True


def test_changing_camera_makes_it_stale():
    class OtherCam(Cfg):
        CAMERA_TYPE = "PICAM"

    reasons = _fresh().stale_reasons(OtherCam())
    assert any("camera_type" in reason for reason in reasons)


# --------------------------------------------------------------- persistence


def test_saves_and_loads(tmp_path):
    view = camera_view()
    original = calibrate_from_image(view, Cfg(), (COLS, ROWS), SQUARE_INCHES)
    path = str(tmp_path / "cv_calibration.json")
    original.save(path)

    loaded = Calibration.load(path)
    assert loaded.pixels_per_inch == pytest.approx(original.pixels_per_inch)
    assert loaded.source == "chessboard"
    assert loaded.homography is not None
    assert loaded.image_to_ground(160, 120) == pytest.approx(original.image_to_ground(160, 120))


def test_load_rejects_unknown_fields(tmp_path):
    path = tmp_path / "cv_calibration.json"
    path.write_text(
        '{"pixels_per_inch": 4, "scan_y": 1, "image_w": 1, "image_h": 1, '
        '"camera_type": "x", "source": "y", "surprise": 1}'
    )
    with pytest.raises(CalibrationError, match="unknown field"):
        Calibration.load(str(path))


def test_load_reports_missing_fields(tmp_path):
    path = tmp_path / "cv_calibration.json"
    path.write_text('{"pixels_per_inch": 4}')
    with pytest.raises(CalibrationError, match="missing required field"):
        Calibration.load(str(path))


def test_load_reports_bad_json(tmp_path):
    path = tmp_path / "cv_calibration.json"
    path.write_text("{not json")
    with pytest.raises(CalibrationError, match="not valid JSON"):
        Calibration.load(str(path))


def test_find_and_load_from_a_car_directory(tmp_path):
    assert find_calibration_file(None) is None
    assert find_calibration_file(str(tmp_path)) is None
    calibrate_from_image(camera_view(), Cfg(), (COLS, ROWS), SQUARE_INCHES).save(str(tmp_path / "cv_calibration.json"))
    assert find_calibration_file(str(tmp_path)) is not None
    loaded = load_calibration(str(tmp_path), Cfg())
    assert loaded is not None and loaded.source == "chessboard"


def test_manual_pixels_per_inch_is_honoured_without_a_file(tmp_path):
    """The rest of the system must be usable before anyone runs a capture."""

    class Manual(Cfg):
        CV_PIXELS_PER_INCH = 5.0

    calibration = load_calibration(str(tmp_path), Manual())
    assert calibration is not None
    assert calibration.pixels_per_inch == 5.0
    assert calibration.source == "config"
    assert calibration.homography is None


def test_no_calibration_at_all(tmp_path):
    assert load_calibration(str(tmp_path), Cfg()) is None


# ------------------------------------------------------------ tape fallback


def tape_image(left_x, right_x, width_px=6):
    img = np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8)
    for centre in (left_x, right_x):
        img[:, centre - width_px // 2 : centre + width_px // 2] = (255, 255, 0)
    return img


def test_tape_fallback_measures_scale():
    # 100 px apart, declared as 10 inches -> 10 px per inch
    calibration = calibrate_from_tape(tape_image(90, 190), Cfg(), separation_inches=10.0)
    assert calibration.pixels_per_inch == pytest.approx(10.0, abs=0.5)
    assert calibration.source == "tape"
    assert calibration.homography is None


def test_tape_fallback_is_close_to_the_board_result():
    """
    The fallback exists for people without a printer, so it has to agree with
    the board to within something useful.
    """
    view = camera_view()
    board = calibrate_from_image(view, Cfg(), (COLS, ROWS), SQUARE_INCHES)

    # Two strips whose true separation is derived from the board calibration.
    left, right = 120, 200
    inches = (right - left) / board.pixels_per_inch
    tape = calibrate_from_tape(tape_image(left, right), Cfg(), separation_inches=inches)
    assert tape.pixels_per_inch == pytest.approx(board.pixels_per_inch, rel=0.1)


def test_tape_fallback_needs_two_strips():
    single = np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8)
    single[:, 150:158] = (255, 255, 0)
    with pytest.raises(CalibrationError, match="Only one tape strip"):
        calibrate_from_tape(single, Cfg(), separation_inches=10.0)


def test_tape_fallback_reports_no_tape():
    with pytest.raises(CalibrationError, match="No tape found"):
        calibrate_from_tape(np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8), Cfg(), separation_inches=10.0)


def test_tape_fallback_rejects_bad_separation():
    with pytest.raises(CalibrationError, match="must be positive"):
        calibrate_from_tape(tape_image(90, 190), Cfg(), separation_inches=0.0)


# ---------------------------------------------------------------- preview


def test_overlay_marks_detected_corners():
    view = camera_view()
    corners = detect_board(view, (COLS, ROWS))
    painted = overlay_calibration(view, corners, Cfg.SCAN_Y, Cfg.SCAN_HEIGHT)
    assert painted.shape == view.shape
    # Green appears only where corners were drawn.
    green = (painted[:, :, 1] > 200) & (painted[:, :, 0] < 100) & (painted[:, :, 2] < 100)
    assert green.sum() > 0


def test_overlay_without_a_board_still_draws_the_band():
    blank = np.zeros((IMAGE_H, IMAGE_W, 3), np.uint8)
    painted = overlay_calibration(blank, None, Cfg.SCAN_Y, Cfg.SCAN_HEIGHT)
    assert painted.shape == blank.shape
    assert painted.any(), "expected the scan band and centre line to be drawn"
