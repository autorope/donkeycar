"""
An MCP server that exposes the CV autopilot to an LLM agent.

The agent reads the car's state and sets slow-changing intent -- a throttle
ceiling and a lane offset -- while the line follower keeps steering at loop
rate. The agent is never in the steering path.

Two things in here are load-bearing and easy to get wrong:

* **Throttle is a ceiling, not a command.** The CV controller ramps its own
  throttle and slows itself in corners. An absolute agent value would fight that
  ramp, so `cv_control-set_control(throttle=v)` applies `min(v, cv_throttle)` going
  forward. Zero is always a hard stop.
* **State is exchanged under a lock.** `run_threaded` runs on the vehicle loop
  thread and the tool handlers run on the server's event loop thread. A frame
  plus several correlated scalars is a torn read waiting to happen.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

from donkeycar.parts.camera_intrinsics import CameraIntrinsics, load_intrinsics
from donkeycar.parts.cv_calibration import Calibration, load_calibration
from donkeycar.parts.object_distance import (
    check_sizes,
    estimate_speed,
    measure_object,
    parse_box,
    parse_observations,
    unknown,
    unknown_speed,
)
from donkeycar.parts.track_config import (
    CV_CONTROL,
    TRACK_FILENAME,
    TrackConfig,
    TrackConfigError,
    default_track,
    find_track_file,
    load_track,
)
from donkeycar.utils import arr_to_binary

# The autopilot this bridge drives. Its name keys its section of track.yml and
# prefixes the tools specific to it, so an agent asks for it first and uses the
# matching namespace. Only the computer-vision template is driven today.
AUTOPILOT = CV_CONTROL

# Tools that only make sense for this autopilot carry its name, so a second
# autopilot can add its own get_track_config without colliding. The separator is
# a dash because no tool name otherwise contains one: a dash means "prefixed",
# and a name without one -- start, stop, emergency_stop, measure_ground_point,
# get_autopilot -- applies to any autopilot. A dot would say the same, but the
# Claude API allows only letters, digits, _ and - in a tool name.
CV_TOOL_PREFIX = f"{AUTOPILOT}-"

# The config settings that explain what the CV autopilot does on the track:
# what colour it looks for and where, how it steers, and how fast it goes.
# Hardware calibration (PWM, pins, joystick) is left out -- it explains nothing
# an agent can act on.
CV_AUTOPILOT_SETTINGS = (
    # line colour, HSV
    "COLOR_THRESHOLD_LOW",
    "COLOR_THRESHOLD_HIGH",
    "CONFIDENCE_THRESHOLD",
    # where it looks
    "SCAN_Y",
    "SCAN_HEIGHT",
    "IMAGE_W",
    "IMAGE_H",
    # steering
    "TARGET_PIXEL",
    "TARGET_THRESHOLD",
    "PID_P",
    "PID_I",
    "PID_D",
    "LOST_LINE_STEERING_DECAY",
    # speed
    "THROTTLE_MIN",
    "THROTTLE_MAX",
    "THROTTLE_INITIAL",
    "THROTTLE_STEP",
    # loop and frame
    "DRIVE_LOOP_HZ",
    "OVERLAY_IMAGE",
    "CV_PIXELS_PER_INCH",
    "MCP_COMMAND_TIMEOUT_S",
)

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

# The car config is populated by exec'ing the car's config.py, so its attributes
# do not exist statically.
CarConfig = Any

DEFAULT_MCP_PORT = 8891
DEFAULT_COMMAND_TIMEOUT_S = 2.0

MCP_INSTALL_HINT = (
    "The MCP server needs the `mcp` package, which is not installed.\n"
    "It is an optional extra, so none of the platform extras pull it in:\n"
    "\n"
    '    uv pip install -e ".[pi,dev,mcp]"     # on the car, from a clone\n'
    '    uv pip install "donkeycar[pi,mcp]"     # on the car, from PyPI\n'
    "\n"
    "Swap `pi` for `pc` or `macos` off the car."
)


class MCPNotInstalledError(ImportError):
    """The `mcp` extra is missing. The message says how to install it."""


class ModeLatchingController(Protocol):
    """
    A user controller whose drive mode can be latched.

    The web controller and the joystick controllers both work this way; the
    bridge only ever sets the latch, never `user/mode` itself.
    """

    mode_latch: str | None


class Lifecycle(Protocol):
    """
    What `start` and `stop` act on.

    In part mode this is the bridge itself and start/stop mean arm/disarm. The
    supervisor supplies a richer implementation that really does build and tear
    down the vehicle.
    """

    def start(self) -> str: ...

    def stop(self) -> str: ...

    def is_running(self) -> bool: ...


@dataclass(frozen=True)
class AgentCommand:
    """What the agent has most recently asked for."""

    throttle: float = 0.0
    lane_offset_px: int = 0
    armed: bool = False
    # Escape hatch: bypass the ceiling and command throttle directly. Not
    # reachable from the tool surface, and deliberately so.
    absolute: bool = False


@dataclass
class VehicleState:
    """A coherent snapshot of the car, taken under the lock."""

    loop_count: int = 0
    timestamp: float = 0.0
    # Monotonic stamp of when the vehicle loop last wrote this. Used to tell a
    # live snapshot from one frozen by a stopped loop; the wall clock above can
    # jump and cannot be used for that.
    monotonic: float = 0.0
    steering: float | None = None
    throttle: float | None = None
    cv_throttle: float | None = None
    applied_throttle: float | None = None
    lane_offset_px: int = 0
    user_mode: str | None = None
    armed: bool = False
    # From the CV controller: how strongly it can see the line, and whether that
    # clears its threshold. Without these an agent cannot distinguish a car
    # holding a hard turn because the road turns from one that has lost the line.
    line_confidence: float | None = None
    line_detected: bool | None = None
    watchdog_tripped: bool = False
    frame: np.ndarray | None = field(default=None, repr=False)


def resolve_throttle(command: AgentCommand, cv_throttle: float | None) -> float:
    """
    Combine the agent's throttle with the CV controller's.

    Forward motion is capped at whatever the controller currently thinks is
    safe, so the agent can slow and stop the car but never push it through a
    corner faster than the controller would go. Zero is a hard stop, and
    reverse passes through because the controller has no opinion about it.
    """
    if not command.armed:
        return 0.0
    if command.throttle == 0.0:
        return 0.0
    if command.absolute:
        return command.throttle
    if command.throttle < 0.0:
        return command.throttle
    if cv_throttle is None:
        # The controller has not produced a throttle yet, so there is nothing to
        # cap against. Refusing to move is the safe reading.
        return 0.0
    return min(command.throttle, cv_throttle)


def _resolve_track_file(track_file: str, car_dir: str | None) -> str:
    """
    Where a --track file is. A relative path is taken from the car directory,
    so `donkey mcp --car ~/mycar --track office.yml` means ~/mycar/office.yml.
    A file asked for by name that is not there is an error: falling back to
    the default track would be driving a track other than the one you chose.
    """
    path = os.path.expanduser(track_file)
    if not os.path.isabs(path):
        path = os.path.join(os.path.expanduser(car_dir) if car_dir else os.getcwd(), path)
    if not os.path.isfile(path):
        raise TrackConfigError(f"Track file {path} does not exist (from --track {track_file}).")
    return path


class MCPBridge:
    """
    Donkeycar part that carries agent intent into the vehicle loop and vehicle
    state back out, and serves both over MCP.

    Inputs:  cam/image_array, cv/image_array, pilot/steering, pilot/throttle,
             user/mode
    Outputs: pilot/throttle (capped), mcp/lane_offset_px, mcp/armed
    """

    def __init__(
        self,
        cfg: CarConfig,
        lifecycle: Lifecycle | None = None,
        host: str | None = None,
        port: int | None = None,
        command_timeout_s: float | None = None,
        serve: bool = True,
        track: TrackConfig | None = None,
        car_dir: str | None = None,
        track_file: str | None = None,
    ) -> None:
        self.cfg = cfg
        # From the config, like the port. A fixed default here meant
        # `drive --mcp` always bound 127.0.0.1 whatever MCP_SERVER_HOST said.
        self.host = host if host is not None else getattr(cfg, "MCP_SERVER_HOST", "127.0.0.1")
        self.port = port if port is not None else getattr(cfg, "MCP_SERVER_PORT", DEFAULT_MCP_PORT)
        self.command_timeout_s = (
            command_timeout_s
            if command_timeout_s is not None
            else getattr(cfg, "MCP_COMMAND_TIMEOUT_S", DEFAULT_COMMAND_TIMEOUT_S)
        )
        # When False the part still exchanges state but no server is started.
        # Tests use this; so does anyone embedding the bridge.
        self.serve = serve

        self._lock = threading.Lock()
        self._command = AgentCommand()
        self._state = VehicleState()
        self._last_command_at: float = 0.0
        self._running = True
        self._server: MCPServer | None = None

        # In part mode the bridge is its own lifecycle: start/stop arm/disarm.
        self.lifecycle: Lifecycle = lifecycle if lifecycle is not None else _BridgeArming(self)

        self.car_dir = car_dir
        # Held here rather than in cfg: `donkey mcp` re-reads the config on
        # every start, which would quietly drop a --track given at launch.
        self.track_file = track_file
        self.track = track if track is not None else self._load_track(car_dir)
        # The user controller, when there is one. Needed to put the car into
        # autopilot mode: the CV controller only runs when run_pilot is set,
        # and that comes from user/mode.
        self._controller: object = None
        self.calibration_data: Calibration | None = load_calibration(car_dir, cfg)
        # Optional: only the object-distance tools need it, and they say so
        # when it is missing rather than failing.
        self.intrinsics: CameraIntrinsics | None = load_intrinsics(car_dir, cfg)

    # ------------------------------------------------------------------
    # vehicle loop side
    # ------------------------------------------------------------------

    def run_threaded(
        self,
        cam_img: np.ndarray | None = None,
        cv_img: np.ndarray | None = None,
        pilot_steering: float | None = None,
        pilot_throttle: float | None = None,
        user_mode: str | None = None,
        line_confidence: float | None = None,
        line_detected: bool | None = None,
    ) -> tuple[float, int, bool]:
        """
        Called once per vehicle loop. Publishes a state snapshot for the agent
        and returns the throttle, lane offset and armed flag the rest of the
        pipeline should use.
        """
        now = time.monotonic()

        with self._lock:
            command = self._command
            tripped = False

            # Agent silence must fail safe. Without this the car keeps whatever
            # throttle it was last given while nobody is watching.
            if (
                command.armed
                and command.throttle != 0.0
                and self._last_command_at
                and (now - self._last_command_at) > self.command_timeout_s
            ):
                tripped = True
                command = replace(command, throttle=0.0)
                self._command = command
                logger.warning(
                    "MCP watchdog: no agent command for %.1fs, throttle zeroed",
                    now - self._last_command_at,
                )

            applied = resolve_throttle(command, pilot_throttle)

            self._state = VehicleState(
                loop_count=self._state.loop_count + 1,
                timestamp=time.time(),
                monotonic=now,
                steering=pilot_steering,
                throttle=pilot_throttle,
                cv_throttle=pilot_throttle,
                applied_throttle=applied,
                lane_offset_px=command.lane_offset_px,
                user_mode=user_mode,
                armed=command.armed,
                line_confidence=line_confidence,
                line_detected=line_detected,
                watchdog_tripped=tripped,
                # The pilot image carries the CV overlay when one is enabled.
                frame=cv_img if cv_img is not None else cam_img,
            )

        return applied, command.lane_offset_px, command.armed

    def run(
        self,
        cam_img: np.ndarray | None = None,
        cv_img: np.ndarray | None = None,
        pilot_steering: float | None = None,
        pilot_throttle: float | None = None,
        user_mode: str | None = None,
        line_confidence: float | None = None,
        line_detected: bool | None = None,
    ) -> tuple[float, int, bool]:
        return self.run_threaded(
            cam_img, cv_img, pilot_steering, pilot_throttle, user_mode, line_confidence, line_detected
        )

    def update(self) -> None:
        """Thread body: serve MCP until shutdown."""
        if not self.serve:
            return
        try:
            server = self.build_server()
        except MCPNotInstalledError as exc:
            # The vehicle keeps driving; only the agent interface is missing.
            logger.error("%s", exc)
            return
        self.serve_http(server, self.host, self.port)

    def shutdown(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # agent side
    # ------------------------------------------------------------------

    def snapshot(self) -> VehicleState:
        """A coherent copy of the latest state."""
        with self._lock:
            return replace(self._state)

    def command(self) -> AgentCommand:
        with self._lock:
            return self._command

    def state_is_live(self) -> bool:
        """
        Is the vehicle loop still writing state?

        Measured directly rather than inferred from the lifecycle: in part mode
        the loop keeps turning while the bridge is disarmed, so "armed" says
        nothing about whether the camera is still producing frames.
        """
        with self._lock:
            written_at = self._state.monotonic
        if not written_at:
            return False
        hz = float(getattr(self.cfg, "DRIVE_LOOP_HZ", 20) or 20)
        # A few loop periods of slack, with a floor for very slow loops.
        return (time.monotonic() - written_at) < max(1.0, 5.0 / hz)

    def reload_config(self, cfg: CarConfig) -> None:
        """
        Adopt a freshly read config.

        The bridge outlives the vehicle, so a rebuilt vehicle on new settings
        would otherwise leave the bridge answering from the old ones -- lane
        offsets, pixels-per-inch and the track all come from here. Track and
        both calibrations are re-read too, so a malformed track.yml or
        calibration file surfaces now rather than at the next tool call.
        """
        track = self._load_track(self.car_dir) if cfg is not None else self.track
        calibration = load_calibration(self.car_dir, cfg)
        intrinsics = load_intrinsics(self.car_dir, cfg)
        # Only commit once all three have parsed: a half-applied config is
        # worse than the old one.
        self.cfg = cfg
        self.track = track
        self.calibration_data = calibration
        self.intrinsics = intrinsics
        self.command_timeout_s = getattr(cfg, "MCP_COMMAND_TIMEOUT_S", DEFAULT_COMMAND_TIMEOUT_S)
        logger.info("Bridge adopted reloaded config")

    def attach_controller(self, controller: object) -> None:
        """
        Remember the user controller so drive mode can be switched.

        The bridge cannot write `user/mode` directly: the web controller
        re-outputs it every loop and would clobber it. Latching is the same
        mechanism its own buttons use.
        """
        self._controller = controller

    def _request_mode(self, mode: str) -> None:
        controller = self._controller
        if controller is None:
            return
        if hasattr(controller, "mode_latch"):
            controller.mode_latch = mode
            logger.info("Requested drive mode %r", mode)
        else:
            logger.warning(
                "The configured controller cannot switch drive mode; set WEB_INIT_MODE = 'local_pilot' "
                "so the autopilot runs."
            )

    def arm(self) -> None:
        with self._lock:
            self._command = replace(self._command, armed=True)
            self._last_command_at = time.monotonic()
        # Without autopilot mode the CV controller never runs, pilot/throttle
        # stays None, and the throttle ceiling resolves to zero forever.
        self._request_mode("local_pilot")

    def disarm(self) -> None:
        with self._lock:
            self._command = replace(self._command, armed=False, throttle=0.0)
            self._last_command_at = time.monotonic()
        self._request_mode("user")

    def is_armed(self) -> bool:
        with self._lock:
            return self._command.armed

    def set_control(
        self,
        throttle: float | None = None,
        lane_offset_px: int | None = None,
    ) -> AgentCommand:
        """Apply an agent command and refresh the watchdog."""
        with self._lock:
            command = self._command
            if throttle is not None:
                command = replace(command, throttle=_clamp(float(throttle), -1.0, 1.0))
            if lane_offset_px is not None:
                command = replace(command, lane_offset_px=int(lane_offset_px))
            self._command = command
            self._last_command_at = time.monotonic()
            return command

    def emergency_stop(self) -> AgentCommand:
        """Zero throttle immediately without touching the lifecycle."""
        with self._lock:
            self._command = replace(self._command, throttle=0.0)
            self._last_command_at = time.monotonic()
            logger.warning("MCP emergency stop")
            return self._command

    def frame_jpeg(self) -> bytes | None:
        """
        Encode the latest frame. Done per request rather than per loop: at
        20 Hz most frames are never asked for.

        Returns None once the loop has stopped. A stale frame is the most
        dangerous stale field there is: an agent decides when to brake from it.
        """
        if not self.state_is_live():
            return None
        state = self.snapshot()
        if state.frame is None:
            return None
        return bytes(arr_to_binary(state.frame))

    # ------------------------------------------------------------------
    # MCP surface
    # ------------------------------------------------------------------

    def build_server(self) -> MCPServer:
        """
        Construct the MCP server and register the tools.

        The surface lives in `mcp_tools`, which imports the `mcp` package at
        module scope. Importing it lazily here is what keeps this module usable
        on a car that never installed the extra -- and it also lets the tool
        annotations resolve, which they cannot do from inside a function body.
        """
        try:
            from donkeycar.parts.mcp_tools import build_server
        except ImportError as exc:
            # Only translate a missing `mcp`; anything else wrong inside
            # mcp_tools should surface as itself rather than as bad advice.
            if exc.name and exc.name.split(".")[0] != "mcp":
                raise
            raise MCPNotInstalledError(MCP_INSTALL_HINT) from exc

        server = build_server(self)
        self._server = server
        return server

    def serve_http(self, server: MCPServer, host: str, port: int) -> None:
        """
        Serve `server` over HTTP until stopped, behind the host check.

        The one place either run mode starts the server, so protection cannot
        differ between them. Settings are read from the config the process
        started with: the socket is bound once.
        """
        from donkeycar.parts.mcp_http import serve_http

        serve_http(
            server,
            host,
            port,
            extra_allowed_hosts=getattr(self.cfg, "MCP_SERVER_ALLOWED_HOSTS", None) or (),
            token=getattr(self.cfg, "MCP_SERVER_TOKEN", None) or None,
        )

    # ------------------------------------------------------------------
    # track and calibration
    # ------------------------------------------------------------------

    def _load_track(self, car_dir: str | None) -> TrackConfig:
        """
        Prefer the --track file if one was given, else a track.yml beside the
        car's config, else a default. A malformed file is an error, not a
        silent fallback: driving a track you have mis-described is worse than
        not starting.

        The track is described only by a file. The TRACK_* constants older
        cars' config.py copies carry are never looked at.
        """
        car_dir = car_dir or getattr(self.cfg, "CAR_PATH", None)
        path = _resolve_track_file(self.track_file, car_dir) if self.track_file else find_track_file(car_dir)
        if path:
            track = load_track(path)
            logger.info("Loaded track description from %s", path)
            return track

        expected = os.path.join(os.path.expanduser(car_dir), TRACK_FILENAME) if car_dir else TRACK_FILENAME
        logger.warning(
            "No track file at %s; the agent gets the default track, with generic left, center and right lanes. "
            "Describe the track in %s, or choose a file with --track.",
            expected,
            TRACK_FILENAME,
        )
        return default_track()

    def track_config(self) -> dict[str, Any]:
        return self.track.to_dict()

    def autopilot(self) -> dict[str, Any]:
        return {
            "autopilot": AUTOPILOT,
            "tool_prefix": CV_TOOL_PREFIX,
            "note": (
                f"Tools specific to this autopilot start with '{CV_TOOL_PREFIX}'. Read the '{AUTOPILOT}' "
                f"section of {CV_TOOL_PREFIX}get_track_config, and {CV_TOOL_PREFIX}get_autopilot_config "
                "for the settings this autopilot is running with."
            ),
        }

    def autopilot_config(self) -> dict[str, Any]:
        """
        The settings the autopilot is running with, from the current config.

        `start` reloads the config, so this is always what the running car uses
        rather than what the process launched with. A setting the config does
        not define is reported as None, so "unset" cannot be mistaken for "not
        reported".
        """
        return {
            "autopilot": AUTOPILOT,
            "source": "config.py + myconfig.py",
            "settings": {name: getattr(self.cfg, name, None) for name in CV_AUTOPILOT_SETTINGS},
        }

    def lane_offset_px_for(self, lane: str) -> int:
        # TrackConfigError is a ValueError, so the tool layer turns it into a
        # ToolError carrying the list of lanes that do exist.
        return self.inches_to_px(self.track.cv_control.offset_inches(lane))

    def pixels_per_inch(self) -> float | None:
        return self.calibration_data.pixels_per_inch if self.calibration_data else None

    def inches_to_px(self, inches: float) -> int:
        """
        A lane offset in ground inches, as the pixel offset the controller wants.

        These are two different frames and they run in opposite directions.
        `inches` says where the *car* should sit: positive is right of the
        centreline, which is how a person describes a lane and how track.yml
        records one. `lane_offset_px` says where the *tape* should appear in the
        camera: positive moves the steering target right in the image.

        Asking the car to sit right of the line is the same as asking the line
        to appear left of centre, so the sign flips here. Without the flip the
        lane named "right" drives the car down the left of the track -- steering
        beautifully, holding its offset precisely, on the wrong side.
        """
        # Zero inches is zero pixels whatever the scale, so holding the centre
        # lane must not require a calibration. Only a real offset does.
        if inches == 0:
            return 0
        ppi = self.pixels_per_inch()
        if not ppi:
            raise ValueError(
                "No pixels-per-inch calibration, so a lane offset cannot be converted. "
                "Set CV_PIXELS_PER_INCH or run `donkey calibrate-cv`."
            )
        return -round(inches * ppi)

    def px_to_inches(self, px: int) -> float | None:
        """Back to ground inches, positive right of the centreline."""
        ppi = self.pixels_per_inch()
        if not ppi:
            return None
        return -px / ppi

    def calibration(self) -> dict[str, Any]:
        if self.calibration_data is None:
            return {
                "calibrated": False,
                "reason": (
                    "No calibration. Run `donkey calibrate-cv` with a checkerboard, or set "
                    "CV_PIXELS_PER_INCH by hand for lane offsets only."
                ),
                "camera": self.camera_calibration(),
            }
        stale = self.calibration_data.stale_reasons(self.cfg)
        payload = self.calibration_data.to_dict()
        payload["calibrated"] = True
        payload["stale"] = bool(stale)
        payload["stale_reasons"] = stale
        payload["can_measure_points"] = self.calibration_data.homography is not None
        payload["camera"] = self.camera_calibration()
        return payload

    def camera_calibration(self) -> dict[str, Any]:
        """
        The optional camera calibration: focal length, principal point and lens
        distortion. A separate calibration from the ground plane's, with its
        own file and its own staleness.
        """
        if self.intrinsics is None:
            return {
                "calibrated": False,
                "reason": (
                    "No camera calibration, so objects cannot be measured by their size. "
                    "Run `donkey calibrate-cv --intrinsics` with a checkerboard held up to the camera."
                ),
            }
        stale = self.intrinsics.stale_reasons(self.cfg)
        payload = self.intrinsics.to_dict()
        payload["calibrated"] = True
        payload["stale"] = bool(stale)
        payload["stale_reasons"] = stale
        return payload

    def measure_ground_point(self, u: float, v: float) -> dict[str, Any]:
        """
        Where on the ground is the thing at this pixel?

        This is the agent's only source of depth. Braking for a stop sign means
        knowing how far away it is, and the alternative -- inferring distance
        from apparent size over a network round trip -- is a guess.
        """
        if self.calibration_data is None:
            raise ValueError(
                "No calibration, so points cannot be measured. Run `donkey calibrate-cv` with a checkerboard."
            )
        state = self.snapshot()
        if state.frame is not None:
            height, width = state.frame.shape[:2]
            if not (0 <= u < width and 0 <= v < height):
                raise ValueError(f"Pixel ({u}, {v}) is outside the {width}x{height} camera frame")

        lateral, forward = self.calibration_data.image_to_ground(u, v)
        return {
            "lateral_inches": lateral,
            "forward_inches": forward,
            "note": (
                "Positive lateral is right of centre, positive forward is away from the car. "
                "Accuracy degrades toward the frame edges because a single homography "
                "assumes no lens distortion."
            ),
        }

    def _intrinsics_problem(self) -> str | None:
        """Why the camera calibration cannot be used, or None when it can."""
        if self.intrinsics is None:
            return (
                "No camera calibration, so distance from an object's size is unknown. Run "
                "`donkey calibrate-cv --intrinsics`, or use measure_ground_point at the object's base."
            )
        stale = self.intrinsics.stale_reasons(self.cfg)
        if stale:
            return (
                f"The camera calibration no longer matches the config ({'; '.join(stale)}), so distance "
                "from an object's size is unknown. Re-run `donkey calibrate-cv --intrinsics`."
            )
        return None

    def measure_object_distance(
        self,
        box: object,
        width_inches: float | None = None,
        height_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        How far away an object of known size is, from its bounding box.

        A malformed request is refused whatever the calibration; a well-formed
        one without a usable camera calibration is answered "unknown", which an
        agent can act on by falling back to measure_ground_point.
        """
        parsed = parse_box(box)
        check_sizes(width_inches, height_inches)
        problem = self._intrinsics_problem()
        if problem is not None or self.intrinsics is None:
            return unknown(problem or "")
        return measure_object(parsed, self.intrinsics, width_inches, height_inches, ground=self.calibration_data)

    def estimate_speed_from_object(
        self,
        observations: object,
        width_inches: float | None = None,
        height_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        How fast the car is closing on a stationary object of known size, from
        its box in two or more frames. Refused and "unknown" as
        measure_object_distance is.
        """
        parsed = parse_observations(observations)
        check_sizes(width_inches, height_inches)
        problem = self._intrinsics_problem()
        if problem is not None or self.intrinsics is None:
            return unknown_speed(problem or "")
        return estimate_speed(parsed, self.intrinsics, width_inches, height_inches)


class _BridgeArming:
    """Part-mode lifecycle: start/stop arm and disarm the bridge."""

    def __init__(self, bridge: MCPBridge) -> None:
        self._bridge = bridge

    def start(self) -> str:
        self._bridge.arm()
        return "armed"

    def stop(self) -> str:
        self._bridge.disarm()
        return "disarmed"

    def is_running(self) -> bool:
        return self._bridge.is_armed()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
