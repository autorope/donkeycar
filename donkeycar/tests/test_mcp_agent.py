"""
The five activities, driven against a real vehicle loop with a MOCK camera.

Perception is scripted, because recognising a stop sign is the agent's job and
not something CI can do. Everything else is real: a built vehicle, the bridge,
the throttle ceiling, the lane conversion and the ground measurement.
"""

import os

import pytest

import donkeycar as dk
from donkeycar.mcp_agent import (
    AddressPolicy,
    BridgeSession,
    LapPolicy,
    ObstacleAvoidPolicy,
    ObstacleHaltPolicy,
    ScriptedPerception,
    Sighting,
    StopSignPolicy,
    build_policy,
)
from donkeycar.parts.mcp_server import MCPBridge

from .setup import custom_template
from .test_cv_calibration import COLS, ROWS, SQUARE_INCHES, camera_view
from .test_cv_calibration import Cfg as CalCfg


class FakeClock:
    """Time the policies can control, so a 5 second wait costs nothing."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make_bridge(tmp_path, calibrated=True):
    """A bridge with a real track and, optionally, a real calibration."""
    path = custom_template(str(tmp_path / "car"), template="cv_control")
    (tmp_path / "car" / "track.yml").write_text(
        "segment_length_inches: 36\n"
        "cross_length_inches: 12\n"
        "continuous: true\n"
        "segment_count: 4\n"
        "lanes:\n"
        "  left: -12\n"
        "  center: 0\n"
        "  right: 12\n"
    )
    if calibrated:
        from donkeycar.parts.cv_calibration import calibrate_from_image

        calibrate_from_image(camera_view(), CalCfg(), (COLS, ROWS), SQUARE_INCHES).save(
            os.path.join(path, "cv_calibration.json")
        )

    cfg = dk.load_config(os.path.join(path, "config.py"))
    return MCPBridge(cfg, serve=False, car_dir=path)


def session_for(tmp_path, **kwargs):
    bridge = make_bridge(tmp_path, **kwargs)
    # One loop so there is state and a frame to report.
    bridge.run_threaded(cam_img=camera_view(), pilot_steering=0.0, pilot_throttle=0.3, user_mode="local_pilot")
    return bridge, BridgeSession(bridge)


def run(policy, ticks, bridge=None, pilot_throttle=0.3):
    """Tick the policy, feeding the vehicle loop between ticks."""
    policy.begin()
    for _ in range(ticks):
        if bridge is not None:
            bridge.run_threaded(cam_img=camera_view(), pilot_throttle=pilot_throttle)
        policy.step()
        if policy.finished:
            break
    policy.end()
    return policy


# ------------------------------------------------------------------ plumbing


def test_policy_reads_the_track_and_starts_the_car(tmp_path):
    bridge, session = session_for(tmp_path)
    policy = LapPolicy(session, ScriptedPerception())
    policy.begin()
    assert policy.track["segment_count"] == 4
    assert bridge.is_armed() is True
    assert bridge.command().throttle > 0


def test_end_stops_and_zeroes_throttle(tmp_path):
    bridge, session = session_for(tmp_path)
    policy = LapPolicy(session, ScriptedPerception())
    policy.begin()
    policy.end()
    assert bridge.command().throttle == 0.0
    assert bridge.is_armed() is False


def test_unknown_activity_lists_the_real_ones(tmp_path):
    _bridge, session = session_for(tmp_path)
    with pytest.raises(ValueError, match="Unknown activity"):
        build_policy("teleport", session, ScriptedPerception())


def test_every_activity_is_buildable(tmp_path):
    _bridge, session = session_for(tmp_path)
    for name in ("lap", "stop-signs", "obstacle-halt", "obstacle-avoid"):
        assert build_policy(name, session, ScriptedPerception()) is not None


# ---------------------------------------------------------- 1. drive a lap


def test_lap_drives_then_stops(tmp_path):
    bridge, session = session_for(tmp_path)
    script = [[], [], [Sighting(kind="lap_complete", pixel=(160, 120))]]
    policy = run(LapPolicy(session, ScriptedPerception(script)), ticks=5, bridge=bridge)

    assert policy.finished is True
    assert "lap complete" in " ".join(policy.log)
    assert bridge.command().throttle == 0.0


# ------------------------------------------------------- 2. stop at signs


def test_stops_at_a_stop_sign_and_waits_five_seconds(tmp_path):
    bridge, session = session_for(tmp_path)
    clock = FakeClock()
    sign = Sighting(kind="stop_sign", pixel=(160, 200))
    script = [[sign], [sign], [], [], []]

    policy = StopSignPolicy(session, ScriptedPerception(script), clock=clock)
    policy.begin()

    bridge.run_threaded(cam_img=camera_view(), pilot_throttle=0.3)
    policy.step()
    policy.step()
    assert bridge.command().throttle == 0.0, "should have stopped at the sign"

    # Still waiting a moment later.
    clock.advance(2.0)
    policy.step()
    assert bridge.command().throttle == 0.0

    # Past five seconds it moves off again.
    clock.advance(4.0)
    policy.step()
    assert bridge.command().throttle > 0.0
    assert any("waiting" in line for line in policy.log)


def test_a_served_stop_sign_is_not_stopped_for_twice(tmp_path):
    bridge, session = session_for(tmp_path)
    clock = FakeClock()
    sign = Sighting(kind="stop_sign", pixel=(160, 200))
    policy = StopSignPolicy(session, ScriptedPerception([[sign]] * 6), clock=clock)
    policy.begin()

    policy.step()
    assert bridge.command().throttle == 0.0
    clock.advance(6.0)
    policy.step()
    assert bridge.command().throttle > 0.0, "the same sign should not stop it again"


# ------------------------------------------------- 3. halt at an obstacle


def test_waits_while_a_blocking_obstacle_is_present(tmp_path):
    bridge, session = session_for(tmp_path)
    person = Sighting(kind="obstacle", pixel=(160, 210), blocking=True)
    script = [[person], [person], [], []]
    policy = ObstacleHaltPolicy(session, ScriptedPerception(script), clock=FakeClock())
    policy.begin()

    policy.step()
    assert bridge.command().throttle == 0.0
    policy.step()
    assert bridge.command().throttle == 0.0
    assert any("waiting for the obstacle" in line for line in policy.log)

    policy.step()  # obstacle gone
    assert bridge.command().throttle > 0.0


# ------------------------------------------------ 4. drive around one


def test_passes_a_non_blocking_obstacle_in_another_lane(tmp_path):
    bridge, session = session_for(tmp_path)
    car = Sighting(kind="obstacle", pixel=(160, 210), blocking=False)
    script = [[car], []]
    policy = ObstacleAvoidPolicy(session, ScriptedPerception(script), clock=FakeClock())
    policy.begin()

    policy.step()
    assert bridge.command().lane_offset_px != 0, "should have moved out of the centre lane"
    assert bridge.command().throttle > 0.0
    assert any("passing the obstacle" in line for line in policy.log)

    policy.step()
    assert bridge.command().lane_offset_px == 0, "should return to the centre lane"


def test_a_blocking_obstacle_still_stops_the_avoiding_policy(tmp_path):
    """Which obstacles may be passed is a judgement the agent makes by looking."""
    bridge, session = session_for(tmp_path)
    person = Sighting(kind="obstacle", pixel=(160, 210), blocking=True)
    policy = ObstacleAvoidPolicy(session, ScriptedPerception([[person]]), clock=FakeClock())
    policy.begin()
    policy.step()
    assert bridge.command().throttle == 0.0


# ---------------------------------------------------- 5. stop at an address


def test_stops_at_the_requested_address_until_released(tmp_path):
    bridge, session = session_for(tmp_path)
    target = Sighting(kind="address", pixel=(160, 205), text="214")
    other = Sighting(kind="address", pixel=(40, 205), text="118")
    script = [[other], [target], [], [], []]

    policy = AddressPolicy(session, ScriptedPerception(script), destination="214", clock=FakeClock())
    policy.begin()

    policy.step()  # a different address: keep going
    assert bridge.command().throttle > 0.0

    policy.step()  # the destination
    assert bridge.command().throttle == 0.0
    assert policy.arrived is True

    policy.step()  # still waiting
    assert bridge.command().throttle == 0.0

    policy.release()
    policy.step()
    assert bridge.command().throttle > 0.0


# ------------------------------------------------------------- approach


def test_slows_down_with_distance(tmp_path):
    """
    The reason measure_ground_point matters: braking has to begin before the
    thing is close, and apparent size is not a distance.
    """
    _bridge, session = session_for(tmp_path)
    policy = LapPolicy(session, ScriptedPerception())
    far = policy._approach_throttle(48.0)
    mid = policy._approach_throttle(24.0)
    near = policy._approach_throttle(6.0)
    assert far > mid > near
    assert near == 0.0


def test_unmeasurable_sighting_does_not_stop_the_car(tmp_path):
    """
    Without a calibration the agent cannot measure distance. It should say so
    and keep to cruise rather than brake for something it cannot locate.
    """
    bridge, session = session_for(tmp_path, calibrated=False)
    sign = Sighting(kind="stop_sign", pixel=(160, 200))
    policy = StopSignPolicy(session, ScriptedPerception([[sign]]), clock=FakeClock())
    policy.begin()
    policy.step()
    assert any("could not measure" in line for line in policy.log)
    assert bridge.command().throttle > 0.0
