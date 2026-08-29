"""
`donkey mcp` -- run the MCP server as the host process and let it own the
vehicle loop.

The difference from `manage.py drive --mcp` is lifecycle. There, the vehicle
owns the process and `stop` can only disarm the bridge, because returning from
`V.start()` ends the program. Here the server owns the process and runs the
vehicle on a background thread it can join and rebuild, so `stop` really does
tear the loop down and `start` really does build a new one.

The bridge instance outlives the vehicle, so an agent keeps its connection and
its view of the world across a restart.
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
import threading
import types
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import donkeycar as dk
from donkeycar.parts.mcp_server import MCP_INSTALL_HINT, MCPBridge, MCPNotInstalledError

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from donkeycar.vehicle import Vehicle

logger = logging.getLogger(__name__)

CarConfig = Any
VehicleBuilder = Callable[..., "Vehicle"]

# How long to wait for the drive loop to notice it has been asked to stop.
STOP_TIMEOUT_S = 10.0


def load_vehicle_builder(car_dir: str | None) -> tuple[VehicleBuilder, str]:
    """
    Find the `build_vehicle` to use, preferring the car's own manage.py.

    A car directory is created by copying a template, so a customised manage.py
    is the truth for that car. Older cars predate `build_vehicle` entirely, so
    fall back to the packaged template rather than refusing to start.

    Returns the builder and a short description of where it came from.
    """
    if car_dir:
        manage_py = os.path.join(os.path.expanduser(car_dir), "manage.py")
        if os.path.exists(manage_py):
            module = _load_module_from_path("car_manage", manage_py)
            builder = getattr(module, "build_vehicle", None)
            if builder is not None:
                return builder, manage_py
            logger.warning(
                "%s has no build_vehicle(); it predates the MCP work. Using the packaged "
                "cv_control template instead -- run `donkey update` to pick up local changes.",
                manage_py,
            )

    from donkeycar.templates.cv_control import build_vehicle

    return build_vehicle, "donkeycar.templates.cv_control"


def _load_module_from_path(name: str, path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    # The car directory has to be importable for a customised manage.py that
    # imports its own helpers.
    car_dir = os.path.dirname(path)
    if car_dir not in sys.path:
        sys.path.insert(0, car_dir)
    spec.loader.exec_module(module)
    return module


class VehicleSupervisor:
    """
    Builds, runs and tears down the vehicle on demand.

    Implements the bridge's Lifecycle protocol, so `start` and `stop` on the MCP
    surface mean what they say.
    """

    def __init__(
        self,
        cfg: CarConfig,
        builder: VehicleBuilder,
        builder_source: str = "",
        use_joystick: bool = False,
        camera_type: str = "single",
        car_dir: str | None = None,
    ) -> None:
        self.cfg = cfg
        self.builder = builder
        self.builder_source = builder_source
        self.use_joystick = use_joystick
        self.camera_type = camera_type

        self.bridge = MCPBridge(cfg, lifecycle=self, serve=False, car_dir=car_dir)

        self._vehicle: Vehicle | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # -------------------------------------------------------------- lifecycle

    def start(self) -> str:
        with self._lock:
            if self._is_running():
                return "already running"

            logger.info("Building vehicle from %s", self.builder_source)
            vehicle = self.builder(
                self.cfg,
                use_joystick=self.use_joystick,
                camera_type=self.camera_type,
                mcp_bridge=self.bridge,
            )
            self._vehicle = vehicle

            # Arm on start so the agent's first set_control takes effect. The
            # throttle is still zero until it asks for one.
            self.bridge.arm()

            thread = threading.Thread(target=self._run, args=(vehicle,), daemon=True)
            self._thread = thread
            thread.start()
            return "started"

    def _run(self, vehicle: Vehicle) -> None:
        try:
            vehicle.start(rate_hz=self.cfg.DRIVE_LOOP_HZ, max_loop_count=self.cfg.MAX_LOOPS)
        except Exception:
            logger.exception("Vehicle loop exited with an error")

    def stop(self) -> str:
        with self._lock:
            vehicle = self._vehicle
            thread = self._thread
            if vehicle is None:
                return "not running"

            # Zero the throttle before tearing anything down, so a car cannot
            # coast on the last commanded value while parts shut down.
            self.bridge.disarm()

            vehicle.on = False
            if thread is not None and thread.is_alive():
                thread.join(timeout=STOP_TIMEOUT_S)
                if thread.is_alive():
                    logger.error("Vehicle loop did not stop within %.0fs", STOP_TIMEOUT_S)
                    return "stop timed out"

            # Vehicle.start() calls stop() in its finally block, so the parts
            # have already been shut down by the time the thread is joined.
            self._vehicle = None
            self._thread = None
            return "stopped"

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running()

    def _is_running(self) -> bool:
        """Caller must hold the lock."""
        return self._thread is not None and self._thread.is_alive()

    # ----------------------------------------------------------------- server

    def serve(self, host: str, port: int) -> None:
        """Run the MCP server on this thread until interrupted."""
        try:
            server = self.bridge.build_server()
        except MCPNotInstalledError as exc:
            raise SystemExit(str(exc)) from exc
        logger.info("MCP server listening on http://%s:%d/mcp", host, port)
        logger.info("The vehicle is not running yet; call the `start` tool to begin.")
        try:
            server.run(transport="streamable-http", host=host, port=port)
        finally:
            self.stop()


def run(args: list[str]) -> None:
    """Entry point for `donkey mcp`."""
    parser = argparse.ArgumentParser(prog="mcp", usage="%(prog)s [options]")
    parser.add_argument("--car", default=None, help="path to the car directory, e.g. ~/mycar")
    parser.add_argument("--myconfig", default="myconfig.py", help="myconfig file to use")
    parser.add_argument("--host", default=None, help="address to bind (default from config)")
    parser.add_argument("--port", type=int, default=None, help="port to bind (default from config)")
    parser.add_argument("--js", action="store_true", help="use a physical joystick as well")
    parser.add_argument("--camera", default="single", choices=["single", "stereo"])
    parsed = parser.parse_args(args)

    # Fail before loading config or touching the camera: the whole command is
    # the MCP server, so without the package there is nothing to run.
    if importlib.util.find_spec("mcp") is None:
        raise SystemExit(MCP_INSTALL_HINT)

    car_dir = os.path.expanduser(parsed.car) if parsed.car else os.getcwd()
    cfg = dk.load_config(config_path=os.path.join(car_dir, "config.py"), myconfig=parsed.myconfig)

    builder, source = load_vehicle_builder(car_dir)
    supervisor = VehicleSupervisor(
        cfg,
        builder,
        builder_source=source,
        use_joystick=parsed.js,
        camera_type=parsed.camera,
        car_dir=car_dir,
    )

    host = parsed.host or getattr(cfg, "MCP_SERVER_HOST", "127.0.0.1")
    port = parsed.port or getattr(cfg, "MCP_SERVER_PORT", 8891)
    supervisor.serve(host, port)
