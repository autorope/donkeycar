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

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from donkeycar.parts.mcp_server import MCPBridge

INSTRUCTIONS = (
    "Drive a donkeycar that is following a yellow tape line with a computer-vision autopilot. "
    "The autopilot steers; you set intent. Call get_track_config once to learn the track, then "
    "poll get_vehicle_state and call set_control to change throttle or lane. Throttle is a "
    "ceiling on the autopilot's own throttle, so a high value does not make the car corner "
    "faster; 0 stops it. Commands expire, so keep calling set_control while you want the car to "
    "move. Traffic features such as stop signs and addresses are not in the track description -- "
    "look for them in the camera frame."
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
    server = MCPServer(name="donkeycar", instructions=INSTRUCTIONS)

    @server.tool()
    def get_track_config() -> dict[str, Any]:
        """Describe the track: segment geometry, how many segments, whether it loops, and the named lanes."""
        return bridge.track_config()

    # The return annotation matters. The SDK decides whether to render a result
    # as content blocks or as structured JSON by inspecting it, and a loose
    # annotation sends the Image down the structured path, where it fails to
    # serialise at request time rather than at import time.
    @server.tool()
    def get_vehicle_state() -> list[TextContent | ImageContent]:
        """
        Return the latest camera frame plus the current throttle, steering, lane
        offset and drive mode. `loop_count` increases every vehicle loop, so
        compare it across calls to tell a fresh frame from a stale one.
        """
        state = bridge.snapshot()
        payload: dict[str, Any] = {
            "loop_count": state.loop_count,
            "timestamp": state.timestamp,
            "steering": state.steering,
            "throttle": state.applied_throttle,
            "autopilot_throttle": state.cv_throttle,
            "lane_offset_px": state.lane_offset_px,
            "lane_offset_inches": bridge.px_to_inches(state.lane_offset_px),
            "user_mode": state.user_mode,
            "armed": state.armed,
            "watchdog_tripped": state.watchdog_tripped,
            "running": bridge.lifecycle.is_running(),
        }
        blocks: list[TextContent | ImageContent] = [
            TextContent(type="text", text=json.dumps(payload, indent=2, default=str))
        ]
        jpeg = bridge.frame_jpeg()
        if jpeg is not None:
            blocks.append(Image(data=jpeg, format="jpeg").to_image_content())
        return blocks

    @server.tool()
    def set_control(
        throttle: float | None = None,
        lane: str | None = None,
        lane_offset_inches: float | None = None,
    ) -> dict[str, Any]:
        """
        Set the throttle and/or the lane.

        throttle is -1..1 and acts as a ceiling on the autopilot's own throttle;
        0 stops the car. Give either `lane` (a name from get_track_config) or
        `lane_offset_inches` for finer control.
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
        """Start driving. The car does not move until this is called."""
        return {"result": bridge.lifecycle.start(), "running": bridge.lifecycle.is_running()}

    @server.tool()
    def stop() -> dict[str, Any]:
        """Stop driving. Throttle is zeroed first."""
        return {"result": bridge.lifecycle.stop(), "running": bridge.lifecycle.is_running()}

    @server.tool()
    def emergency_stop() -> dict[str, Any]:
        """Zero the throttle right now, without stopping the vehicle loop."""
        command = bridge.emergency_stop()
        return {"throttle": command.throttle, "armed": command.armed}

    @server.tool()
    def get_calibration() -> dict[str, Any]:
        """
        Pixels-per-inch and the ground homography, with the settings they were
        captured under so you can tell whether they are still valid.
        """
        return bridge.calibration()

    return server
