"""
The MCP tool surface for the donkeycar bridge.

Kept apart from `mcp_server` for two reasons. It imports the `mcp` package at
module scope, so a car that never installed the optional extra can still import
and run the part; and tool return annotations are resolved against *module*
globals by the SDK, which they cannot be if the types are imported inside a
function body.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ImageContent, TextContent

import donkeycar
from donkeycar.parts.mcp_server import CV_TOOL_PREFIX

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from donkeycar.parts.mcp_server import MCPBridge

INSTRUCTIONS = (
    "Drive a donkeycar that is following a taped centreline with a computer-vision autopilot. "
    "The autopilot steers; you set intent. Call get_autopilot first: it names the autopilot, and "
    "tools specific to that autopilot start with its name and a dash (cv_control-...); a tool "
    "with no dash in its name applies to any autopilot. Call "
    "cv_control-get_track_config once to learn the track, then poll cv_control-get_vehicle_state "
    "and call cv_control-set_control to change throttle or lane. Every track has the lanes left, "
    "center (on the centreline) and right. The track's widths and lap length are nominal: the "
    "width and the centreline's position vary along the course, so measure from the camera frame "
    "with measure_ground_point where it matters. A tape_color in the track is only a label; "
    "cv_control-get_autopilot_config reports the colour window and other settings the autopilot "
    "actually runs with. Throttle is a ceiling on the autopilot's own throttle, so a high value "
    "does not make the car corner faster; 0 stops it. Commands expire, so keep calling "
    "cv_control-set_control while you want the car to move. Traffic features such as stop signs "
    "and addresses are not in the track description -- look for them in the camera frame. For an "
    "object of known size, such as a stop sign, measure_object_distance gives its range from a tight "
    "bounding box; when it answers known: false, use measure_ground_point at the object's base instead. "
    "estimate_speed_from_object gives the car's closing speed on a stationary object from two or more "
    "frames: pass the timestamp cv_control-get_vehicle_state returned with each frame, and use frames "
    "at least half a second apart."
)


@contextmanager
def _agent_facing_errors() -> Iterator[None]:
    """
    Turn the bridge's ValueErrors into ToolErrors.

    Only a ToolError's message reaches the client; every other exception is
    reported as a bare "Error executing tool <name>". An agent that asks for an
    unknown lane needs to be told which lanes exist, not that something failed.
    """
    try:
        yield
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def build_server(bridge: MCPBridge) -> MCPServer:
    """Register the tool surface against a bridge and return the server."""
    # Without an explicit version clients see an empty string in server_info.
    server = MCPServer(name="donkeycar", version=donkeycar.__version__, instructions=INSTRUCTIONS)

    @server.tool()
    def get_autopilot() -> dict[str, Any]:
        """
        Name the autopilot driving the car. Call this first. Tools specific to that autopilot start
        with its name -- `tool_prefix`, e.g. cv_control-get_track_config -- and the same name is the
        section of that tool's result that describes the track for it.
        """
        return bridge.autopilot()

    @server.tool(name=CV_TOOL_PREFIX + "get_autopilot_config")
    def get_autopilot_config() -> dict[str, Any]:
        """
        The settings the autopilot is running with, read from the car's config.py and myconfig.py:
        the HSV colour window it matches the line with, where in the image it looks, how it steers,
        and its throttle range. Read-only. `start` reloads the config, so call this again after a
        restart. A setting the config does not define is null.
        """
        return bridge.autopilot_config()

    @server.tool(name=CV_TOOL_PREFIX + "get_track_config")
    def get_track_config() -> dict[str, Any]:
        """
        Describe the track: its name, and a section per autopilot (see get_autopilot). The
        cv_control section gives whether it loops, its lap length, the centreline (tape_color,
        width, dashed), the side-lines, and the named lanes. Every track has the lanes left,
        center and right. A tape_color is only a label.

        All distances are NOMINAL -- measured once, as guidance. The track's width and the
        centreline's position vary along the course; for the real values at a given spot, find
        the side-lines in the camera frame and call measure_ground_point on them.
        """
        return bridge.track_config()

    # The return annotation matters. The SDK decides whether to render a result
    # as content blocks or as structured JSON by inspecting it, and a loose
    # annotation sends the Image down the structured path, where it fails to
    # serialise at request time rather than at import time.
    @server.tool(name=CV_TOOL_PREFIX + "get_vehicle_state")
    def get_vehicle_state() -> list[TextContent | ImageContent]:
        """
        Return the latest camera frame plus the current throttle, steering, lane
        offset and drive mode. `loop_count` increases every vehicle loop, so
        compare it across calls to tell a fresh frame from a stale one.
        """
        state = bridge.snapshot()
        command = bridge.command()
        live = bridge.state_is_live()

        # What the agent has asked for is always current. What the vehicle
        # reported is only current while the loop is turning -- after a stop the
        # snapshot freezes, and reporting it verbatim told the agent the car was
        # still armed and steering.
        payload: dict[str, Any] = {
            "running": bridge.lifecycle.is_running(),
            "live": live,
            "armed": command.armed,
            "commanded_throttle": command.throttle,
            "lane_offset_px": command.lane_offset_px,
            "lane_offset_inches": bridge.px_to_inches(command.lane_offset_px),
            "loop_count": state.loop_count,
            "timestamp": state.timestamp if live else None,
            "steering": state.steering if live else None,
            "throttle": state.applied_throttle if live else None,
            "autopilot_throttle": state.cv_throttle if live else None,
            "user_mode": state.user_mode if live else None,
            "watchdog_tripped": state.watchdog_tripped if live else False,
            # How well the autopilot can see the line. A hard steering value
            # means something very different depending on this: following a
            # bend, or driving blind at the lock it last held.
            "line_detected": state.line_detected if live else None,
            "line_confidence": state.line_confidence if live else None,
        }
        if live and state.watchdog_tripped:
            payload["watchdog_note"] = (
                "The throttle was zeroed because no command arrived for "
                f"{bridge.command_timeout_s:.0f}s. Reading state does not reset the timer -- "
                "call cv_control-set_control again to resume, and keep calling it while driving."
            )
        if live and state.line_detected is False:
            payload["warning"] = (
                "The autopilot cannot see the line. Steering is decaying toward centre, "
                "but the car is driving blind -- consider cv_control-set_control(throttle=0)."
            )
        if not live:
            payload["note"] = (
                "The vehicle loop is not running, so there is no current camera frame, "
                "steering or throttle. Call start."
            )
        blocks: list[TextContent | ImageContent] = [
            TextContent(type="text", text=json.dumps(payload, indent=2, default=str))
        ]
        jpeg = bridge.frame_jpeg()
        if jpeg is not None:
            blocks.append(Image(data=jpeg, format="jpeg").to_image_content())
        return blocks

    @server.tool(name=CV_TOOL_PREFIX + "set_control")
    def set_control(
        throttle: float | None = None,
        lane: str | None = None,
        lane_offset_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        Set the throttle and/or the lane.

        throttle is -1..1 and acts as a ceiling on the autopilot's own throttle;
        0 stops the car. Give either `lane` (a name from cv_control-get_track_config) or
        `lane_offset_inches` for finer control.

        KEEP CALLING THIS WHILE YOU WANT THE CAR TO MOVE. A watchdog zeroes the
        throttle if no command arrives for MCP_COMMAND_TIMEOUT_S (2 seconds by
        default), so that a car whose agent has crashed or lost its connection
        stops rather than driving on unattended. Reading state does not count --
        only a command resets the timer. Re-send this at least every second
        during a drive; sending the same values again is fine and is the normal
        way to hold a speed. If the car stops for no apparent reason, check
        `watchdog_tripped` in cv_control-get_vehicle_state.
        """
        if lane is not None and lane_offset_inches is not None:
            raise ToolError("Give either lane or lane_offset_inches, not both.")

        offset_px: int | None = None
        with _agent_facing_errors():
            if lane is not None:
                offset_px = bridge.lane_offset_px_for(lane)
            elif lane_offset_inches is not None:
                offset_px = bridge.inches_to_px(lane_offset_inches)

        command = bridge.set_control(throttle=throttle, lane_offset_px=offset_px)
        return {
            "throttle": command.throttle,
            "lane_offset_px": command.lane_offset_px,
            "lane_offset_inches": bridge.px_to_inches(command.lane_offset_px),
            "armed": command.armed,
            "note": "throttle is a ceiling on the autopilot's throttle, not a direct command",
        }

    @server.tool()
    def start() -> dict[str, Any]:
        """
        Start driving. The car does not move until this is called.

        The car's config is re-read first, so edits to config.py or myconfig.py
        take effect without restarting the server.
        """
        with _agent_facing_errors():
            result = bridge.lifecycle.start()
        return {"result": result, "running": bridge.lifecycle.is_running()}

    @server.tool()
    def stop() -> dict[str, Any]:
        """Stop driving. Throttle is zeroed first."""
        with _agent_facing_errors():
            result = bridge.lifecycle.stop()
        return {"result": result, "running": bridge.lifecycle.is_running()}

    @server.tool()
    def emergency_stop() -> dict[str, Any]:
        """Zero the throttle right now, without stopping the vehicle loop."""
        command = bridge.emergency_stop()
        return {"throttle": command.throttle, "armed": command.armed}

    @server.tool()
    def measure_ground_point(pixel_x: float, pixel_y: float) -> dict[str, Any]:
        """
        Convert a point in the camera image to a position on the ground, in
        inches. Use it to work out how far ahead something is -- a stop sign, an
        obstacle -- so you can slow down in time rather than guessing from how
        large it looks.
        """
        with _agent_facing_errors():
            return bridge.measure_ground_point(pixel_x, pixel_y)

    @server.tool()
    def measure_object_distance(
        box: dict[str, float],
        width_inches: float | None = None,
        height_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        How far away an object of known size is: a stop sign, a cone, a card.

        `box` is the object's bounding box in pixels of the camera frame, as
        {x_min, y_min, x_max, y_max}; draw it tight. Give the object's real
        `width_inches`, `height_inches`, or both -- both is better, because
        their `size_disagreement` shows when the box is poor.

        Returns `range_inches`, the straight-line distance from the camera to
        the object, with `range_uncertainty_inches`. With a floor calibration
        too, `forward_inches` and `lateral_inches` say where on the floor the
        object stands. Needs the camera calibration; without it `known` is
        false and `reason` says what to do -- measure_ground_point at the
        object's base is the fallback.
        """
        with _agent_facing_errors():
            return bridge.measure_object_distance(box, width_inches, height_inches)

    @server.tool()
    def estimate_speed_from_object(
        observations: list[dict[str, Any]],
        width_inches: float | None = None,
        height_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        How fast the car is closing on a stationary object of known size.

        `observations` is two or more frames, each {timestamp, box}: the
        `timestamp` cv_control-get_vehicle_state returned with that frame, and
        the object's bounding box in it, as for measure_object_distance. Give
        the object's real `width_inches`, `height_inches`, or both.

        Returns `closing_speed_inches_per_s` (positive means getting closer)
        with its uncertainty, the time spanned, and each frame's range. Use
        frames at least half a second apart; a `warning` says when they are too
        close, or the boxes too rough, to tell. Needs the camera calibration;
        without it `known` is false and `reason` says what to do.
        """
        with _agent_facing_errors():
            return bridge.estimate_speed_from_object(observations, width_inches, height_inches)

    @server.tool(name=CV_TOOL_PREFIX + "get_calibration")
    def get_calibration() -> dict[str, Any]:
        """
        Pixels-per-inch and the ground homography, with the settings they were
        captured under so you can tell whether they are still valid.
        `loaded_from` says where the values came from: the calibration file's
        path, or the CV_PIXELS_PER_INCH config setting when there is no file.
        The `camera` section is the separate, optional camera calibration
        (focal length and lens distortion) that measuring an object by its
        size needs; `camera.calibrated` is false when it has not been captured.
        """
        return bridge.calibration()

    return server
