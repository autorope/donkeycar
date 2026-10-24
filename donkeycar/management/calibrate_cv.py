"""
`donkey calibrate-cv` -- measure how many pixels an inch is worth on the ground.

Lay a checkerboard flat on the floor in front of the car, open the preview page,
and slide the board until the scan band crosses it and its corners light up
green. Then capture. The overlay is the point: it turns a geometry problem into
"make the line cross the board".

Reuses the existing MJPEG stream machinery rather than inventing one, so this
looks and behaves like the PWM calibration page that is already there.

`--intrinsics` runs the other, optional calibration instead: the camera's focal
length and lens distortion, from many views of the board held up and tilted.
Every view is kept on disk, so `--from-images` can solve again later without
the car.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any, Protocol, cast

import cv2
import numpy as np
import tornado.web
from tornado.ioloop import IOLoop

import donkeycar as dk
from donkeycar.parts.camera_intrinsics import (
    INTRINSICS_FILENAME,
    MIN_VIEWS,
    CameraIntrinsics,
    IntrinsicsRefused,
    missing_quadrants,
    solve_intrinsics,
)
from donkeycar.parts.cv_calibration import (
    CALIBRATION_FILENAME,
    DEFAULT_PATTERN,
    DEFAULT_SQUARE_INCHES,
    CalibrationError,
    calibrate_from_image,
    calibrate_from_tape,
    detect_board,
    find_reference_corner,
    overlay_calibration,
)
from donkeycar.utils import arr_to_binary

logger = logging.getLogger(__name__)

CarConfig = Any

#: Where `--intrinsics` keeps each capture's views, inside the car directory
VIEWS_DIRNAME = "camera_calibration_views"
VIEWS_MANIFEST = "views.json"


class CameraPart(Protocol):
    """Any donkeycar camera part: it hands back the most recent frame."""

    def run(self) -> np.ndarray | None: ...


PAGE = """<!doctype html>
<title>Donkeycar CV calibration</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 46rem; }}
  img {{ width: 100%; image-rendering: pixelated; border: 1px solid #ccc; }}
  button {{ font-size: 1rem; padding: .6rem 1.2rem; }}
  .ok {{ color: #157f3b; }} .bad {{ color: #b23a32; }}
  pre {{ background: #f4f4f6; padding: 1rem; overflow-x: auto; }}
</style>
<h1>CV calibration</h1>
<p>
  Lay the checkerboard <strong>flat on the floor</strong> in front of the car.
  Slide it until the blue band crosses the board and the corners turn green,
  then capture. A board held upright gives meaningless numbers.
</p>
<p>
  The ringed corner, <strong>measure to here</strong>, is the reference corner: the inner corner
  nearest the car and furthest left. <code>--forward-inches</code> is the floor distance straight
  ahead from the mark under the camera lens to it, and <code>--lateral-inches</code> its distance
  sideways from the car's centreline, negative to the left.
</p>
<p>Board: {cols}&times;{rows} inner corners, {square} inch squares.</p>
<img src="/video" alt="camera preview with the scan band and detected corners">
<p><button onclick="capture()">Capture calibration</button></p>
<pre id="out">Waiting.</pre>
<script>
async function capture() {{
  const out = document.getElementById('out');
  out.textContent = 'Capturing...';
  const res = await fetch('/capture', {{method: 'POST'}});
  const body = await res.json();
  out.textContent = JSON.stringify(body, null, 2);
}}
</script>
"""


class PreviewHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        app = cast(CalibrationApp, self.application)
        self.write(
            PAGE.format(
                cols=app.pattern[0],
                rows=app.pattern[1],
                square=app.square_inches,
            )
        )


class VideoHandler(tornado.web.RequestHandler):
    """MJPEG stream of the preview, with the scan band and corners drawn on."""

    async def get(self) -> None:
        app = cast(CalibrationApp, self.application)
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")
        boundary = "--boundarydonotcross\n"
        while True:
            frame = app.latest_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            corners = detect_board(frame, app.pattern)
            app.last_corners = corners
            height, width = frame.shape[:2]
            reference = find_reference_corner(corners, width, height, app.pattern, app.square_inches)
            painted = overlay_calibration(frame, corners, app.scan_y, app.scan_height, reference)
            jpeg = arr_to_binary(painted)
            self.write(boundary)
            self.write("Content-type: image/jpeg\r\n")
            self.write(f"Content-length: {len(jpeg)}\r\n\r\n")
            self.write(jpeg)
            try:
                await self.flush()
            except tornado.iostream.StreamClosedError:
                return
            await asyncio.sleep(0.1)


class CaptureHandler(tornado.web.RequestHandler):
    def post(self) -> None:
        app = cast(CalibrationApp, self.application)
        frame = app.latest_frame()
        if frame is None:
            self.set_status(503)
            self.write({"ok": False, "error": "No camera frame yet."})
            return
        try:
            calibration = calibrate_from_image(
                frame,
                app.cfg,
                app.pattern,
                app.square_inches,
                origin_forward_inches=app.origin_forward_inches,
                origin_lateral_inches=app.origin_lateral_inches,
            )
        except CalibrationError as exc:
            self.set_status(400)
            self.write({"ok": False, "error": str(exc)})
            return

        calibration.save(app.output_path)
        self.write(
            {
                "ok": True,
                "written_to": app.output_path,
                "pixels_per_inch": round(calibration.pixels_per_inch, 3),
                "reprojection_error_inches": round(calibration.reprojection_error_px or 0.0, 4),
                "scan_y": calibration.scan_y,
            }
        )


class CalibrationApp(tornado.web.Application):
    def __init__(
        self,
        camera: CameraPart,
        cfg: CarConfig,
        output_path: str,
        pattern: tuple[int, int],
        square_inches: float,
        origin_forward_inches: float,
        origin_lateral_inches: float,
    ) -> None:
        self.camera = camera
        self.cfg = cfg
        self.output_path = output_path
        self.pattern = pattern
        self.square_inches = square_inches
        self.origin_forward_inches = origin_forward_inches
        self.origin_lateral_inches = origin_lateral_inches
        self.scan_y = int(getattr(cfg, "SCAN_Y", 100))
        self.scan_height = int(getattr(cfg, "SCAN_HEIGHT", 20))
        self.last_corners: np.ndarray | None = None
        super().__init__(
            [(r"/", PreviewHandler), (r"/video", VideoHandler), (r"/capture", CaptureHandler)],
            debug=False,
        )

    def latest_frame(self) -> np.ndarray | None:
        return self.camera.run_threaded() if hasattr(self.camera, "run_threaded") else self.camera.run()


# ----------------------------------------------------------- camera intrinsics


class IntrinsicsCapture:
    """
    One `--intrinsics` session: the views collected so far, and their folder.

    Every view is written to disk as it is added, so nothing a capture saw is
    lost to a refused solve -- the frames are what shows why it was refused.
    The folder is created on the first view, so opening the page and leaving
    writes nothing.
    """

    def __init__(
        self,
        car_dir: str,
        cfg: CarConfig,
        pattern: tuple[int, int] = DEFAULT_PATTERN,
        square_inches: float = DEFAULT_SQUARE_INCHES,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.cfg = cfg
        self.pattern = pattern
        self.square_inches = square_inches
        self.output_path = os.path.join(car_dir, INTRINSICS_FILENAME)
        self.started_at = clock()
        stamp = time.strftime("%Y-%m-%dT%H-%M-%S", time.localtime(self.started_at))
        self.folder = os.path.join(car_dir, VIEWS_DIRNAME, stamp)
        self.files: list[str] = []
        self.corners: list[np.ndarray] = []
        self.image_size: tuple[int, int] | None = None

    def add_view(self, frame: np.ndarray) -> dict[str, Any]:
        """Keep this frame as a view if the board is in it; refuse it otherwise."""
        corners = detect_board(frame, self.pattern)
        if corners is None:
            raise CalibrationError(
                f"No {self.pattern[0]}x{self.pattern[1]} board found in this frame; nothing was added. "
                "Hold the whole board in view, still and well lit."
            )
        height, width = frame.shape[:2]
        if self.image_size is not None and self.image_size != (width, height):
            raise CalibrationError(f"This frame is {width}x{height}, but earlier views were {self.image_size}.")

        os.makedirs(self.folder, exist_ok=True)
        name = f"view_{len(self.files) + 1:02d}.png"
        # Camera parts hand back RGB; OpenCV writes BGR
        cv2.imwrite(os.path.join(self.folder, name), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        self.files.append(name)
        self.corners.append(corners)
        self.image_size = (width, height)
        return self.status()

    def status(self) -> dict[str, Any]:
        width, height = self.image_size or (int(self.cfg.IMAGE_W), int(self.cfg.IMAGE_H))
        return {
            "views": len(self.corners),
            "needed": max(0, MIN_VIEWS - len(self.corners)),
            "coverage": quadrant_counts(self.corners, width, height),
            "missing_quadrants": missing_quadrants(self.corners, width, height) if self.corners else [],
            "folder": self.folder if self.files else None,
        }

    def solve(self) -> dict[str, Any]:
        """
        Solve from the views so far, write camera_intrinsics.json if it is
        accepted, and record the outcome in views.json either way.
        """
        width, height = self.image_size or (int(self.cfg.IMAGE_W), int(self.cfg.IMAGE_H))
        camera_type = str(getattr(self.cfg, "CAMERA_TYPE", "unknown"))
        try:
            intrinsics, view_errors = solve_intrinsics(
                self.corners, width, height, camera_type, self.pattern, self.square_inches
            )
        except IntrinsicsRefused as exc:
            self._write_manifest(used=False, view_errors=exc.view_errors, result={"ok": False, "error": str(exc)})
            raise

        intrinsics.save(self.output_path)
        result = {"ok": True, "written_to": self.output_path, **summarise(intrinsics)}
        self._write_manifest(used=True, view_errors=view_errors, result=result)
        return {**result, "folder": self.folder}

    def _write_manifest(self, used: bool, view_errors: list[float] | None, result: dict[str, Any]) -> None:
        if not self.files:
            return
        errors: list[float | None] = list(view_errors) if view_errors else [None] * len(self.files)
        manifest = {
            "pattern": list(self.pattern),
            "square_inches": self.square_inches,
            "image_w": self.image_size[0] if self.image_size else None,
            "image_h": self.image_size[1] if self.image_size else None,
            "camera_type": str(getattr(self.cfg, "CAMERA_TYPE", "unknown")),
            "started_at": self.started_at,
            "solved_at": time.time(),
            "result": result,
            "views": [
                {"file": name, "used": used, "error_px": error} for name, error in zip(self.files, errors, strict=True)
            ],
        }
        with open(os.path.join(self.folder, VIEWS_MANIFEST), "w") as handle:
            json.dump(manifest, handle, indent=2)


def quadrant_counts(corner_sets: list[np.ndarray], image_w: int, image_h: int) -> dict[str, int]:
    """How many views reach each quadrant of the frame, for the page's coverage grid."""
    counts = {"top-left": 0, "top-right": 0, "bottom-left": 0, "bottom-right": 0}
    for corners in corner_sets:
        for name in counts:
            if name not in missing_quadrants([corners], image_w, image_h):
                counts[name] += 1
    return counts


def summarise(intrinsics: CameraIntrinsics) -> dict[str, Any]:
    return {
        "fx": round(intrinsics.fx, 2),
        "fy": round(intrinsics.fy, 2),
        "cx": round(intrinsics.cx, 2),
        "cy": round(intrinsics.cy, 2),
        "distortion": [round(k, 5) for k in intrinsics.distortion],
        "rms_error_px": round(intrinsics.rms_error_px or 0.0, 4),
        "view_count": intrinsics.view_count,
    }


def solve_from_images(
    paths: list[str],
    car_dir: str,
    cfg: CarConfig,
    pattern: tuple[int, int] = DEFAULT_PATTERN,
    square_inches: float = DEFAULT_SQUARE_INCHES,
) -> dict[str, Any]:
    """
    Solve from saved frames, with no camera and no page.

    For a laptop, or for re-solving a folder an earlier capture kept. Frames
    with no board are skipped and listed. No views folder is written: the
    frames are already on disk.
    """
    if not paths:
        raise CalibrationError("No images matched.")
    corner_sets: list[np.ndarray] = []
    skipped: list[str] = []
    size: tuple[int, int] | None = None
    for path in sorted(paths):
        image = cv2.imread(path)
        if image is None:
            skipped.append(path)
            continue
        height, width = image.shape[:2]
        if size is not None and size != (width, height):
            raise CalibrationError(f"{path} is {width}x{height}, but earlier images were {size[0]}x{size[1]}.")
        corners = detect_board(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), pattern)
        if corners is None:
            skipped.append(path)
            continue
        corner_sets.append(corners)
        size = (width, height)

    if size is None:
        raise CalibrationError(f"No {pattern[0]}x{pattern[1]} board found in any of the {len(paths)} image(s).")
    camera_type = str(getattr(cfg, "CAMERA_TYPE", "unknown"))
    intrinsics, _errors = solve_intrinsics(corner_sets, size[0], size[1], camera_type, pattern, square_inches)
    output_path = os.path.join(car_dir, INTRINSICS_FILENAME)
    intrinsics.save(output_path)
    return {"ok": True, "written_to": output_path, "skipped": skipped, **summarise(intrinsics)}


INTRINSICS_PAGE = """<!doctype html>
<title>Donkeycar camera calibration</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 46rem; }}
  img {{ width: 100%; image-rendering: pixelated; border: 1px solid #ccc; }}
  button {{ font-size: 1rem; padding: .6rem 1.2rem; margin-right: .5rem; }}
  table {{ border-collapse: collapse; margin: 1rem 0; }}
  td {{ border: 1px solid #ccc; width: 7rem; height: 3rem; text-align: center; }}
  td.empty {{ background: #fbe9e7; }}
  pre {{ background: #f4f4f6; padding: 1rem; overflow-x: auto; }}
</style>
<h1>Camera calibration</h1>
<p>
  Hold the checkerboard <strong>up in front of the camera</strong> -- not flat on the floor --
  and keep it still. Press <strong>Add view</strong> when the corners turn green, then move or
  tilt the board and add another. Fill every part of the frame, corners included, and tilt the
  board left, right, up and down. At least {min_views} views; 15 to 20 is better.
</p>
<p>Board: {cols}&times;{rows} inner corners, {square} inch squares.</p>
<img src="/video" alt="camera preview with the detected corners">
<p>
  <button onclick="post('/add')">Add view</button>
  <button onclick="post('/solve')">Solve</button>
</p>
<table id="grid"></table>
<pre id="out">No views yet.</pre>
<script>
function draw(status) {{
  if (!status.coverage) return;
  const c = status.coverage;
  const cell = q => `<td class="${{c[q] ? '' : 'empty'}}">${{q}}<br>${{c[q]}} view(s)</td>`;
  document.getElementById('grid').innerHTML =
    `<tr>${{cell('top-left')}}${{cell('top-right')}}</tr><tr>${{cell('bottom-left')}}${{cell('bottom-right')}}</tr>`;
}}
async function post(path) {{
  const out = document.getElementById('out');
  out.textContent = 'Working...';
  const res = await fetch(path, {{method: 'POST'}});
  const body = await res.json();
  draw(body.status || body);
  out.textContent = JSON.stringify(body, null, 2);
}}
fetch('/status').then(r => r.json()).then(draw);
</script>
"""


class IntrinsicsPageHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        app = cast(IntrinsicsApp, self.application)
        self.write(
            INTRINSICS_PAGE.format(
                cols=app.session.pattern[0],
                rows=app.session.pattern[1],
                square=app.session.square_inches,
                min_views=MIN_VIEWS,
            )
        )


class IntrinsicsVideoHandler(tornado.web.RequestHandler):
    """MJPEG preview with the board's corners drawn on when they are found."""

    async def get(self) -> None:
        app = cast(IntrinsicsApp, self.application)
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")
        boundary = "--boundarydonotcross\n"
        while True:
            frame = app.latest_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            painted = frame.copy()
            corners = detect_board(frame, app.session.pattern)
            if corners is not None:
                cv2.drawChessboardCorners(
                    painted, app.session.pattern, corners.reshape(-1, 1, 2).astype(np.float32), True
                )
            jpeg = arr_to_binary(painted)
            self.write(boundary)
            self.write("Content-type: image/jpeg\r\n")
            self.write(f"Content-length: {len(jpeg)}\r\n\r\n")
            self.write(jpeg)
            try:
                await self.flush()
            except tornado.iostream.StreamClosedError:
                return
            await asyncio.sleep(0.2)


class IntrinsicsStatusHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        self.write(cast(IntrinsicsApp, self.application).session.status())


class AddViewHandler(tornado.web.RequestHandler):
    def post(self) -> None:
        app = cast(IntrinsicsApp, self.application)
        frame = app.latest_frame()
        if frame is None:
            self.set_status(503)
            self.write({"ok": False, "error": "No camera frame yet.", "status": app.session.status()})
            return
        try:
            status = app.session.add_view(frame)
        except CalibrationError as exc:
            self.set_status(400)
            self.write({"ok": False, "error": str(exc), "status": app.session.status()})
            return
        self.write({"ok": True, "status": status})


class SolveHandler(tornado.web.RequestHandler):
    def post(self) -> None:
        app = cast(IntrinsicsApp, self.application)
        try:
            result = app.session.solve()
        except CalibrationError as exc:
            self.set_status(400)
            self.write({"ok": False, "error": str(exc), "status": app.session.status()})
            return
        self.write({**result, "status": app.session.status()})


class IntrinsicsApp(tornado.web.Application):
    def __init__(self, camera: CameraPart, session: IntrinsicsCapture) -> None:
        self.camera = camera
        self.session = session
        super().__init__(
            [
                (r"/", IntrinsicsPageHandler),
                (r"/video", IntrinsicsVideoHandler),
                (r"/status", IntrinsicsStatusHandler),
                (r"/add", AddViewHandler),
                (r"/solve", SolveHandler),
            ],
            debug=False,
        )

    def latest_frame(self) -> np.ndarray | None:
        return self.camera.run_threaded() if hasattr(self.camera, "run_threaded") else self.camera.run()


def _expand_images(pattern: str) -> list[str]:
    """A glob, or a folder an earlier capture kept (its view PNGs)."""
    path = os.path.expanduser(pattern)
    if os.path.isdir(path):
        path = os.path.join(path, "*.png")
    return glob.glob(path)


def run(args: list[str]) -> None:
    """Entry point for `donkey calibrate-cv`."""
    parser = argparse.ArgumentParser(prog="calibrate-cv", usage="%(prog)s [options]")
    parser.add_argument("--car", default=None, help="path to the car directory, e.g. ~/mycar")
    parser.add_argument("--myconfig", default="myconfig.py")
    parser.add_argument("--port", type=int, default=8892, help="port for the preview page")
    parser.add_argument("--cols", type=int, default=DEFAULT_PATTERN[0], help="inner corners across")
    parser.add_argument("--rows", type=int, default=DEFAULT_PATTERN[1], help="inner corners down")
    parser.add_argument("--square-inches", type=float, default=DEFAULT_SQUARE_INCHES)
    parser.add_argument(
        "--forward-inches",
        type=float,
        default=0.0,
        help=(
            "floor distance straight ahead from the mark under the camera lens to the board's reference corner "
            "(the inner corner nearest the car and furthest left, ringed on the preview); 0 measures from the corner"
        ),
    )
    parser.add_argument(
        "--lateral-inches",
        type=float,
        default=0.0,
        help="sideways distance from the car's centreline to the reference corner, negative to the left",
    )
    parser.add_argument(
        "--tape-separation-inches",
        type=float,
        default=None,
        help="headless fallback: measure two tape strips this far apart instead of a board",
    )
    parser.add_argument(
        "--intrinsics",
        action="store_true",
        help="calibrate the camera itself (focal length, lens distortion) from views of a board held up",
    )
    parser.add_argument(
        "--from-images",
        default=None,
        metavar="GLOB",
        help="solve the camera calibration from saved frames, or a saved views folder, with no camera",
    )
    parsed = parser.parse_args(args)

    car_dir = os.path.expanduser(parsed.car) if parsed.car else os.getcwd()
    cfg = dk.load_config(config_path=os.path.join(car_dir, "config.py"), myconfig=parsed.myconfig)
    output_path = os.path.join(car_dir, CALIBRATION_FILENAME)
    pattern = (parsed.cols, parsed.rows)

    # Before the camera is opened: this mode needs none, and may run on a laptop
    if parsed.from_images is not None:
        try:
            result = solve_from_images(_expand_images(parsed.from_images), car_dir, cfg, pattern, parsed.square_inches)
        except CalibrationError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(result, indent=2))
        return

    from donkeycar.templates.complete import add_camera
    from donkeycar.vehicle import Vehicle

    vehicle = Vehicle()
    add_camera(vehicle, cfg, camera_type="single")
    camera = vehicle.parts[0]["part"]
    for entry in vehicle.parts:
        if entry.get("thread"):
            entry["thread"].start()
    time.sleep(1.0)

    if parsed.tape_separation_inches is not None:
        _capture_from_tape(camera, cfg, parsed.tape_separation_inches, output_path)
        return

    if parsed.intrinsics:
        session = IntrinsicsCapture(car_dir, cfg, pattern, parsed.square_inches)
        intrinsics_app = IntrinsicsApp(camera, session)
        logger.info("Camera calibration on http://localhost:%d -- hold the board up and add views.", parsed.port)
        asyncio.set_event_loop(asyncio.new_event_loop())
        intrinsics_app.listen(parsed.port)
        IOLoop.current().start()
        return

    app = CalibrationApp(
        camera,
        cfg,
        output_path,
        pattern,
        parsed.square_inches,
        parsed.forward_inches,
        parsed.lateral_inches,
    )
    logger.info("Calibration preview on http://localhost:%d -- lay the board flat and capture.", parsed.port)
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.listen(parsed.port)
    IOLoop.current().start()


def _capture_from_tape(camera: CameraPart, cfg: CarConfig, separation_inches: float, output_path: str) -> None:
    frame = camera.run_threaded() if hasattr(camera, "run_threaded") else camera.run()
    if frame is None:
        raise SystemExit("No camera frame; is the camera configured?")
    calibration = calibrate_from_tape(frame, cfg, separation_inches)
    calibration.save(output_path)
    logger.info(
        "Wrote %s: %.3f pixels per inch (scale only, no ground measurements)", output_path, calibration.pixels_per_inch
    )
