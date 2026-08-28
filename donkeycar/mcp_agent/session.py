"""
How the agent talks to the car.

`CarSession` is the surface the policies use. Two implementations: one that
calls an MCP server over the socket (what a real agent uses) and one that calls
a bridge directly (what the tests use, so the driving logic can be exercised
without standing up a server).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from mcp.client.client import Client
    from mcp.types import CallToolResult

    from donkeycar.parts.mcp_server import MCPBridge


class CarSession(Protocol):
    """The tools a policy needs."""

    def get_track_config(self) -> dict[str, Any]: ...

    def get_vehicle_state(self) -> tuple[dict[str, Any], bytes | None]: ...

    def set_control(
        self,
        throttle: float | None = None,
        lane: str | None = None,
        lane_offset_inches: float | None = None,
    ) -> dict[str, Any]: ...

    def measure_ground_point(self, pixel_x: float, pixel_y: float) -> dict[str, Any]: ...

    def start(self) -> dict[str, Any]: ...

    def stop(self) -> dict[str, Any]: ...


class BridgeSession:
    """
    Calls an MCPBridge directly.

    The same calls a real agent makes over MCP, minus the transport. Used by the
    tests so the activities run against a real vehicle loop.
    """

    def __init__(self, bridge: MCPBridge) -> None:
        self._bridge = bridge

    def get_track_config(self) -> dict[str, Any]:
        return self._bridge.track_config()

    def get_vehicle_state(self) -> tuple[dict[str, Any], bytes | None]:
        state = self._bridge.snapshot()
        payload = {
            "loop_count": state.loop_count,
            "throttle": state.applied_throttle,
            "autopilot_throttle": state.cv_throttle,
            "steering": state.steering,
            "lane_offset_px": state.lane_offset_px,
            "armed": state.armed,
            "watchdog_tripped": state.watchdog_tripped,
        }
        return payload, self._bridge.frame_jpeg()

    def set_control(
        self,
        throttle: float | None = None,
        lane: str | None = None,
        lane_offset_inches: float | None = None,
    ) -> dict[str, Any]:
        offset_px = None
        if lane is not None:
            offset_px = self._bridge.lane_offset_px_for(lane)
        elif lane_offset_inches is not None:
            offset_px = self._bridge.inches_to_px(lane_offset_inches)
        command = self._bridge.set_control(throttle=throttle, lane_offset_px=offset_px)
        return {"throttle": command.throttle, "lane_offset_px": command.lane_offset_px}

    def measure_ground_point(self, pixel_x: float, pixel_y: float) -> dict[str, Any]:
        return self._bridge.measure_ground_point(pixel_x, pixel_y)

    def start(self) -> dict[str, Any]:
        return {"result": self._bridge.lifecycle.start()}

    def stop(self) -> dict[str, Any]:
        return {"result": self._bridge.lifecycle.stop()}


class McpSession:
    """
    Calls a running MCP server.

    Thin on purpose: it exists to show what the tool calls look like from a
    client, not to be a framework.
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def _call(self, tool: str, **arguments: object) -> CallToolResult:
        import anyio

        async def go() -> CallToolResult:
            return await self._client.call_tool(tool, {k: v for k, v in arguments.items() if v is not None})

        return anyio.run(go)

    @staticmethod
    def _payload(result: CallToolResult) -> dict[str, Any]:
        from mcp.types import TextContent

        for block in result.content:
            if isinstance(block, TextContent):
                try:
                    parsed = json.loads(block.text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
        return {}

    @staticmethod
    def _image(result: CallToolResult) -> bytes | None:
        import base64

        from mcp.types import ImageContent

        for block in result.content:
            if isinstance(block, ImageContent):
                return base64.b64decode(block.data)
        return None

    def get_track_config(self) -> dict[str, Any]:
        return self._payload(self._call("get_track_config"))

    def get_vehicle_state(self) -> tuple[dict[str, Any], bytes | None]:
        result = self._call("get_vehicle_state")
        return self._payload(result), self._image(result)

    def set_control(
        self,
        throttle: float | None = None,
        lane: str | None = None,
        lane_offset_inches: float | None = None,
    ) -> dict[str, Any]:
        return self._payload(
            self._call("set_control", throttle=throttle, lane=lane, lane_offset_inches=lane_offset_inches)
        )

    def measure_ground_point(self, pixel_x: float, pixel_y: float) -> dict[str, Any]:
        return self._payload(self._call("measure_ground_point", pixel_x=pixel_x, pixel_y=pixel_y))

    def start(self) -> dict[str, Any]:
        return self._payload(self._call("start"))

    def stop(self) -> dict[str, Any]:
        return self._payload(self._call("stop"))
