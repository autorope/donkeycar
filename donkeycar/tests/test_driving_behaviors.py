#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import (
    DEFAULT_DEAD_ZONE,
    TriggerThrottle,
    UserSteering,
    UserThrottle,
    apply_dead_zone,
)


class TestUserSteering(unittest.TestCase):

    def test_it_passes_the_control_through(self):
        assert UserSteering().run(0.5) == 0.5

    def test_scale_limits_the_travel(self):
        assert UserSteering(scale=0.5).run(1.0) == 0.5
        assert UserSteering(scale=0.5).run(-1.0) == -0.5

    def test_invert_swaps_left_and_right(self):
        assert UserSteering(invert=True).run(0.5) == -0.5

    def test_nothing_yet_is_centred(self):
        """
        Before the control has moved there is no value in memory for it.
        """
        assert UserSteering().run(None) == 0.0
        assert UserSteering().run() == 0.0

    def test_the_dead_zone_is_applied_by_default(self):
        """
        The legacy controller applied JOYSTICK_DEADZONE only to whether to
        record, never to steering, so a resting stick steered the car.
        """
        assert UserSteering().run(DEFAULT_DEAD_ZONE / 2) == 0.0
        assert UserSteering().run(0.5) == 0.5

    def test_the_dead_zone_can_be_turned_off(self):
        assert UserSteering(dead_zone=0.0).run(0.002) == 0.002

    def test_the_dead_zone_ignores_a_resting_stick(self):
        steering = UserSteering(dead_zone=0.1)

        assert steering.run(0.08) == 0.0
        assert steering.run(-0.08) == 0.0
        assert steering.run(0.5) == 0.5


class TestUserThrottle(unittest.TestCase):

    def test_the_default_direction_turns_forward_into_positive(self):
        """
        A stick pushed away usually reads negative, so the default
        direction of -1.0 makes pushing away mean forwards.
        """
        assert UserThrottle().run(-1.0) == 1.0
        assert UserThrottle().run(1.0) == -1.0

    def test_direction_can_be_left_alone(self):
        assert UserThrottle(direction=1.0).run(1.0) == 1.0

    def test_scale_limits_the_throttle(self):
        assert UserThrottle(direction=1.0, scale=0.5).run(1.0) == 0.5

    def test_nothing_yet_is_no_throttle(self):
        assert UserThrottle().run(None) == 0.0
        assert UserThrottle().run() == 0.0

    def test_the_scale_can_be_changed_while_driving(self):
        """
        AdjustMaxThrottle writes user/throttle_scale, which arrives here as
        an input, so the limit can be raised or lowered on the move.
        """
        throttle = UserThrottle(direction=1.0, scale=1.0)

        assert throttle.run(1.0, 0.25) == 0.25
        assert throttle.run(1.0, 0.75) == 0.75

    def test_no_scale_input_falls_back_to_the_constructor(self):
        throttle = UserThrottle(direction=1.0, scale=0.4)
        assert throttle.run(1.0, None) == 0.4

    def test_the_dead_zone_is_applied_by_default(self):
        assert UserThrottle(direction=1.0).run(DEFAULT_DEAD_ZONE / 2) == 0.0

    def test_the_dead_zone_ignores_a_resting_stick(self):
        throttle = UserThrottle(direction=1.0, dead_zone=0.1)

        assert throttle.run(0.08) == 0.0
        assert throttle.run(0.5) == 0.5


class TestTriggerThrottle(unittest.TestCase):
    """
    Forza mode: one trigger for forward, one for reverse.  This never ran
    in the legacy code -- it was bound to axis names that mapped to codes
    the driver does not send -- so there is no old behavior to preserve,
    only correct behavior to establish.
    """

    def test_untouched_triggers_give_no_throttle(self):
        """
        The safety case.  A trigger rests at -1.0 and has no value in memory
        until it first moves; reading that absence as centre would mean half
        throttle the moment the car started.
        """
        assert TriggerThrottle().run(None, None) == 0.0
        assert TriggerThrottle().run() == 0.0

    def test_a_released_trigger_gives_no_throttle(self):
        assert TriggerThrottle().run(-1.0, -1.0) == 0.0

    def test_the_forward_trigger_drives_forward(self):
        assert TriggerThrottle().run(1.0, -1.0) == 1.0

    def test_the_reverse_trigger_drives_backward(self):
        assert TriggerThrottle().run(-1.0, 1.0) == -1.0

    def test_a_half_squeeze_gives_half_throttle(self):
        assert TriggerThrottle().run(0.0, -1.0) == 0.5

    def test_scale_limits_the_throttle(self):
        assert TriggerThrottle(scale=0.5).run(1.0, -1.0) == 0.5

    def test_the_scale_can_be_changed_while_driving(self):
        assert TriggerThrottle(scale=1.0).run(1.0, -1.0, 0.25) == 0.25

    def test_squeezing_both_cancels_out(self):
        """
        The legacy version bound each trigger to its own handler writing the
        throttle in turn, so whichever moved last won outright: holding
        forward and brushing reverse gave full reverse.  Reading an
        ambiguous request as "no request" is the sensible answer.
        """
        assert TriggerThrottle().run(1.0, 1.0) == 0.0

    def test_partly_squeezing_both_gives_the_difference(self):
        assert TriggerThrottle().run(1.0, 0.0) == 0.5

    def test_a_trigger_beyond_its_travel_is_clamped(self):
        assert TriggerThrottle().run(2.0, -1.0) == 1.0
        assert TriggerThrottle().run(-2.0, -1.0) == 0.0

    def test_the_dead_zone_ignores_a_resting_trigger(self):
        throttle = TriggerThrottle(dead_zone=0.1)

        # -0.9 is 5% squeezed, which is a trigger sitting against its stop
        assert throttle.run(-0.9, -1.0) == 0.0
        assert throttle.run(0.0, -1.0) == 0.5


class TestDeadZone(unittest.TestCase):

    def test_zero_dead_zone_changes_nothing(self):
        assert apply_dead_zone(0.001, 0.0) == 0.001

    def test_a_reading_inside_the_zone_is_centred(self):
        assert apply_dead_zone(0.05, 0.1) == 0.0
        assert apply_dead_zone(-0.05, 0.1) == 0.0

    def test_a_reading_outside_the_zone_is_untouched(self):
        assert apply_dead_zone(0.5, 0.1) == 0.5
        assert apply_dead_zone(-0.5, 0.1) == -0.5

    def test_the_boundary_counts_as_outside(self):
        assert apply_dead_zone(0.1, 0.1) == 0.1


class TestTheMeasuredPad(unittest.TestCase):
    """
    Using the values actually measured on the Xbox pad, since that is what
    these parts will be fed.
    """

    def test_a_resting_trigger_reads_as_no_throttle(self):
        """
        Measured: right_trigger sits at -1.0 until squeezed.
        """
        assert TriggerThrottle().run(-1.0, -1.0) == 0.0

    def test_the_default_dead_zone_is_too_small_for_this_pad(self):
        """
        Measured: the resting sticks produced readings of 0.048, 0.068 and
        0.099, all well past the shipped 0.01.  So the default keeps a car
        from drifting on a tidy pad but not on this one, and a car whose
        sticks idle this far out needs JOYSTICK_DEADZONE raised.
        """
        steering = UserSteering()
        for jitter in (0.048, 0.068, 0.099):
            assert steering.run(jitter) != 0.0

        steering = UserSteering(dead_zone=0.1)
        for jitter in (0.048, 0.068, 0.099):
            assert steering.run(jitter) == 0.0
