"""
Tests for the cv_control template.

These run headless: a MOCK camera, no drivetrain and a bounded loop count, so
the whole vehicle pipeline is exercised without hardware.
"""

import os

import donkeycar as dk
from donkeycar.templates import cv_control
from donkeycar.vehicle import Vehicle

from .setup import custom_template


def _headless_cfg(tmp_path, max_loops=10):
    """
    Build a cv_control config that needs no hardware.

    Each test gets its own car directory. Sharing one (as the older template
    tests do via gettempdir()) leaks a tub whose schema then collides with the
    next template's tub.
    """
    path = custom_template(str(tmp_path / "car"), template="cv_control")
    with open(os.path.join(path, "myconfig.py"), "w") as myconfig:
        myconfig.write("CAMERA_TYPE = 'MOCK'\n")
        myconfig.write("USE_SSD1306_128_32 = False\n")
        myconfig.write("DRIVE_TRAIN_TYPE = 'None'\n")
    cfg = dk.load_config(os.path.join(path, "config.py"))
    cfg.MAX_LOOPS = max_loops
    return cfg


def test_config(tmp_path):
    cfg = _headless_cfg(tmp_path)
    assert cfg is not None
    assert cfg.CV_CONTROLLER_CLASS == "LineFollower"


def test_build_vehicle_returns_unstarted_vehicle(tmp_path):
    """build_vehicle assembles the pipeline but must not run it."""
    cfg = _headless_cfg(tmp_path)
    v = cv_control.build_vehicle(cfg)
    try:
        assert isinstance(v, Vehicle)
        assert len(v.parts) > 0
        # Nothing has run, so no part has written its outputs to memory yet.
        assert v.mem.get(["steering"]) == [None]
    finally:
        v.stop()


def test_drive_runs_the_loop(tmp_path):
    """drive() must still assemble and run on the calling thread, as before."""
    cfg = _headless_cfg(tmp_path, max_loops=10)
    cv_control.drive(cfg)


def test_mcp_part_absent_by_default(tmp_path):
    """
    Without --mcp the pipeline must be the pipeline it always was. An MCP
    bridge here would mean the default path had silently gained a network
    server.
    """
    cfg = _headless_cfg(tmp_path)
    v = cv_control.build_vehicle(cfg)
    try:
        names = [entry["part"].__class__.__name__ for entry in v.parts]
        assert not any("MCP" in name.upper() for name in names), names
    finally:
        v.stop()


def test_build_vehicle_does_not_accumulate_metadata(tmp_path):
    """
    build_vehicle appends cfg.METADATA to the caller's `meta` list. With a
    mutable default argument that append leaked across calls, which the MCP
    supervisor would hit every time it rebuilt the vehicle.
    """
    cfg = _headless_cfg(tmp_path)
    cfg.METADATA = ["k:v"]

    first = cv_control.build_vehicle(cfg)
    first.stop()
    second = cv_control.build_vehicle(cfg)
    second.stop()

    tub_writers = [e["part"] for e in second.parts if e["part"].__class__.__name__ == "TubWriter"]
    assert tub_writers, "expected a TubWriter in the pipeline"
    # One entry, not two: the second build must not see the first build's append.
    assert tub_writers[0].tub.manifest.metadata == {"k": "v"}


def test_lane_offset_is_wired_into_the_controller(tmp_path):
    """
    The controller must receive mcp/lane_offset_px from vehicle memory. Config
    alone does this wiring, so this guards the config as much as the part.
    """
    cfg = _headless_cfg(tmp_path)
    assert cfg.CV_CONTROLLER_INPUTS == ["cam/image_array", "mcp/lane_offset_px"]

    v = cv_control.build_vehicle(cfg)
    try:
        entries = [e for e in v.parts if e["part"].__class__.__name__ == "LineFollower"]
        assert entries, "expected a LineFollower in the pipeline"
        assert entries[0]["inputs"] == ["cam/image_array", "mcp/lane_offset_px"]
    finally:
        v.stop()


def test_missing_lane_offset_key_is_harmless(tmp_path):
    """
    With no MCP bridge running the key is absent from memory, which Memory.get
    resolves to None. The loop must run exactly as before.
    """
    cfg = _headless_cfg(tmp_path, max_loops=5)
    v = cv_control.build_vehicle(cfg)
    try:
        assert v.mem.get(["mcp/lane_offset_px"]) == [None]
        v.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=5)
    finally:
        v.stop()


def test_mcp_bridge_present_when_enabled(tmp_path):
    """--mcp adds the bridge between the CV controller and DriveMode."""
    cfg = _headless_cfg(tmp_path)
    v = cv_control.build_vehicle(cfg, enable_mcp=True)
    try:
        names = [e["part"].__class__.__name__ for e in v.parts]
        assert "MCPBridge" in names

        bridge_i = names.index("MCPBridge")
        follower_i = names.index("LineFollower")
        drivemode_i = names.index("DriveMode")
        assert follower_i < bridge_i < drivemode_i, names

        entry = v.parts[bridge_i]
        assert entry["outputs"] == ["pilot/throttle", "mcp/lane_offset_px", "mcp/armed"]
        assert entry["inputs"][0] == "cam/image_array"
    finally:
        v.stop()


def test_mcp_pipeline_runs_and_holds_the_car_until_started(tmp_path):
    """
    End to end through the real vehicle loop: with the bridge added but never
    started, throttle at the drivetrain must stay zero.
    """
    cfg = _headless_cfg(tmp_path, max_loops=8)
    v = cv_control.build_vehicle(cfg, enable_mcp=True)
    try:
        v.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=8)
        assert v.mem.get(["mcp/armed"]) == [False]
        assert v.mem.get(["pilot/throttle"]) == [0.0]
    finally:
        v.stop()
