"""
`donkey calibrate-cv` -- measure how many pixels an inch is worth on the ground.

Lay a checkerboard flat on the floor in front of the car, open the preview page,
and slide the board until the scan band crosses it and its corners light up
green. Then capture. The overlay is the point: it turns a geometry problem into
"make the line cross the board".

Reuses the existing MJPEG stream machinery rather than inventing one, so this
looks and behaves like the PWM calibration page that is already there.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from typing import Any, Protocol, cast

import numpy as np
import tornado.web
from tornado.ioloop import IOLoop

import donkeycar as dk
from donkeycar.parts.cv_calibration import (
    CALIBRATION_FILENAME,
    DEFAULT_PATTERN,
    DEFAULT_SQUARE_INCHES,
    CalibrationError,
    calibrate_from_image,
    calibrate_from_tape,
    detect_board,
    overlay_calibration,
)
from donkeycar.utils import arr_to_binary

logger = logging.getLogger(__name__)

CarConfig = Any


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
            painted = overlay_calibration(frame, corners, app.scan_y, app.scan_height)
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
        help="distance from the car to the board's first corner; leave 0 to measure in the board's own frame",
    )
    parser.add_argument(
        "--lateral-inches", type=float, default=0.0, help="offset of the board's first corner from the centreline"
    )
    parser.add_argument(
        "--tape-separation-inches",
        type=float,
        default=None,
        help="headless fallback: measure two tape strips this far apart instead of a board",
    )
    parsed = parser.parse_args(args)

    car_dir = os.path.expanduser(parsed.car) if parsed.car else os.getcwd()
    cfg = dk.load_config(config_path=os.path.join(car_dir, "config.py"), myconfig=parsed.myconfig)
    output_path = os.path.join(car_dir, CALIBRATION_FILENAME)

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

    app = CalibrationApp(
        camera,
        cfg,
        output_path,
        (parsed.cols, parsed.rows),
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
