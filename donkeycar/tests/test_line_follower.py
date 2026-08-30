"""
Tests for the LineFollower CV autopilot, in particular the lane offset added so
an MCP agent can ask the car to hold a lane beside the tape rather than on it.

No camera and no hardware: images are synthesised with a known yellow column.
"""

import numpy as np
import pytest
from simple_pid import PID

from donkeycar.parts.line_follower import LineFollower

IMAGE_W = 160
IMAGE_H = 120
SCAN_Y = 60
SCAN_HEIGHT = 10


class Cfg:
    """Minimal stand-in for the car config that LineFollower reads."""

    OVERLAY_IMAGE = False
    SCAN_Y = SCAN_Y
    SCAN_HEIGHT = SCAN_HEIGHT
    # Wide hue range so the synthetic yellow bar is detected reliably.
    COLOR_THRESHOLD_LOW = (20, 100, 100)
    COLOR_THRESHOLD_HIGH = (40, 255, 255)
    TARGET_PIXEL = IMAGE_W // 2
    TARGET_THRESHOLD = 10
    CONFIDENCE_THRESHOLD = 1
    THROTTLE_INITIAL = 0.15
    THROTTLE_STEP = 0.05
    THROTTLE_MAX = 0.30
    THROTTLE_MIN = 0.15
    IMAGE_W = IMAGE_W


def make_image(line_x, width=IMAGE_W, height=IMAGE_H, bar=6):
    """An RGB frame that is black except for a yellow vertical bar at line_x."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    lo = max(0, line_x - bar // 2)
    hi = min(width, line_x + bar // 2 + 1)
    # Pure yellow in RGB.
    img[:, lo:hi] = (255, 255, 0)
    return img


def make_follower(cfg=None, **pid_kwargs):
    cfg = cfg or Cfg()
    pid = PID(Kp=-0.01, Ki=0.0, Kd=0.0, **pid_kwargs)
    return LineFollower(pid, cfg)


def test_detects_the_line():
    lf = make_follower()
    img = make_image(100)
    max_yellow, confidence, _mask = lf.get_i_color(img)
    assert abs(max_yellow - 100) <= 3
    assert confidence > 0
    # The declared return type is plain ints, not numpy scalars.
    assert isinstance(max_yellow, int)
    assert isinstance(confidence, int)


def test_no_offset_matches_base_target():
    """Called with one argument, behaviour is exactly what it always was."""
    lf = make_follower()
    img = make_image(Cfg.TARGET_PIXEL)
    lf.run(img)
    assert lf.effective_target_pixel == Cfg.TARGET_PIXEL
    assert lf.pid_st.setpoint == Cfg.TARGET_PIXEL


def test_explicit_zero_offset_is_identical_to_none():
    lf_none = make_follower()
    lf_zero = make_follower()
    img = make_image(70)
    a = lf_none.run(img, None)
    b = lf_zero.run(img, 0)
    assert a[0] == b[0]
    assert a[1] == b[1]


def test_offset_shifts_the_setpoint():
    lf = make_follower()
    img = make_image(Cfg.TARGET_PIXEL)
    lf.run(img, 20)
    assert lf.effective_target_pixel == Cfg.TARGET_PIXEL + 20
    assert lf.pid_st.setpoint == Cfg.TARGET_PIXEL + 20

    lf.run(img, -20)
    assert lf.effective_target_pixel == Cfg.TARGET_PIXEL - 20
    assert lf.pid_st.setpoint == Cfg.TARGET_PIXEL - 20


def test_steering_sign_flips_across_the_line():
    """
    With the line fixed, moving the target from one side of it to the other must
    reverse the steering command.
    """
    line_x = Cfg.TARGET_PIXEL
    img = make_image(line_x)

    left = make_follower()
    left.run(img, -30)

    right = make_follower()
    right.run(img, +30)

    assert left.steering * right.steering < 0, (left.steering, right.steering)


@pytest.mark.parametrize("offset", [-10_000, -500, 500, 10_000])
def test_offset_clamps_into_the_frame(offset):
    """A wild offset must clamp, not wrap, go negative, or raise."""
    lf = make_follower()
    img = make_image(80)
    lf.run(img, offset)
    assert 0 <= lf.effective_target_pixel <= IMAGE_W - 1


def test_clamp_falls_back_to_frame_width_without_image_w():
    """A config missing IMAGE_W must still clamp, using the frame it was given."""

    class NoWidthCfg:
        # Deliberately a fresh class rather than a subclass of Cfg: IMAGE_W must
        # be genuinely absent, and subclassing would inherit it.
        OVERLAY_IMAGE = False
        SCAN_Y = SCAN_Y
        SCAN_HEIGHT = SCAN_HEIGHT
        COLOR_THRESHOLD_LOW = Cfg.COLOR_THRESHOLD_LOW
        COLOR_THRESHOLD_HIGH = Cfg.COLOR_THRESHOLD_HIGH
        TARGET_PIXEL = Cfg.TARGET_PIXEL
        TARGET_THRESHOLD = Cfg.TARGET_THRESHOLD
        CONFIDENCE_THRESHOLD = Cfg.CONFIDENCE_THRESHOLD
        THROTTLE_INITIAL = Cfg.THROTTLE_INITIAL
        THROTTLE_STEP = Cfg.THROTTLE_STEP
        THROTTLE_MAX = Cfg.THROTTLE_MAX
        THROTTLE_MIN = Cfg.THROTTLE_MIN

    assert not hasattr(NoWidthCfg, "IMAGE_W")
    lf = make_follower(cfg=NoWidthCfg())
    assert lf.image_w is None
    img = make_image(80, width=IMAGE_W)
    lf.run(img, 10_000)
    assert 0 <= lf.effective_target_pixel <= IMAGE_W - 1


def test_throttle_ramp_uses_the_effective_target():
    """
    The cornering slow-down must measure distance from the *offset* target. If it
    still measured from the base target, an on-target offset run would be treated
    as off-target and would slow down instead of speeding up.
    """
    line_x = 40
    img = make_image(line_x)
    offset = line_x - Cfg.TARGET_PIXEL  # puts the effective target exactly on the line

    lf = make_follower()
    start = lf.throttle
    lf.run(img, offset)
    # Aligned with the line, so it should speed up.
    assert lf.throttle > start

    # Same frame, no offset: the target is far from the line, so it should slow.
    lf2 = make_follower()
    lf2.throttle = Cfg.THROTTLE_MAX
    lf2.run(img, None)
    assert lf2.throttle < Cfg.THROTTLE_MAX


def test_none_image_returns_the_declared_outputs():
    """
    run() must return exactly what CV_CONTROLLER_OUTPUTS declares. It once
    returned a four-tuple here against three declared names, which left
    cv/image_array set to False.
    """
    lf = make_follower()
    out = lf.run(None)
    assert len(out) == 5
    assert out == (0.0, 0.0, None, 0.0, False)


def test_steering_survives_a_pid_that_returns_none():
    """
    simple_pid returns None until it has produced an output. Assigning that to
    steering would propagate None into the drivetrain.
    """
    lf = make_follower()
    lf.pid_st.auto_mode = False  # forces __call__ to return _last_output, i.e. None
    assert lf.pid_st(0) is None
    img = make_image(80)
    steering, throttle, _img, _conf, _seen = lf.run(img, 0)
    assert steering == 0.0
    assert isinstance(steering, float)
    assert isinstance(throttle, float)


def test_overlay_runs_and_preserves_shape():
    cfg = Cfg()
    cfg.OVERLAY_IMAGE = True
    lf = make_follower(cfg=cfg)
    img = make_image(80)
    _, _, out, _conf, _seen = lf.run(img, 15)
    assert out is not None
    assert out.shape == img.shape


# ------------------------------------------------ losing sight of the line


def blank_image(width=IMAGE_W, height=IMAGE_H):
    """No tape anywhere."""
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_reports_confidence_and_detection():
    """
    An agent cannot tell a confident lock from a lost line by steering alone --
    both look like a number. These are what make the difference visible.
    """
    lf = make_follower()
    _, _, _, conf, seen = lf.run(make_image(80))
    assert seen is True
    assert conf > 0

    _, _, _, conf, seen = lf.run(blank_image())
    assert seen is False
    assert conf < Cfg.CONFIDENCE_THRESHOLD


def test_steering_decays_toward_centre_when_the_line_is_lost():
    """
    Observed on a real track: the car lost the line at full right lock, held
    that steering, and drove off the course into the furniture. Holding the last
    command means driving blind in a circle.
    """
    lf = make_follower()
    lf.steering = 0.9  # as if mid-turn when the line vanished

    seen = [lf.run(blank_image())[0] for _ in range(5)]
    assert seen[0] < 0.9, "steering must start coming back toward centre"
    assert seen == sorted(seen, reverse=True), "and keep decaying"
    assert seen[-1] < 0.5


def test_steering_reaches_centre_and_stays():
    lf = make_follower()
    lf.steering = 0.9
    for _ in range(60):
        lf.run(blank_image())
    assert lf.steering == 0.0


def test_decay_of_one_restores_the_old_hold_behaviour():
    """Left configurable so anyone relying on the old behaviour can keep it."""

    class HoldCfg(Cfg):
        LOST_LINE_STEERING_DECAY = 1.0

    lf = make_follower(cfg=HoldCfg())
    lf.steering = 0.9
    for _ in range(5):
        lf.run(blank_image())
    assert lf.steering == pytest.approx(0.9)


def test_lost_loop_counter_resets_when_the_line_returns():
    lf = make_follower()
    for _ in range(3):
        lf.run(blank_image())
    assert lf.loops_since_line == 3

    lf.run(make_image(80))
    assert lf.loops_since_line == 0
    assert lf.line_detected is True


def test_a_seen_line_still_steers_normally():
    """The decay must not touch the normal path."""
    lf = make_follower()
    img = make_image(Cfg.TARGET_PIXEL)
    lf.run(img, 30)
    first = lf.steering
    lf.run(img, 30)
    assert lf.steering == pytest.approx(first, abs=0.2)
    assert lf.line_detected is True


def test_older_configs_declaring_three_outputs_still_work():
    """
    Memory.put assigns by position, so a config that names only the original
    three outputs keeps working against the five returned.
    """
    from donkeycar.memory import Memory

    lf = make_follower()
    outputs = lf.run(make_image(80))
    mem = Memory()
    mem.put(["pilot/steering", "pilot/throttle", "cv/image_array"], outputs)
    assert mem.get(["pilot/steering"])[0] == outputs[0]
    assert mem.get(["cv/image_array"])[0] is outputs[2]
