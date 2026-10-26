#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import (
    ESTOP_NEUTRAL_THROTTLE,
    AxisChord,
    ChaosMonkey,
    EmergencyStop,
    StopVehicle,
)


class FakeVehicle:
    def __init__(self) -> None:
        self.on = True


class FakeClock:
    """
    Seconds that only move when a test moves them.
    """

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def drive_at(estop: EmergencyStop, throttle: float) -> None:
    """
    One pass with the drivetrain at this throttle and no stop pressed.
    """
    estop.run(drive_throttle=throttle)


def run_to_completion(estop: EmergencyStop) -> list[float]:
    """
    Every throttle the stop asks for, from the press until it is done.
    """
    throttles = [estop.run(estop_event=1.0)[0]]
    while estop.stopping:
        throttles.append(estop.run()[0])
    return throttles


def braking_from(throttle: float, **kwargs) -> list[float]:
    """
    The stop's sequence after one pass driven at this throttle.
    """
    estop = EmergencyStop(clock=FakeClock(), **kwargs)
    drive_at(estop, throttle)
    return [round(v, 4) for v in run_to_completion(estop)]


class TestEmergencyStop(unittest.TestCase):

    def test_it_passes_everything_through_when_idle(self):
        throttle, mode, recording, stopping = EmergencyStop().run(
            None, 0.5, 'local', True
        )

        assert throttle == 0.5
        assert mode == 'local'
        assert recording is True
        assert stopping is False

    def test_the_event_starts_the_stop(self):
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, 0.5)
        assert estop.stopping is False

        estop.run(estop_event=1.0)
        assert estop.stopping is True

    def test_it_sends_reverse_neutral_reverse(self):
        """
        Many RC speed controllers read a single reverse request as brake
        and only engage reverse on a second one, so one reverse pulse would
        slow the car rather than stopping it.
        """
        sequence = braking_from(1.0)

        assert sequence[0] == -1.0
        assert sequence[1] == ESTOP_NEUTRAL_THROTTLE
        assert sequence[2] == -1.0

    def test_it_winds_back_up_to_zero(self):
        """
        Otherwise the car is left sitting in reverse once it has stopped.
        """
        estop = EmergencyStop(recovery_step=0.25, clock=FakeClock())
        drive_at(estop, 1.0)
        sequence = run_to_completion(estop)

        assert sequence[-1] == 0.0
        assert estop.stopping is False

    def test_the_wind_up_is_gradual(self):
        sequence = braking_from(1.0, recovery_step=0.25)

        # after the second reverse pulse, back up in steps
        assert sequence[3:] == [-0.75, -0.5, -0.25, 0.0]

    def test_braking_from_full_throttle_matches_the_legacy_sequence(self):
        """
        Every throttle the legacy four-state machine produced, in order, at
        full scale and the default recovery step.  A car stopped from full
        throttle brakes exactly as it always did.
        """
        assert braking_from(1.0) == [
            -1.0, 0.01, -1.0,
            -0.95, -0.9, -0.85, -0.8, -0.75, -0.7, -0.65, -0.6, -0.55,
            -0.5, -0.45, -0.4, -0.35, -0.3, -0.25, -0.2, -0.15, -0.1,
            -0.05, 0.0,
        ]

    def test_it_brakes_as_hard_as_the_car_was_driven(self):
        sequence = braking_from(0.5)

        assert sequence[:3] == [-0.5, ESTOP_NEUTRAL_THROTTLE, -0.5]
        assert sequence[3] == -0.45
        assert min(sequence) == -0.5

    def test_a_car_that_never_moved_gets_no_reverse(self):
        """
        Found on hardware: wheels off the ground at zero throttle, the
        stop's reverse pulses spun the motor, because that car's ESC drives
        reverse directly rather than braking.
        """
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, 0.0)

        throttle, mode, recording, stopping = estop.run(
            estop_event=1.0, mode='local', recording=True)

        assert throttle == 0.0
        assert mode == 'user'
        assert recording is False
        assert stopping is True
        assert estop.stopping is False

    def test_the_brake_fades_while_the_car_coasts(self):
        """
        A fast car keeps rolling after the throttle is released, so the
        brake fades over the coast time rather than vanishing at once.
        """
        clock = FakeClock()
        estop = EmergencyStop(coast_time=1.0, clock=clock)
        drive_at(estop, 0.5)
        clock.now += 0.5
        drive_at(estop, 0.0)

        assert estop.run(estop_event=1.0)[0] == -0.25

    def test_after_the_coast_time_there_is_nothing_to_brake(self):
        clock = FakeClock()
        estop = EmergencyStop(coast_time=1.0, clock=clock)
        drive_at(estop, 0.5)
        clock.now += 1.5
        drive_at(estop, 0.0)

        assert run_to_completion(estop) == [0.0]

    def test_easing_off_fades_from_the_peak(self):
        """
        Dropping from full throttle to a little does not stop the car at
        once either, so the brake follows the fading peak while that is
        higher than the throttle now.
        """
        clock = FakeClock()
        estop = EmergencyStop(coast_time=1.0, clock=clock)
        drive_at(estop, 1.0)
        clock.now += 0.5
        drive_at(estop, 0.2)

        assert estop.run(estop_event=1.0)[0] == -0.5

    def test_steady_driving_keeps_the_brake_at_the_throttle(self):
        clock = FakeClock()
        estop = EmergencyStop(coast_time=1.0, clock=clock)
        for _ in range(30):
            drive_at(estop, 0.4)
            clock.now += 0.1

        # the pass with the press still carries the drivetrain's throttle
        assert estop.run(estop_event=1.0, drive_throttle=0.4)[0] == -0.4

    def test_the_pilots_throttle_counts(self):
        """
        Under the pilot the user's throttle is zero while the car drives,
        so the stop reads what the drivetrain was given.
        """
        estop = EmergencyStop(clock=FakeClock())
        estop.run(throttle=0.0, drive_throttle=0.6)

        assert estop.run(estop_event=1.0, throttle=0.0)[0] == -0.6

    def test_without_the_drivetrain_throttle_it_uses_the_users(self):
        estop = EmergencyStop(clock=FakeClock())
        estop.run(throttle=0.3)

        assert estop.run(estop_event=1.0, throttle=0.3)[0] == -0.3

    def test_a_car_driving_backwards_gets_no_brake_pulse(self):
        """
        Legacy did not brake reverse either; a forward pulse would be a
        lurch towards whatever is in front.
        """
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, -0.5)

        assert run_to_completion(estop) == [0.0]

    def test_it_drops_back_to_manual(self):
        """
        Whatever the pilot was doing is the thing being stopped.
        """
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, 0.5)

        _, mode, _, _ = estop.run(estop_event=1.0, mode='local')
        assert mode == 'user'

    def test_it_stops_recording(self):
        """
        A recording of an emergency is not training data.
        """
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, 0.5)

        _, _, recording, _ = estop.run(estop_event=1.0, recording=True)
        assert recording is False

    def test_it_overrides_the_throttle_while_stopping(self):
        estop = EmergencyStop(clock=FakeClock())
        drive_at(estop, 0.5)
        estop.run(estop_event=1.0)

        throttle, _, _, _ = estop.run(throttle=0.9, drive_throttle=0.9)
        assert throttle != 0.9

    def test_pressing_again_mid_stop_does_not_restart_it(self):
        """
        A frightened driver presses more than once.  Restarting would send
        the car through another reverse pulse each time and never finish.
        """
        estop = EmergencyStop(recovery_step=0.25, clock=FakeClock())
        drive_at(estop, 1.0)
        estop.run(estop_event=1.0)

        stages = []
        for _ in range(3):
            stages.append(estop.run(estop_event=1.0)[0])

        assert stages == [ESTOP_NEUTRAL_THROTTLE, -1.0, -0.75]

    def test_a_second_stop_does_not_brake_for_the_first_drive(self):
        """
        The first stop brought the car to rest, so pressing again straight
        afterwards has nothing to brake.
        """
        estop = EmergencyStop(recovery_step=0.5, clock=FakeClock())
        drive_at(estop, 1.0)
        run_to_completion(estop)

        assert run_to_completion(estop) == [0.0]

    def test_it_can_be_used_again_afterwards(self):
        estop = EmergencyStop(recovery_step=0.5, clock=FakeClock())
        drive_at(estop, 1.0)
        run_to_completion(estop)
        drive_at(estop, 1.0)

        assert estop.run(estop_event=1.0)[0] == -1.0

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


class TestAxisChord(unittest.TestCase):
    """
    Both triggers squeezed, as the stop gesture for a pad whose spare
    controls are axes.  Triggers rest at -1.0 and are fully in at +1.0.
    """

    def test_fires_when_both_are_squeezed(self):
        assert AxisChord().run(1.0, 1.0) is True

    def test_one_alone_is_not_enough(self):
        chord = AxisChord()

        assert chord.run(1.0, -1.0) is False
        assert chord.run(-1.0, 1.0) is False

    def test_either_order(self):
        """
        Squeezed together, either trigger may cross first.  A button-style
        modifier would only fire if the modifier went in first.
        """
        left_first = AxisChord()
        assert left_first.run(1.0, -1.0) is False
        assert left_first.run(1.0, 1.0) is True

        right_first = AxisChord()
        assert right_first.run(-1.0, 1.0) is False
        assert right_first.run(1.0, 1.0) is True

    def test_fires_once_while_held(self):
        """
        StopVehicle cannot be undone, but firing it every pass while the
        triggers are held would still be wrong for any other use.
        """
        chord = AxisChord()

        assert chord.run(1.0, 1.0) is True
        assert chord.run(1.0, 1.0) is False
        assert chord.run(0.9, 1.0) is False

    def test_letting_one_go_rearms_it(self):
        chord = AxisChord()

        assert chord.run(1.0, 1.0) is True
        assert chord.run(-1.0, 1.0) is False
        assert chord.run(1.0, 1.0) is True

    def test_a_partial_squeeze_does_not_count(self):
        """
        0.6 is 80% of a trigger's travel from rest.
        """
        assert AxisChord().run(0.5, 1.0) is False
        assert AxisChord().run(0.6, 1.0) is True

    def test_released_triggers_are_not_squeezed(self):
        """
        A released trigger reads -1.0, which is truthy.  That is the trap
        this part exists to avoid.
        """
        assert AxisChord().run(-1.0, -1.0) is False

    def test_an_untouched_trigger_is_not_squeezed(self):
        """
        A trigger has no value in memory until it first moves.
        """
        assert AxisChord().run(None, 1.0) is False
        assert AxisChord().run(None, None) is False

    def test_no_axes_is_not_a_chord(self):
        assert AxisChord().run() is False

    def test_a_single_axis_works(self):
        assert AxisChord().run(1.0) is True
