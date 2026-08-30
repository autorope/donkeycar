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
    CONFIDENCE_THRESHOLD = 0.15
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
    assert isinstance(max_yellow, int)
    # Confidence is a fraction of the scan column, not a raw sum of mask values.
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


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


# --------------------------------------------- the gate that could not reject


def test_confidence_is_a_fraction_of_the_scan_column():
    """
    A full column of tape scores 1.0, half scores 0.5. It used to be the raw sum
    of mask values -- 255 per pixel -- while the threshold was documented as a
    fraction, so the two were never comparable.
    """
    lf = make_follower()
    full = np.zeros((IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
    full[:, 150:160] = (255, 255, 0)  # tape spanning the whole band
    _, conf, _ = lf.get_i_color(full)
    assert conf == pytest.approx(1.0, abs=0.05)

    half = np.zeros((IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
    half[SCAN_Y : SCAN_Y + Cfg.SCAN_HEIGHT // 2, 150:160] = (255, 255, 0)
    _, conf, _ = lf.get_i_color(half)
    assert conf == pytest.approx(0.5, abs=0.05)


def test_a_speck_no_longer_counts_as_a_line():
    """
    The failure this fixes: ten matching pixels at the edge of the frame were
    treated as a confident detection, the PID chased them, steering saturated
    and the car drove off the course. 255 >= 0.0015 was always true.
    """
    lf = make_follower()
    speck = np.zeros((IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
    # one row of a ten-row band, at the right-hand edge
    speck[SCAN_Y : SCAN_Y + 1, IMAGE_W - 15 : IMAGE_W - 8] = (255, 255, 0)

    _, _, _, conf, seen = lf.run(speck)
    assert conf == pytest.approx(1 / Cfg.SCAN_HEIGHT, abs=0.02)
    assert seen is False, "a one-row speck must not read as a detected line"


def test_a_real_line_still_passes_the_gate():
    lf = make_follower()
    _, _, _, conf, seen = lf.run(make_image(150))
    assert seen is True
    assert conf > Cfg.CONFIDENCE_THRESHOLD


def test_an_old_style_threshold_leaves_the_gate_open():
    """
    Someone upgrading still has 0.0015 in their config. Under the new units that
    is a very low bar, so they keep the behaviour they had rather than suddenly
    getting `No line detected` everywhere. It is a migration, not a trap.
    """

    class OldCfg(Cfg):
        CONFIDENCE_THRESHOLD = 0.0015

    lf = make_follower(cfg=OldCfg())
    speck = np.zeros((IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
    speck[SCAN_Y : SCAN_Y + 1, IMAGE_W - 15 : IMAGE_W - 8] = (255, 255, 0)
    _, _, _, _, seen = lf.run(speck)
    assert seen is True, "old configs should behave as they did before"


def test_confidence_is_independent_of_image_width():
    """
    Expressing it per column rather than per frame means a wider camera does not
    silently change what the threshold means.
    """
    half = Cfg.SCAN_HEIGHT // 2
    for width in (160, 640):
        lf = make_follower()
        img = np.zeros((IMAGE_H, width, 3), dtype=np.uint8)
        img[SCAN_Y : SCAN_Y + half, width // 2 - 5 : width // 2 + 5] = (255, 255, 0)
        _, conf, _ = lf.get_i_color(img)
        assert conf == pytest.approx(0.5, abs=0.05), width


# ------------------------------------------------------------ steering limits


def test_steering_never_leaves_the_commanded_range():
    """
    Steering is a -1..1 command. Observed on a real car as 1.28, which the
    drivetrain silently clamped -- so the agent was told a number the actuator
    could not deliver.
    """
    lf = make_follower()
    # a line hard against one edge, far from the target
    img = make_image(IMAGE_W - 3)
    for _ in range(30):
        steering, _, _, _, _ = lf.run(img)
        assert -1.0 <= steering <= 1.0, steering


def test_the_pid_is_given_output_limits():
    lf = make_follower()
    assert lf.pid_st.output_limits == (-1.0, 1.0)


def test_limits_the_caller_configured_are_left_alone():
    """A caller supplying its own limits knows something we do not."""
    pid = PID(Kp=-0.01, Ki=0.0, Kd=0.0, output_limits=(-0.5, 0.5))
    lf = LineFollower(pid, Cfg())
    assert lf.pid_st.output_limits == (-0.5, 0.5)


def test_output_limits_matter_only_when_there_is_an_integral():
    """
    The clamp is what this change actually buys with the stock config, since
    donkeycar ships PID_I = 0.000 and there is then no integral to wind up.
    The limits are still worth setting: they are anti-windup for anyone who
    does configure PID_I, and they stop the PID reporting a command the servo
    cannot deliver.

    Kp is deliberately large here: with the test frame only IMAGE_W wide, the
    stock -0.01 cannot produce an output beyond 0.8, so it would never saturate
    and the test would prove nothing.
    """
    # sample_time=None so every call recomputes; otherwise simple_pid returns
    # its cached output for calls inside one sample window and nothing moves.
    pid = PID(Kp=-0.05, Ki=0.0, Kd=0.0, sample_time=None)
    lf = LineFollower(pid, Cfg())
    assert lf.pid_st.output_limits == (-1.0, 1.0)

    hard_over = make_image(IMAGE_W - 3)
    for _ in range(40):
        steering, _, _, _, _ = lf.run(hard_over)
        assert -1.0 <= steering <= 1.0

    assert steering == pytest.approx(1.0), "expected the controller to be saturated"

    # back on target it should come straight back, not grind down from a
    # wound-up accumulator
    first = lf.run(make_image(Cfg.TARGET_PIXEL))[0]
    assert abs(first) < 0.2, f"recovery started at {first}"


# --------------------------------------------------- auto-latched target pixel


class AutoCfg(Cfg):
    """TARGET_PIXEL unset, so the follower latches it from what it sees."""

    TARGET_PIXEL = None


def make_speck_image(column, lit_rows=1):
    """
    A frame with too little yellow to count as a line: a short stub, the way a
    reflection or a distant scrap of tape shows up in the scan band.

    One row of ten scores 0.10 against the 0.15 gate -- deliberately close, and
    the same margin the real car produced when it latched onto a reflection.
    """
    img = np.zeros((IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
    img[SCAN_Y : SCAN_Y + lit_rows, column : column + 3] = (255, 255, 0)
    return img


def test_a_speck_does_not_become_the_target():
    """
    Regression: the target used to be latched from the first frame outright,
    before the confidence gate had any say. A car started while looking away
    from the tape anchored itself to the argmax of an empty scan band -- seen on
    a real car as a reflection at column 18, scored 0.087 against a threshold of
    0.15, becoming the place it spent the rest of the run steering toward.
    """
    lf = make_follower(AutoCfg())
    _steering, _throttle, _img, confidence, detected = lf.run(make_speck_image(18))

    assert not detected, "the speck should not read as a line, or this proves nothing"
    assert confidence < AutoCfg.CONFIDENCE_THRESHOLD
    assert lf.target_pixel is None, "an unconfident frame must not latch the target"
    assert lf.effective_target_pixel == IMAGE_W // 2, "with no line yet, steer to the middle"


def test_the_target_latches_on_the_first_real_line():
    lf = make_follower(AutoCfg())
    lf.run(make_speck_image(18))
    assert lf.target_pixel is None

    lf.run(make_image(120))
    assert lf.target_pixel is not None
    assert abs(lf.target_pixel - 120) <= 3, "the target should latch to the real line"


def test_a_lane_offset_applies_before_any_line_is_seen():
    """A requested offset must still be honoured against the fallback centre."""
    lf = make_follower(AutoCfg())
    lf.run(make_speck_image(18), -21)
    assert lf.effective_target_pixel == IMAGE_W // 2 - 21
