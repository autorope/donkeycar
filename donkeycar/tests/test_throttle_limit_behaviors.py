#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import (
    DEFAULT_THROTTLE_STEP,
    AdjustMaxThrottle,
    ConstantThrottle,
    ToggleConstantThrottle,
    UserThrottle,
)


class TestAdjustMaxThrottle(unittest.TestCase):

    def test_a_positive_step_raises_the_limit(self):
        assert AdjustMaxThrottle(step=0.1).run(0.5) == 0.6

    def test_a_negative_step_lowers_the_limit(self):
        assert AdjustMaxThrottle(step=-0.1).run(0.5) == 0.4

    def test_the_limit_cannot_go_above_full(self):
        assert AdjustMaxThrottle(step=0.1).run(1.0) == 1.0

    def test_the_limit_cannot_go_below_nothing(self):
        """
        A negative limit would invert the throttle, so pushing forward
        would drive the car backwards.
        """
        assert AdjustMaxThrottle(step=-0.1).run(0.0) == 0.0
        assert AdjustMaxThrottle(step=-0.5).run(0.2) == 0.0

    def test_repeated_steps_do_not_accumulate_float_error(self):
        """
        Without rounding, thirty steps of 0.01 leave the limit reading
        0.7300000000000001, which then shows up in logs and the web UI.
        """
        adjust = AdjustMaxThrottle(step=DEFAULT_THROTTLE_STEP)
        scale = 0.5
        for _ in range(30):
            scale = adjust.run(scale)

        assert scale == 0.8

    def test_it_steps_from_whatever_the_limit_actually_is(self):
        """
        The limit is in memory, not held here, so the web interface or a
        config reload can change it and this steps on from there.
        """
        adjust = AdjustMaxThrottle(step=0.1)

        assert adjust.run(0.2) == 0.3
        assert adjust.run(0.9) == 1.0

    def test_no_limit_set_yet_starts_from_the_default(self):
        assert AdjustMaxThrottle(step=-0.1, default_scale=1.0).run(None) == 0.9
        assert AdjustMaxThrottle(step=-0.1, default_scale=1.0).run() == 0.9

    def test_the_default_step_matches_the_legacy_one(self):
        assert DEFAULT_THROTTLE_STEP == 0.01


class TestToggleConstantThrottle(unittest.TestCase):

    def test_it_flips(self):
        assert ToggleConstantThrottle().run(False) is True
        assert ToggleConstantThrottle().run(True) is False

    def test_nothing_set_yet_turns_it_on(self):
        assert ToggleConstantThrottle().run(None) is True
        assert ToggleConstantThrottle().run() is True

    def test_it_reads_the_value_rather_than_remembering_it(self):
        toggle = ToggleConstantThrottle()

        assert toggle.run(True) is False
        assert toggle.run(True) is False


class TestConstantThrottle(unittest.TestCase):

    def test_off_passes_the_control_through(self):
        assert ConstantThrottle().run(False, 0.5, 0.3) == 0.3

    def test_on_holds_the_throttle_at_the_limit(self):
        assert ConstantThrottle().run(True, 0.5, 0.0) == 0.5

    def test_on_ignores_the_control(self):
        assert ConstantThrottle().run(True, 0.5, 0.9) == 0.5

    def test_the_limit_sets_the_speed_it_holds(self):
        """
        So the same buttons that trim the limit also set the speed on a car
        driven this way.
        """
        constant = ConstantThrottle()

        assert constant.run(True, 0.25, 0.0) == 0.25
        assert constant.run(True, 0.75, 0.0) == 0.75

    def test_turning_it_off_stops_rather_than_lurching(self):
        """
        A driver who has not touched the throttle for a lap has it resting
        at zero, but the value in memory is whatever it last was.  Handing
        that back would be a surprise at speed.
        """
        constant = ConstantThrottle()
        assert constant.run(True, 0.5, 0.0) == 0.5

        assert constant.run(False, 0.5, 0.9) == 0.0

    def test_the_control_takes_over_again_afterwards(self):
        constant = ConstantThrottle()
        constant.run(True, 0.5, 0.0)
        constant.run(False, 0.5, 0.9)

        assert constant.run(False, 0.5, 0.3) == 0.3

    def test_it_does_not_stop_a_car_that_was_never_holding(self):
        """
        Only a car coming out of constant throttle is stopped; one that was
        never in it keeps driving normally.
        """
        constant = ConstantThrottle()

        assert constant.run(False, 0.5, 0.4) == 0.4
        assert constant.run(False, 0.5, 0.4) == 0.4

    def test_nothing_set_yet_is_off(self):
        assert ConstantThrottle().run(None, None, None) == 0.0
        assert ConstantThrottle().run() == 0.0

    def test_no_limit_set_yet_uses_the_default(self):
        assert ConstantThrottle(default_scale=0.6).run(True, None, 0.0) == 0.6


class TestTheLimitReachesTheThrottle(unittest.TestCase):
    """
    AdjustMaxThrottle writes user/throttle_scale and UserThrottle reads it,
    which is what replaces the shared mutable field the legacy controller
    used.  These check the two ends actually meet.
    """

    def test_lowering_the_limit_lowers_the_throttle(self):
        throttle = UserThrottle(direction=1.0, scale=1.0)
        adjust = AdjustMaxThrottle(step=-0.5)

        assert throttle.run(1.0, 1.0) == 1.0

        lowered = adjust.run(1.0)
        assert throttle.run(1.0, lowered) == 0.5

    def test_the_limit_does_not_change_the_direction(self):
        throttle = UserThrottle(direction=-1.0, scale=1.0)
        assert throttle.run(-1.0, 0.5) == 0.5

    def test_a_zero_limit_stops_the_car(self):
        throttle = UserThrottle(direction=1.0, scale=1.0)
        assert throttle.run(1.0, 0.0) == 0.0
