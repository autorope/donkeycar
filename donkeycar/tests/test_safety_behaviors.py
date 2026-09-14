#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import (
    ESTOP_NEUTRAL_THROTTLE,
    ChaosMonkey,
    EmergencyStop,
    StopVehicle,
)


class FakeVehicle:
    def __init__(self) -> None:
        self.on = True


def run_to_completion(estop: EmergencyStop, scale: float = 1.0) -> list[float]:
    """
    Every throttle the stop asks for, from the press until it is done.
    """
    throttles = [estop.run(estop_event=1.0, throttle_scale=scale)[0]]
    while estop.stopping:
        throttles.append(estop.run(throttle_scale=scale)[0])
    return throttles


class TestEmergencyStop(unittest.TestCase):

    def test_it_passes_everything_through_when_idle(self):
        throttle, mode, recording, stopping = EmergencyStop().run(
            None, 0.5, 1.0, 'local', True
        )

        assert throttle == 0.5
        assert mode == 'local'
        assert recording is True
        assert stopping is False

    def test_the_event_starts_the_stop(self):
        estop = EmergencyStop()
        assert estop.stopping is False

        estop.run(estop_event=1.0, throttle_scale=1.0)
        assert estop.stopping is True

    def test_it_sends_reverse_neutral_reverse(self):
        """
        Many RC speed controllers read a single reverse request as brake
        and only engage reverse on a second one, so one full-reverse pulse
        would slow the car rather than stopping it.
        """
        estop = EmergencyStop()
        sequence = run_to_completion(estop, scale=1.0)

        assert sequence[0] == -1.0
        assert sequence[1] == ESTOP_NEUTRAL_THROTTLE
        assert sequence[2] == -1.0

    def test_it_winds_back_up_to_zero(self):
        """
        Otherwise the car is left sitting in reverse once it has stopped.
        """
        estop = EmergencyStop(recovery_step=0.25)
        sequence = run_to_completion(estop, scale=1.0)

        assert sequence[-1] == 0.0
        assert estop.stopping is False

    def test_the_wind_up_is_gradual(self):
        estop = EmergencyStop(recovery_step=0.25)
        sequence = run_to_completion(estop, scale=1.0)

        # after the second reverse pulse, back up in steps
        assert sequence[3:] == [-0.75, -0.5, -0.25, 0.0]

    def test_the_whole_sequence_matches_the_legacy_one(self):
        """
        Every throttle the legacy four-state machine produced, in order, at
        full scale and the default recovery step.  How hard a car brakes is
        not something to change while moving it into a part.
        """
        estop = EmergencyStop()
        sequence = [round(v, 4) for v in run_to_completion(estop, scale=1.0)]

        assert sequence == [
            -1.0, 0.01, -1.0,
            -0.95, -0.9, -0.85, -0.8, -0.75, -0.7, -0.65, -0.6, -0.55,
            -0.5, -0.45, -0.4, -0.35, -0.3, -0.25, -0.2, -0.15, -0.1,
            -0.05, 0.0,
        ]

    def test_it_uses_the_throttle_limit_for_the_reverse_pulse(self):
        """
        A car limited to a quarter throttle cannot brake at full reverse.
        """
        estop = EmergencyStop()
        sequence = run_to_completion(estop, scale=0.25)

        assert sequence[0] == -0.25
        assert sequence[2] == -0.25

    def test_it_drops_back_to_manual(self):
        """
        Whatever the pilot was doing is the thing being stopped.
        """
        _, mode, _, _ = EmergencyStop().run(
            estop_event=1.0, mode='local', throttle_scale=1.0
        )
        assert mode == 'user'

    def test_it_stops_recording(self):
        """
        A recording of an emergency is not training data.
        """
        _, _, recording, _ = EmergencyStop().run(
            estop_event=1.0, recording=True, throttle_scale=1.0
        )
        assert recording is False

    def test_it_overrides_the_throttle_while_stopping(self):
        estop = EmergencyStop()
        estop.run(estop_event=1.0, throttle_scale=1.0)

        throttle, _, _, _ = estop.run(throttle=0.9, throttle_scale=1.0)
        assert throttle != 0.9

    def test_pressing_again_mid_stop_does_not_restart_it(self):
        """
        A frightened driver presses more than once.  Restarting would send
        the car through another reverse pulse each time and never finish.
        """
        estop = EmergencyStop(recovery_step=0.25)
        estop.run(estop_event=1.0, throttle_scale=1.0)

        stages = []
        for _ in range(3):
            stages.append(estop.run(estop_event=1.0, throttle_scale=1.0)[0])

        assert stages == [ESTOP_NEUTRAL_THROTTLE, -1.0, -0.75]

    def test_it_can_be_used_again_afterwards(self):
        estop = EmergencyStop(recovery_step=0.5)
        run_to_completion(estop, scale=1.0)

        assert estop.stopping is False
        assert estop.run(estop_event=1.0, throttle_scale=1.0)[0] == -1.0

    def test_no_throttle_limit_set_yet_uses_the_default(self):
        estop = EmergencyStop(default_scale=0.5)
        assert estop.run(estop_event=1.0)[0] == -0.5

    def test_nothing_set_yet_is_not_a_crash(self):
        throttle, mode, recording, stopping = EmergencyStop().run()

        assert throttle == 0.0
        assert mode == 'user'
        assert recording is False
        assert stopping is False


class TestChaosMonkey(unittest.TestCase):

    def test_it_pulls_the_steering_while_held(self):
        assert ChaosMonkey(0.2).run(1, 0.0) == 0.2
        assert ChaosMonkey(-0.2).run(1, 0.0) == -0.2

    def test_it_overrides_the_driver(self):
        assert ChaosMonkey(0.2).run(1, -0.9) == 0.2

    def test_releasing_gives_the_steering_back(self):
        monkey = ChaosMonkey(0.2)

        assert monkey.run(1, -0.9) == 0.2
        assert monkey.run(0, -0.9) == -0.9

    def test_it_passes_the_steering_through_when_not_held(self):
        assert ChaosMonkey().run(0, 0.5) == 0.5

    def test_nothing_set_yet_is_centred(self):
        assert ChaosMonkey().run(None, None) == 0.0
        assert ChaosMonkey().run() == 0.0

    def test_two_of_them_make_a_left_and_a_right(self):
        """
        How it is bound: one part per shoulder button, opposite signs.
        """
        left = ChaosMonkey(-0.2)
        right = ChaosMonkey(0.2)

        assert left.run(1, 0.0) == -0.2
        assert right.run(1, 0.0) == 0.2


class TestStopVehicle(unittest.TestCase):

    def test_it_stops_the_vehicle(self):
        vehicle = FakeVehicle()
        StopVehicle(vehicle).run()

        assert vehicle.on is False

    def test_the_modifier_has_to_be_held(self):
        """
        The gesture is a click on one button while another is held, so that
        stopping the car cannot happen by accident.
        """
        vehicle = FakeVehicle()
        StopVehicle(vehicle).run(modifier_state=0)

        assert vehicle.on is True

    def test_holding_the_modifier_completes_the_gesture(self):
        vehicle = FakeVehicle()
        StopVehicle(vehicle).run(modifier_state=1)

        assert vehicle.on is False

    def test_no_modifier_at_all_just_stops(self):
        """
        A template that wants a single button, not a gesture, binds no
        input.
        """
        vehicle = FakeVehicle()
        StopVehicle(vehicle).run(None)

        assert vehicle.on is False

    def test_no_vehicle_is_not_a_crash(self):
        StopVehicle(None).run()  # must not raise
