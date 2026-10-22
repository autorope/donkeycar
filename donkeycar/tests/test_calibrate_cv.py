"""
Tests for `donkey calibrate-cv`: the camera-intrinsics capture, its saved
views, `--from-images`, and that the ground capture is left as it was.

The views are rendered: a checkerboard image warped through a known camera at
varied positions and tilts, so the corner detector runs on real pixels.
"""

import json
import os

import cv2
import numpy as np
import pytest
from tornado.testing import AsyncHTTPTestCase

from donkeycar.management.calibrate_cv import (
    VIEWS_DIRNAME,
    VIEWS_MANIFEST,
    CalibrationApp,
    IntrinsicsApp,
    IntrinsicsCapture,
    _expand_images,
    quadrant_counts,
    solve_from_images,
)
from donkeycar.parts.camera_intrinsics import INTRINSICS_FILENAME, MIN_VIEWS, CameraIntrinsics
from donkeycar.parts.cv_calibration import CALIBRATION_FILENAME, CalibrationError

from .test_cv_calibration import board_image, camera_view

COLS, ROWS = 9, 6
SQUARE_PX, MARGIN = 30, 60
IMAGE_W, IMAGE_H = 320, 240
TRUE_K = np.array([[230.0, 0.0, 160.0], [0.0, 230.0, 120.0], [0.0, 0.0, 1.0]])


class Cfg:
    IMAGE_W = IMAGE_W
    IMAGE_H = IMAGE_H
    CAMERA_TYPE = "MOCK"
    SCAN_Y = 120
    SCAN_HEIGHT = 20


def _texture_to_board():
    """Board-texture pixels to board inches, with inner corner (0, 0) at the origin."""
    offset = MARGIN + SQUARE_PX
    return np.array([[1 / SQUARE_PX, 0, -offset / SQUARE_PX], [0, 1 / SQUARE_PX, -offset / SQUARE_PX], [0, 0, 1]])


def rendered_views(count=14, seed=3):
    """RGB frames of the board held up in front of a pinhole camera, covering the frame."""
    texture = board_image(COLS, ROWS, SQUARE_PX, MARGIN)
    to_board = _texture_to_board()
    # The board's outer edge, in inches, so the whole board must land in frame
    outline = np.array([[-1, -1, 0], [COLS, -1, 0], [COLS, ROWS, 0], [-1, ROWS, 0]], dtype=np.float64)
    centre = np.array([(COLS - 1) / 2, (ROWS - 1) / 2, 0.0])

    rng = np.random.default_rng(seed)
    frames = []
    while len(frames) < count:
        rvec = rng.uniform(-0.5, 0.5, 3)
        rvec[2] = rng.uniform(-0.2, 0.2)
        rotation, _ = cv2.Rodrigues(rvec)
        tvec = np.array([rng.uniform(-5.0, 5.0), rng.uniform(-3.5, 3.5), rng.uniform(16.0, 22.0)])
        tvec = tvec - rotation @ centre
        edge, _ = cv2.projectPoints(outline, rvec, tvec, TRUE_K, None)
        edge = edge.reshape(-1, 2)
        if edge.min() < 3 or (edge[:, 0] > IMAGE_W - 3).any() or (edge[:, 1] > IMAGE_H - 3).any():
            continue
        plane_to_image = TRUE_K @ np.column_stack([rotation[:, 0], rotation[:, 1], tvec])
        warp = plane_to_image @ to_board
        frame = cv2.warpPerspective(
            texture, warp, (IMAGE_W, IMAGE_H), flags=cv2.INTER_AREA, borderValue=(255, 255, 255)
        )
        frames.append(frame)
    return frames


@pytest.fixture(scope="module")
def views():
    return rendered_views()


def _session(tmp_path, clock_at=1_790_000_000.0):
    return IntrinsicsCapture(str(tmp_path), Cfg(), (COLS, ROWS), 1.0, clock=lambda: clock_at)


def _manifest(session):
    with open(os.path.join(session.folder, VIEWS_MANIFEST)) as handle:
        return json.load(handle)


def _blank():
    return np.full((IMAGE_H, IMAGE_W, 3), 200, np.uint8)


# --------------------------------------------------------------------- capture


def test_a_view_with_no_board_is_refused_and_adds_nothing(tmp_path):
    session = _session(tmp_path)
    with pytest.raises(CalibrationError, match="No 9x6 board found"):
        session.add_view(_blank())
    assert session.status()["views"] == 0
    assert not (tmp_path / VIEWS_DIRNAME).exists()


def test_every_view_added_is_saved_in_a_timestamped_folder(tmp_path, views):
    session = _session(tmp_path)
    for frame in views[:3]:
        status = session.add_view(frame)
    assert status["views"] == 3 and status["needed"] == MIN_VIEWS - 3
    folder = tmp_path / VIEWS_DIRNAME / os.path.basename(session.folder)
    assert sorted(os.listdir(folder)) == ["view_01.png", "view_02.png", "view_03.png"]
    # Saved as the camera delivered it, colour order included
    saved = cv2.cvtColor(cv2.imread(str(folder / "view_02.png")), cv2.COLOR_BGR2RGB)
    assert np.array_equal(saved, views[1])


def test_solve_before_enough_views_is_refused_and_recorded(tmp_path, views):
    session = _session(tmp_path)
    for frame in views[:5]:
        session.add_view(frame)
    with pytest.raises(CalibrationError, match=f"add {MIN_VIEWS - 5} more"):
        session.solve()

    assert not (tmp_path / INTRINSICS_FILENAME).exists()
    manifest = _manifest(session)
    assert manifest["result"]["ok"] is False
    assert "more" in manifest["result"]["error"]
    assert [v["file"] for v in manifest["views"]] == [f"view_{i:02d}.png" for i in range(1, 6)]
    assert all(v["used"] is False for v in manifest["views"])


def test_a_full_capture_writes_intrinsics_that_load(tmp_path, views):
    session = _session(tmp_path)
    for frame in views:
        session.add_view(frame)
    assert session.status()["missing_quadrants"] == []
    result = session.solve()

    loaded = CameraIntrinsics.load(str(tmp_path / INTRINSICS_FILENAME))
    assert loaded.fx == pytest.approx(TRUE_K[0, 0], rel=0.03)
    assert loaded.view_count == len(views)
    assert result["ok"] is True and result["folder"] == session.folder

    manifest = _manifest(session)
    assert manifest["result"]["ok"] is True
    assert len(manifest["views"]) == len(views)
    assert all(v["used"] is True and v["error_px"] < 1.0 for v in manifest["views"])


def test_a_refused_fit_still_records_each_views_error(tmp_path, views):
    """A poor fit is refused, but the manifest must say which view was poor."""
    session = _session(tmp_path)
    for frame in views:
        session.add_view(frame)
    session.corners[2] = session.corners[2] + np.random.default_rng(1).normal(0, 8.0, session.corners[2].shape)
    with pytest.raises(CalibrationError, match="worst view is 3"):
        session.solve()
    manifest = _manifest(session)
    errors = [v["error_px"] for v in manifest["views"]]
    assert all(e is not None for e in errors)
    assert errors.index(max(errors)) == 2


def test_a_second_capture_leaves_the_first_untouched(tmp_path, views):
    first = _session(tmp_path, clock_at=1_790_000_000.0)
    for frame in views[:2]:
        first.add_view(frame)
    before = sorted(os.listdir(first.folder))

    second = _session(tmp_path, clock_at=1_790_000_100.0)
    second.add_view(views[2])
    assert second.folder != first.folder
    assert sorted(os.listdir(first.folder)) == before
    assert sorted(os.listdir(second.folder)) == ["view_01.png"]


def test_quadrant_counts_follow_the_corners():
    left = np.array([[10.0, 10.0], [10.0, 200.0]])
    everywhere = np.array([[10.0, 10.0], [300.0, 10.0], [10.0, 200.0], [300.0, 200.0]])
    counts = quadrant_counts([left, everywhere], IMAGE_W, IMAGE_H)
    assert counts == {"top-left": 2, "top-right": 1, "bottom-left": 2, "bottom-right": 1}


# ---------------------------------------------------------------- from images


def test_from_images_reproduces_a_saved_capture(tmp_path, views):
    session = _session(tmp_path)
    for frame in views:
        session.add_view(frame)
    captured = session.solve()

    elsewhere = tmp_path / "laptop"
    elsewhere.mkdir()
    result = solve_from_images(_expand_images(session.folder), str(elsewhere), Cfg(), (COLS, ROWS), 1.0)
    assert result["fx"] == captured["fx"]
    assert result["rms_error_px"] == captured["rms_error_px"]
    assert CameraIntrinsics.load(str(elsewhere / INTRINSICS_FILENAME)).view_count == len(views)
    # It solves from frames already on disk, so it keeps no views of its own
    assert not (elsewhere / VIEWS_DIRNAME).exists()


def test_from_images_skips_frames_without_a_board(tmp_path, views):
    folder = tmp_path / "frames"
    folder.mkdir()
    for index, frame in enumerate(views):
        cv2.imwrite(str(folder / f"f{index:02d}.png"), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(folder / "blank.png"), _blank())
    result = solve_from_images(_expand_images(str(folder / "*.png")), str(tmp_path), Cfg(), (COLS, ROWS), 1.0)
    assert result["skipped"] == [str(folder / "blank.png")]
    assert result["view_count"] == len(views)


def test_from_images_with_nothing_matched_is_refused(tmp_path):
    with pytest.raises(CalibrationError, match="No images matched"):
        solve_from_images([], str(tmp_path), Cfg())


# ------------------------------------------------------------------- the pages


class FakeCamera:
    def __init__(self, frame):
        self.frame = frame

    def run(self):
        return self.frame


class TestIntrinsicsPages(AsyncHTTPTestCase):
    def get_app(self):
        import tempfile

        self.car_dir = tempfile.mkdtemp()
        self.camera = FakeCamera(_blank())
        self.session = IntrinsicsCapture(self.car_dir, Cfg(), (COLS, ROWS), 1.0)
        return IntrinsicsApp(self.camera, self.session)

    def test_add_view_without_a_board_is_a_400_and_adds_nothing(self):
        response = self.fetch("/add", method="POST", body="")
        assert response.code == 400
        body = json.loads(response.body)
        assert "No 9x6 board" in body["error"] and body["status"]["views"] == 0

    def test_add_view_with_a_board_reports_the_folder(self):
        self.camera.frame = rendered_views(count=1)[0]
        body = json.loads(self.fetch("/add", method="POST", body="").body)
        assert body["ok"] is True and body["status"]["views"] == 1
        assert body["status"]["folder"] == self.session.folder

    def test_solve_too_early_says_how_many_more(self):
        response = self.fetch("/solve", method="POST", body="")
        assert response.code == 400
        assert f"add {MIN_VIEWS} more" in json.loads(response.body)["error"]

    def test_the_page_tells_you_to_hold_the_board_up(self):
        assert b"Hold the checkerboard" in self.fetch("/").body


class TestGroundCaptureUnchanged(AsyncHTTPTestCase):
    def get_app(self):
        import tempfile

        self.car_dir = tempfile.mkdtemp()
        output = os.path.join(self.car_dir, CALIBRATION_FILENAME)
        return CalibrationApp(FakeCamera(camera_view()), Cfg(), output, (COLS, ROWS), 1.0, 0.0, 0.0)

    def test_the_ground_capture_writes_only_its_own_file(self):
        response = self.fetch("/capture", method="POST", body="")
        assert response.code == 200, response.body
        assert sorted(os.listdir(self.car_dir)) == [CALIBRATION_FILENAME]
