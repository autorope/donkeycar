"""
Tests for the MCP bridge.

These exercise the part and its command semantics directly, with no Vehicle,
no camera and no server: the bridge is constructed with serve=False so that
run_threaded and the agent-side methods can be driven by hand.
"""

import json
import threading
import time
from typing import ClassVar

import numpy as np
import pytest

from donkeycar.parts.mcp_server import (
    AgentCommand,
    MCPBridge,
    resolve_throttle,
)
from donkeycar.parts.track_config import TrackConfigError


class Cfg:
    MCP_SERVER_PORT = 8891
    MCP_COMMAND_TIMEOUT_S = 0.2
    CV_PIXELS_PER_INCH = 4.0
    TRACK_SEGMENT_LENGTH_INCHES = 36.0
    TRACK_CROSS_LENGTH_INCHES = 12.0
    TRACK_SEGMENT_COUNT = 8
    TRACK_CONTINUOUS = True
    TRACK_LANES_INCHES: ClassVar[dict[str, float]] = {"left": -12.0, "center": 0.0, "right": 12.0}


def make_bridge(**kwargs):
    return MCPBridge(Cfg(), serve=False, **kwargs)


def frame(value=120, w=32, h=24):
    return np.full((h, w, 3), value, dtype=np.uint8)


# ----------------------------------------------------------------- throttle


def test_throttle_is_a_ceiling_not_a_command():
    """A high agent throttle must not raise throttle above the autopilot's."""
    cmd = AgentCommand(throttle=1.0, armed=True)
    assert resolve_throttle(cmd, 0.2) == 0.2


def test_throttle_below_the_ceiling_wins():
    cmd = AgentCommand(throttle=0.1, armed=True)
    assert resolve_throttle(cmd, 0.3) == 0.1


def test_zero_throttle_is_a_hard_stop():
    cmd = AgentCommand(throttle=0.0, armed=True)
    assert resolve_throttle(cmd, 0.3) == 0.0


def test_disarmed_never_moves():
    cmd = AgentCommand(throttle=1.0, armed=False)
    assert resolve_throttle(cmd, 0.3) == 0.0


def test_no_autopilot_throttle_means_no_movement():
    """Nothing to cap against, so refuse rather than guess."""
    cmd = AgentCommand(throttle=0.5, armed=True)
    assert resolve_throttle(cmd, None) == 0.0


def test_absolute_mode_bypasses_the_ceiling():
    cmd = AgentCommand(throttle=0.9, armed=True, absolute=True)
    assert resolve_throttle(cmd, 0.2) == 0.9


def test_cv_authority_is_preserved_through_the_bridge():
    """
    With the agent ceiling set high, the autopilot's own cornering slow-down
    must still reach the drivetrain. This is what distinguishes a ceiling from
    a replacement: an implementation that simply assigned the agent's value
    would pass the stop test above and fail this one.
    """
    bridge = make_bridge()
    bridge.arm()
    bridge.set_control(throttle=1.0)

    fast, _, _ = bridge.run_threaded(pilot_throttle=0.30)
    slow, _, _ = bridge.run_threaded(pilot_throttle=0.15)

    assert fast == 0.30
    assert slow == 0.15, "the autopilot's slow-down was swallowed by the bridge"


def test_throttle_is_clamped_to_range():
    bridge = make_bridge()
    assert bridge.set_control(throttle=5.0).throttle == 1.0
    assert bridge.set_control(throttle=-5.0).throttle == -1.0


# ----------------------------------------------------------------- watchdog


def test_watchdog_zeroes_throttle_when_the_agent_goes_quiet():
    bridge = make_bridge(command_timeout_s=0.05)
    bridge.arm()
    bridge.set_control(throttle=1.0)

    moving, _, _ = bridge.run_threaded(pilot_throttle=0.3)
    assert moving == 0.3

    time.sleep(0.08)
    stopped, _, _ = bridge.run_threaded(pilot_throttle=0.3)
    assert stopped == 0.0
    assert bridge.snapshot().watchdog_tripped is True


def test_watchdog_does_not_trip_while_commands_keep_arriving():
    bridge = make_bridge(command_timeout_s=0.2)
    bridge.arm()
    for _ in range(5):
        bridge.set_control(throttle=1.0)
        applied, _, _ = bridge.run_threaded(pilot_throttle=0.3)
        assert applied == 0.3
        time.sleep(0.02)
    assert bridge.snapshot().watchdog_tripped is False


# ----------------------------------------------------------------- lifecycle


def test_car_does_not_move_until_started():
    bridge = make_bridge()
    bridge.set_control(throttle=1.0)
    applied, _, armed = bridge.run_threaded(pilot_throttle=0.3)
    assert applied == 0.0
    assert armed is False


def test_start_then_stop():
    bridge = make_bridge()
    bridge.lifecycle.start()
    assert bridge.is_armed() is True
    bridge.set_control(throttle=1.0)
    assert bridge.run_threaded(pilot_throttle=0.3)[0] == 0.3

    bridge.lifecycle.stop()
    assert bridge.is_armed() is False
    assert bridge.run_threaded(pilot_throttle=0.3)[0] == 0.0


def test_emergency_stop_zeroes_throttle_without_disarming():
    bridge = make_bridge()
    bridge.arm()
    bridge.set_control(throttle=1.0)
    bridge.emergency_stop()
    applied, _, armed = bridge.run_threaded(pilot_throttle=0.3)
    assert applied == 0.0
    assert armed is True, "emergency_stop must not touch the lifecycle"


# ----------------------------------------------------------------- lanes


def test_named_lane_converts_to_pixels():
    bridge = make_bridge()
    # 12 inches right at 4 px/inch
    assert bridge.lane_offset_px_for("right") == 48
    assert bridge.lane_offset_px_for("left") == -48
    assert bridge.lane_offset_px_for("center") == 0


def test_unknown_lane_is_an_error_not_a_silent_zero():
    bridge = make_bridge()
    with pytest.raises(ValueError, match="Unknown lane"):
        bridge.lane_offset_px_for("shoulder")


def test_inches_conversion_requires_calibration():
    class NoCal(Cfg):
        CV_PIXELS_PER_INCH = None

    bridge = MCPBridge(NoCal(), serve=False)
    assert bridge.px_to_inches(10) is None
    with pytest.raises(ValueError, match="calibration"):
        bridge.inches_to_px(6.0)


def test_lane_offset_reaches_the_output():
    bridge = make_bridge()
    bridge.arm()
    bridge.set_control(lane_offset_px=25)
    _, offset, _ = bridge.run_threaded(pilot_throttle=0.2)
    assert offset == 25


# ----------------------------------------------------------------- state


def test_loop_count_increases_so_stale_frames_are_detectable():
    bridge = make_bridge()
    bridge.run_threaded(cam_img=frame(), pilot_throttle=0.2)
    first = bridge.snapshot().loop_count
    bridge.run_threaded(cam_img=frame(), pilot_throttle=0.2)
    second = bridge.snapshot().loop_count
    assert second > first


def test_frame_encodes_to_decodable_jpeg():
    from donkeycar.utils import binary_to_img, img_to_arr

    bridge = make_bridge()
    bridge.run_threaded(cam_img=frame(value=200))
    jpeg = bridge.frame_jpeg()
    assert jpeg is not None
    assert jpeg[:2] == b"\xff\xd8"  # JPEG SOI marker
    arr = img_to_arr(binary_to_img(jpeg))
    assert arr.shape == (24, 32, 3)


def test_no_frame_yields_no_jpeg():
    bridge = make_bridge()
    assert bridge.frame_jpeg() is None


def test_cv_overlay_frame_is_preferred():
    bridge = make_bridge()
    bridge.run_threaded(cam_img=frame(10), cv_img=frame(250))
    assert int(bridge.snapshot().frame.mean()) == 250


def test_state_snapshot_is_a_copy():
    bridge = make_bridge()
    bridge.run_threaded(cam_img=frame(), pilot_throttle=0.2)
    snap = bridge.snapshot()
    bridge.run_threaded(cam_img=frame(), pilot_throttle=0.3)
    assert snap.loop_count != bridge.snapshot().loop_count


def test_no_torn_reads_under_concurrency():
    """
    The loop thread writes state while reader threads snapshot it. Every
    snapshot must be internally coherent: the throttle recorded must be the one
    that belongs to that loop's autopilot throttle, never a mix of two loops.
    """
    bridge = make_bridge()
    bridge.arm()
    bridge.set_control(throttle=1.0)
    stop = threading.Event()
    bad: list[str] = []

    def drive_loop():
        i = 0
        while not stop.is_set():
            # throttle alternates so a mismatch is detectable
            bridge.set_control(throttle=1.0)
            bridge.run_threaded(cam_img=frame(), pilot_throttle=0.1 if i % 2 else 0.3)
            i += 1

    def reader():
        while not stop.is_set():
            s = bridge.snapshot()
            # applied is min(1.0, cv_throttle) == cv_throttle here
            if (
                s.cv_throttle is not None
                and s.applied_throttle is not None
                and abs(s.applied_throttle - s.cv_throttle) > 1e-9
            ):
                bad.append(f"{s.applied_throttle} vs {s.cv_throttle}")

    threads = [threading.Thread(target=drive_loop)] + [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    time.sleep(0.4)
    stop.set()
    for t in threads:
        t.join()

    assert not bad, f"torn reads observed: {bad[:5]}"


# ----------------------------------------------------------------- track


def test_track_config_reports_geometry_and_lanes():
    bridge = make_bridge()
    track = bridge.track_config()
    assert track["segment_length_inches"] == 36.0
    assert track["cross_length_inches"] == 12.0
    assert track["segment_count"] == 8
    assert track["continuous"] is True
    assert set(track["lanes"]) == {"left", "center", "right"}


def test_track_config_carries_no_traffic_feature_list():
    """Features are discovered visually; the file describes geometry only."""
    bridge = make_bridge()
    track = bridge.track_config()
    assert not any("feature" in key for key in track)


# ----------------------------------------------------------------- server


def test_build_server_registers_the_tool_surface():
    bridge = make_bridge()
    server = bridge.build_server()
    names = {t.name for t in server._tool_manager.list_tools()}
    expected = {
        "get_track_config",
        "get_vehicle_state",
        "set_control",
        "start",
        "stop",
        "emergency_stop",
        "get_calibration",
    }
    assert expected <= names, expected - names


def test_part_writes_nothing_to_stdout(capsys):
    bridge = make_bridge()
    bridge.arm()
    bridge.set_control(throttle=0.5)
    bridge.run_threaded(cam_img=frame(), pilot_throttle=0.2)
    bridge.emergency_stop()
    assert capsys.readouterr().out == ""


# ------------------------------------------------- through a real MCP client
#
# These drive the server through an in-process MCP client rather than calling
# the bridge directly. That boundary is where a return annotation decides
# whether a value is rendered as a content block or as structured JSON, and a
# mistake there fails at request time -- invisible to every test above.


def _call(server, tool, args=None):
    import asyncio

    from mcp.client.client import Client

    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, args or {})

    return asyncio.run(go())


def _tools(server):
    import asyncio

    from mcp.client.client import Client

    async def go():
        async with Client(server) as client:
            return await client.list_tools()

    return asyncio.run(go())


def _text(result):
    return "\n".join(b.text for b in result.content if type(b).__name__ == "TextContent")


def test_client_sees_the_whole_tool_surface():
    server = make_bridge().build_server()
    names = {t.name for t in _tools(server).tools}
    assert {
        "get_track_config",
        "get_vehicle_state",
        "set_control",
        "start",
        "stop",
        "emergency_stop",
        "get_calibration",
    } <= names


def test_vehicle_state_returns_text_and_an_image_block():
    """
    The frame must come back as an image content block. Returning it inside a
    loosely annotated list makes the SDK try to serialise it as JSON, which
    fails only when a client actually calls the tool.
    """
    bridge = make_bridge()
    bridge.run_threaded(cam_img=frame(), pilot_steering=0.1, pilot_throttle=0.25, user_mode="local_pilot")
    result = _call(bridge.build_server(), "get_vehicle_state")

    kinds = [type(b).__name__ for b in result.content]
    assert "TextContent" in kinds
    assert "ImageContent" in kinds, kinds
    assert result.is_error is not True

    payload = json.loads(_text(result))
    assert payload["autopilot_throttle"] == 0.25
    assert payload["user_mode"] == "local_pilot"
    assert payload["loop_count"] >= 1


def test_vehicle_state_without_a_frame_is_still_valid():
    result = _call(make_bridge().build_server(), "get_vehicle_state")
    kinds = [type(b).__name__ for b in result.content]
    assert kinds == ["TextContent"]
    assert result.is_error is not True


def test_start_and_stop_through_the_client():
    bridge = make_bridge()
    server = bridge.build_server()

    assert "armed" in _text(_call(server, "start"))
    assert bridge.is_armed() is True

    assert "disarmed" in _text(_call(server, "stop"))
    assert bridge.is_armed() is False


def test_set_control_by_lane_name_through_the_client():
    bridge = make_bridge()
    server = bridge.build_server()
    result = _call(server, "set_control", {"throttle": 0.5, "lane": "right"})
    payload = json.loads(_text(result))
    assert payload["lane_offset_px"] == 48
    assert payload["throttle"] == 0.5
    assert bridge.command().lane_offset_px == 48


def test_set_control_rejects_both_lane_and_inches():
    server = make_bridge().build_server()
    result = _call(server, "set_control", {"lane": "right", "lane_offset_inches": 3.0})
    assert result.is_error is True
    assert "not both" in _text(result)


def test_unknown_lane_is_an_error_through_the_client():
    server = make_bridge().build_server()
    result = _call(server, "set_control", {"lane": "shoulder"})
    assert result.is_error is True
    assert "Unknown lane" in _text(result)


def test_track_config_through_the_client():
    server = make_bridge().build_server()
    payload = json.loads(_text(_call(server, "get_track_config")))
    assert payload["segment_count"] == 8
    assert payload["continuous"] is True


# ------------------------------------------------------------- track loading


def test_bridge_reads_track_yml_from_the_car_directory(tmp_path):
    (tmp_path / "track.yml").write_text(
        "segment_length_inches: 24\n"
        "cross_length_inches: 6\n"
        "continuous: true\n"
        "segment_count: 12\n"
        "lanes:\n"
        "  center: 0\n"
        "  outside: 9\n"
    )
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    track = bridge.track_config()
    assert track["segment_length_inches"] == 24.0
    assert track["segment_count"] == 12
    assert sorted(track["lanes"]) == ["center", "outside"]
    # 9 inches at 4 px/inch
    assert bridge.lane_offset_px_for("outside") == 36


def test_bridge_falls_back_to_config_constants_without_a_file(tmp_path):
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    track = bridge.track_config()
    assert sorted(track["lanes"]) == ["center", "left", "right"]
    assert "no track.yml" in (track["description"] or "")


def test_malformed_track_file_refuses_to_start(tmp_path):
    """
    Driving a track you have mis-described is worse than not starting, so a bad
    file is an error rather than a quiet fallback to defaults.
    """
    (tmp_path / "track.yml").write_text(
        "segment_length_inches: -5\ncross_length_inches: 12\ncontinuous: false\nlanes: {center: 0}\n"
    )
    with pytest.raises(TrackConfigError, match="positive"):
        MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))


def test_track_from_a_file_reaches_the_client(tmp_path):
    (tmp_path / "track.yml").write_text(
        "name: Loop\nsegment_length_inches: 36\ncross_length_inches: 12\ncontinuous: true\nlanes: {center: 0}\n"
    )
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    payload = json.loads(_text(_call(bridge.build_server(), "get_track_config")))
    assert payload["name"] == "Loop"
    assert payload["continuous"] is True
    assert "features" not in payload


# --------------------------------------------------------------- calibration


def _write_calibration(tmp_path):
    """A real board calibration, produced from the synthetic scene."""
    from donkeycar.parts.cv_calibration import calibrate_from_image

    from .test_cv_calibration import COLS, ROWS, SQUARE_INCHES, camera_view
    from .test_cv_calibration import Cfg as CalCfg

    calibration = calibrate_from_image(camera_view(), CalCfg(), (COLS, ROWS), SQUARE_INCHES)
    calibration.save(str(tmp_path / "cv_calibration.json"))
    return calibration


def test_bridge_reports_no_calibration_when_there_is_none(tmp_path):
    class NoCal(Cfg):
        CV_PIXELS_PER_INCH = None

    bridge = MCPBridge(NoCal(), serve=False, car_dir=str(tmp_path))
    payload = bridge.calibration()
    assert payload["calibrated"] is False
    assert "calibrate-cv" in payload["reason"]


def test_manual_calibration_converts_lanes_but_cannot_measure(tmp_path):
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    payload = bridge.calibration()
    assert payload["calibrated"] is True
    assert payload["source"] == "config"
    assert payload["can_measure_points"] is False
    with pytest.raises(ValueError, match="no homography"):
        bridge.measure_ground_point(10, 10)


def test_board_calibration_enables_ground_measurement(tmp_path):
    _write_calibration(tmp_path)
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    bridge.run_threaded(cam_img=frame(w=320, h=240))

    payload = bridge.calibration()
    assert payload["can_measure_points"] is True
    assert payload["source"] == "chessboard"

    measured = bridge.measure_ground_point(160, 120)
    assert "lateral_inches" in measured and "forward_inches" in measured


def test_measuring_outside_the_frame_is_rejected(tmp_path):
    _write_calibration(tmp_path)
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    bridge.run_threaded(cam_img=frame(w=320, h=240))
    with pytest.raises(ValueError, match="outside"):
        bridge.measure_ground_point(9999, 9999)


def test_stale_calibration_is_flagged_not_silently_used(tmp_path):
    """
    A calibration taken at a different scan line describes a different
    measurement. Reusing it silently is how a lane change ends up in the
    wrong lane.
    """
    _write_calibration(tmp_path)

    class MovedScanLine(Cfg):
        SCAN_Y = 40
        IMAGE_W = 320
        IMAGE_H = 240
        CAMERA_TYPE = "MOCK"

    bridge = MCPBridge(MovedScanLine(), serve=False, car_dir=str(tmp_path))
    payload = bridge.calibration()
    assert payload["stale"] is True
    assert any("scan_y" in reason for reason in payload["stale_reasons"])


def test_measure_ground_point_through_the_client(tmp_path):
    _write_calibration(tmp_path)
    bridge = MCPBridge(Cfg(), serve=False, car_dir=str(tmp_path))
    bridge.run_threaded(cam_img=frame(w=320, h=240))

    result = _call(bridge.build_server(), "measure_ground_point", {"pixel_x": 160, "pixel_y": 120})
    assert result.is_error is not True
    payload = json.loads(_text(result))
    assert "lateral_inches" in payload


def test_measure_without_calibration_tells_the_agent_what_to_do(tmp_path):
    class NoCal(Cfg):
        CV_PIXELS_PER_INCH = None

    bridge = MCPBridge(NoCal(), serve=False, car_dir=str(tmp_path))
    result = _call(bridge.build_server(), "measure_ground_point", {"pixel_x": 10, "pixel_y": 10})
    assert result.is_error is True
    assert "calibrate-cv" in _text(result)


# --------------------------------------------------------------- drive mode


class FakeController:
    """Stands in for the web controller, which latches its mode."""

    def __init__(self):
        self.mode_latch = None


def test_arming_puts_the_car_into_autopilot_mode():
    """
    The CV controller only runs when run_pilot is set, and that comes from
    user/mode. Without this the autopilot never runs, pilot/throttle stays None,
    and the throttle ceiling resolves to zero forever -- an agent could arm the
    car, command full throttle, and never move.
    """
    bridge = make_bridge()
    controller = FakeController()
    bridge.attach_controller(controller)

    bridge.arm()
    assert controller.mode_latch == "local_pilot"

    bridge.disarm()
    assert controller.mode_latch == "user"


def test_arming_without_a_controller_is_harmless():
    bridge = make_bridge()
    bridge.arm()
    assert bridge.is_armed() is True


def test_controller_that_cannot_latch_is_reported_not_crashed(caplog):
    class NoLatch:
        pass

    bridge = make_bridge()
    bridge.attach_controller(NoLatch())
    bridge.arm()
    assert bridge.is_armed() is True
    assert "WEB_INIT_MODE" in caplog.text
