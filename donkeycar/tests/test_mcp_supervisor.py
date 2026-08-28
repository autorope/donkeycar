"""
Tests for the `donkey mcp` supervisor.

The behaviour that matters here is the one part-mode cannot provide: stop must
really tear the vehicle down, and start must build a fresh one afterwards.
"""

import os
import socket
import time

import donkeycar as dk
from donkeycar.management.mcp import VehicleSupervisor, load_vehicle_builder
from donkeycar.templates import cv_control

from .setup import custom_template


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _headless_cfg(tmp_path):
    """A car that needs no hardware, on a private web port."""
    path = custom_template(str(tmp_path / "car"), template="cv_control")
    with open(os.path.join(path, "myconfig.py"), "w") as myconfig:
        myconfig.write("CAMERA_TYPE = 'MOCK'\n")
        myconfig.write("USE_SSD1306_128_32 = False\n")
        myconfig.write("DRIVE_TRAIN_TYPE = 'None'\n")
        # Each vehicle build stands up a web controller; give it its own port so
        # repeated builds do not collide.
        myconfig.write(f"WEB_CONTROL_PORT = {_free_port()}\n")
    cfg = dk.load_config(os.path.join(path, "config.py"))
    cfg.MAX_LOOPS = None
    return cfg, path


def _make_supervisor(tmp_path):
    cfg, _ = _headless_cfg(tmp_path)
    return VehicleSupervisor(cfg, cv_control.build_vehicle, builder_source="test")


def _wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


# ------------------------------------------------------------------ lifecycle


def test_nothing_runs_until_start(tmp_path):
    sup = _make_supervisor(tmp_path)
    assert sup.is_running() is False
    assert sup.bridge.is_armed() is False


def test_start_stop_start_rebuilds_the_vehicle(tmp_path):
    """
    The reason M3 exists. In part mode a stop ends the process, so this cycle is
    impossible; here each start must produce a fresh, running vehicle.
    """
    sup = _make_supervisor(tmp_path)

    assert sup.start() == "started"
    assert _wait_until(sup.is_running), "vehicle did not start"
    first = sup._vehicle
    assert first is not None

    assert sup.stop() == "stopped"
    assert sup.is_running() is False
    assert sup._vehicle is None

    assert sup.start() == "started"
    assert _wait_until(sup.is_running), "vehicle did not restart"
    second = sup._vehicle
    assert second is not None
    assert second is not first, "start after stop must build a new vehicle"

    sup.stop()


def test_stop_leaves_throttle_at_zero(tmp_path):
    """No coasting: the bridge is disarmed before the loop is torn down."""
    sup = _make_supervisor(tmp_path)
    sup.start()
    _wait_until(sup.is_running)
    sup.bridge.set_control(throttle=1.0)
    time.sleep(0.2)

    sup.stop()
    assert sup.bridge.is_armed() is False
    applied, _, armed = sup.bridge.run_threaded(pilot_throttle=0.3)
    assert applied == 0.0
    assert armed is False


def test_double_start_is_not_an_error(tmp_path):
    sup = _make_supervisor(tmp_path)
    assert sup.start() == "started"
    _wait_until(sup.is_running)
    assert sup.start() == "already running"
    sup.stop()


def test_stop_when_not_running(tmp_path):
    sup = _make_supervisor(tmp_path)
    assert sup.stop() == "not running"


def test_bridge_survives_a_restart(tmp_path):
    """
    The agent's connection and command state must outlive the vehicle, so a
    restart does not require it to reconnect.
    """
    sup = _make_supervisor(tmp_path)
    bridge = sup.bridge
    sup.start()
    _wait_until(sup.is_running)
    sup.bridge.set_control(lane_offset_px=17)
    sup.stop()
    sup.start()
    _wait_until(sup.is_running)

    assert sup.bridge is bridge
    assert sup.bridge.command().lane_offset_px == 17
    sup.stop()


def test_supervisor_satisfies_the_lifecycle_protocol(tmp_path):
    sup = _make_supervisor(tmp_path)
    assert sup.bridge.lifecycle is sup
    for name in ("start", "stop", "is_running"):
        assert callable(getattr(sup, name))


# -------------------------------------------------------- builder resolution


def test_uses_the_cars_own_manage_py(tmp_path):
    """A customised car directory is the truth for that car."""
    _cfg, path = _headless_cfg(tmp_path)
    builder, source = load_vehicle_builder(path)
    assert source.endswith("manage.py")
    assert builder is not cv_control.build_vehicle
    assert builder.__name__ == "build_vehicle"


def test_falls_back_when_manage_py_predates_build_vehicle(tmp_path, caplog):
    """
    manage.py is a copy of the template, so cars created before this work have
    no build_vehicle. Falling back beats refusing to start.
    """
    car = tmp_path / "oldcar"
    car.mkdir()
    (car / "manage.py").write_text("def drive(cfg, **kwargs):\n    pass\n")

    builder, source = load_vehicle_builder(str(car))
    assert builder is cv_control.build_vehicle
    assert source == "donkeycar.templates.cv_control"
    assert "predates the MCP work" in caplog.text


def test_falls_back_when_there_is_no_car_dir():
    builder, source = load_vehicle_builder(None)
    assert builder is cv_control.build_vehicle
    assert source == "donkeycar.templates.cv_control"


# ---------------------------------------------------------------------- CLI


def test_mcp_is_registered_as_a_donkey_command():
    from donkeycar.management.base import Mcp, execute_from_command_line

    src = execute_from_command_line.__code__.co_consts
    assert any(isinstance(c, str) and c == "mcp" for c in _flatten(src))
    assert hasattr(Mcp, "run")


def _flatten(consts):
    for c in consts:
        if isinstance(c, tuple):
            yield from _flatten(c)
        else:
            yield c
