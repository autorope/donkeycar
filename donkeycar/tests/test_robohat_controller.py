#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.device import NO_CHANGE
from donkeycar.parts.controls.robohat import RoboHATController, SerialPort


class FakeSerialPort:
    """
    Replays lines as the MM1 would send them.
    """

    def __init__(self, lines=(), open_error: OSError | None = None) -> None:
        self.lines = list(lines)
        self.open_error = open_error
        self.open_count = 0
        self.closed = False

    def open(self) -> None:
        self.open_count += 1
        if self.open_error is not None:
            raise self.open_error

    def readline(self) -> str:
        return self.lines.pop(0) if self.lines else ''

    def close(self) -> None:
        self.closed = True


_protocol_check: SerialPort = FakeSerialPort()


def make_controller(lines=(), **kwargs):
    port = FakeSerialPort(lines)
    controller = RoboHATController(port=port, **kwargs)
    controller.init()
    return controller, port


def positions(controller: RoboHATController) -> dict[str, float]:
    """
    Everything the controller has to give, as a name -> value map.

    Note this keeps polling until nothing is left, and an empty queue makes
    poll() read the next line, so this consumes every line the port holds.
    Tests that care about one line at a time poll explicitly instead.
    """
    found = {}
    while (change := controller.poll()) != NO_CHANGE:
        found[change.axis] = change.axis_value
    return found


class TestMatchesTheLegacyArithmetic(unittest.TestCase):
    """
    The same readings and expected positions as the existing RoboHAT tests
    in test_robohat.py, so this reports exactly what the legacy part did.
    An MM1 car's steering feel must not change quietly.
    """

    def check(self, line: str, steering: float, throttle: float) -> None:
        controller, _ = make_controller([line])
        found = positions(controller)
        assert found.get('steering', 0.0) == steering, line
        assert found.get('throttle', 0.0) == throttle, line

    def test_centre(self):
        self.check('1500, 1500', steering=0.0, throttle=0.0)

    def test_full_left_stick_centre_throttle(self):
        self.check('2000, 1500', steering=-1.0, throttle=0.0)

    def test_slightly_left_and_slightly_forward(self):
        self.check('1600, 1600', steering=-0.2, throttle=0.2)

    def test_full_left_and_full_forward(self):
        self.check('2000, 2000', steering=-1.0, throttle=1.0)

    def test_full_right_and_full_reverse(self):
        self.check('1000, 1000', steering=1.0, throttle=-1.0)

    def test_part_right_and_part_reverse(self):
        self.check('1200, 1200', steering=0.6, throttle=-0.6)


class TestTheOutputSettingsAreNotReadHere(unittest.TestCase):
    """
    MM1_STOPPED_PWM, MM1_MAX_FORWARD and MM1_MAX_REVERSE limit how hard the
    car drives, which is RoboHATDriver's job.  This is the input side, and
    reports what the transmitter asked for.

    The legacy part appeared to read them but mapped throttle through the
    configured range and straight back out, so they cancelled and never had
    any effect.  These tests exist so that nobody later notices the
    constants are unused, wires them in as a fix, and silently changes the
    throttle response of every MM1 car.
    """

    def test_the_controller_takes_no_output_limits(self):
        import inspect

        parameters = inspect.signature(RoboHATController.__init__).parameters
        for setting in ('stopped_pwm', 'max_forward', 'max_reverse'):
            assert setting not in parameters, setting

    def test_full_travel_reports_full_travel(self):
        """
        Whatever the car is allowed to do with it.  Scaling belongs on the
        output side, where one setting limits every source of throttle
        rather than each source limiting itself.
        """
        controller, _ = make_controller(['1500, 2000', '1500, 1000'])

        # steering stays centred, so only the throttle reports
        assert controller.poll().axis_value == 1.0
        assert controller.poll().axis_value == -1.0

    def test_steering_mid_is_read_because_it_describes_the_input(self):
        """
        The one MM1 setting this side does read: where the wheel rests is
        something the input has to know to report centre correctly.
        """
        import inspect

        parameters = inspect.signature(RoboHATController.__init__).parameters
        assert 'steering_mid' in parameters


class TestAdjustedSteeringMid(unittest.TestCase):
    """
    A receiver whose centre is off-centre still has to reach full lock both
    ways, so each half of the travel is scaled to its own side.
    """

    def test_the_new_centre_reads_as_centred(self):
        controller, _ = make_controller(['1450, 1500'], steering_mid=1450)
        assert positions(controller).get('steering', 0.0) == 0.0

    def test_both_ends_still_reach_full_lock(self):
        controller, _ = make_controller(
            ['2000, 1500', '1000, 1500'], steering_mid=1450
        )
        # centred throttle matches the resting state, so only steering moves
        assert controller.poll().axis_value == -1.0
        assert controller.poll().axis_value == 1.0

    def test_the_short_side_is_scaled_to_its_own_span(self):
        # 1225 is halfway between 1000 and the 1450 centre
        controller, _ = make_controller(['1225, 1500'], steering_mid=1450)
        assert positions(controller)['steering'] == 0.5


class TestParsing(unittest.TestCase):

    def test_a_missing_space_still_parses(self):
        """
        The legacy version split on ', ' exactly, so a firmware that sent
        '1500,1500' produced a line that silently parsed to nothing.
        """
        controller, _ = make_controller(['2000,2000'])
        assert positions(controller) == {'steering': -1.0, 'throttle': 1.0}

    def test_a_decimal_reading_parses(self):
        """
        Legacy used str.isnumeric(), which rejects '1600.0'.
        """
        controller, _ = make_controller(['1600.0, 1600.0'])
        assert positions(controller) == {'steering': -0.2, 'throttle': 0.2}

    def test_a_timed_out_read_is_not_a_reading(self):
        controller, _ = make_controller([])
        assert controller.poll() == NO_CHANGE

    def test_a_malformed_line_is_ignored(self):
        controller, _ = make_controller(['hello', '1600, 1600'])

        assert controller.poll() == NO_CHANGE  # the junk line
        assert positions(controller) == {'steering': -0.2, 'throttle': 0.2}

    def test_a_line_with_one_number_is_ignored(self):
        controller, _ = make_controller(['1500'])
        assert controller.poll() == NO_CHANGE

    def test_a_reading_beyond_the_normal_range_is_clamped(self):
        controller, _ = make_controller(['2500, 2500'])
        assert positions(controller) == {'steering': -1.0, 'throttle': 1.0}


class TestReporting(unittest.TestCase):

    def test_both_channels_moving_together_are_both_reported(self):
        controller, _ = make_controller(['1600, 1600'])
        assert len(positions(controller)) == 2

    def test_an_unchanged_reading_reports_nothing(self):
        controller, _ = make_controller(['1600, 1600', '1600, 1600'])

        assert len(positions(controller)) == 2
        assert controller.poll() == NO_CHANGE

    def test_only_the_channel_that_moved_is_reported(self):
        controller, _ = make_controller(['1600, 1600', '1700, 1600'])

        first = {controller.poll().axis, controller.poll().axis}
        assert first == {'steering', 'throttle'}

        # the second line moves only the steering
        change = controller.poll()
        assert (change.axis, change.axis_value) == ('steering', -0.4)
        assert controller.poll() == NO_CHANGE

    def test_jitter_below_epsilon_is_suppressed(self):
        controller, _ = make_controller(
            ['1600, 1600', '1605, 1600'], axis_epsilon=0.05
        )
        positions(controller)
        assert controller.poll() == NO_CHANGE


class TestLifecycle(unittest.TestCase):

    def test_init_opens_the_port(self):
        _, port = make_controller()
        assert port.open_count == 1

    def test_init_fails_when_the_port_will_not_open(self):
        port = FakeSerialPort(open_error=OSError('no such port'))
        controller = RoboHATController(port=port)

        assert controller.init() is False
        assert controller.poll() == NO_CHANGE

    def test_init_is_idempotent(self):
        controller, port = make_controller()
        controller.init()
        assert port.open_count == 1

    def test_shutdown_closes_the_port(self):
        controller, port = make_controller(['1600, 1600'])
        controller.shutdown()

        assert port.closed is True
        assert controller.poll() == NO_CHANGE
