#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
What a physical controller actually gets to the drivetrain, through a
template's real drive().

Found in review: on this branch no physical controller could drive a car
built from complete.py, cv_control.py or path_follow.py.  The controller's
parts ran after the drivetrain, and each pass began with the web
controller writing 0.0 over what they had written.  Every test passed,
because they all looked at memory at the end of a pass rather than at what
the drivetrain received.  These look at the drivetrain.
"""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from donkeycar.parts.controls.device import ControlChange
from donkeycar.parts.web_controller.web import LocalWebController
from donkeycar.templates import complete, cv_control
from donkeycar.tests.drive_harness import driving, load_template_config
from donkeycar.tests.fake_js import FakeInputController

#: JOYSTICK_MAX_THROTTLE in the shipped configuration.
SCALE = 0.5


class DrivingTest(unittest.TestCase):
    """
    A car from a shipped template with CONTROLLER_TYPE = 'xbox' and a
    scripted pad.  On the xbox map the right stick's vertical axis is the
    throttle and reads negative pushed forward; the left stick's horizontal
    axis steers; Y is the emergency stop; menu toggles constant throttle.
    """

    TEMPLATE = complete
    TEMPLATE_NAME = 'complete'

    @classmethod
    def setUpClass(cls) -> None:
        # one car per template: creating it is the slow part, and runs of
        # the same template can share its tub
        car_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(car_dir.cleanup)
        cls.cfg = load_template_config(car_dir.name, cls.TEMPLATE_NAME,
                                       CONTROLLER_TYPE='xbox')

    def setUp(self) -> None:
        logging.disable(logging.WARNING)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.pad = FakeInputController()

    def stick(self, axis: str, value: float):
        return lambda: self.pad.changes.append(
            ControlChange(None, None, axis, value))

    def press(self, button: str):
        return lambda: self.pad.changes.extend([
            ControlChange(button, 1, None, None),
            ControlChange(button, 0, None, None)])

    @staticmethod
    def idle() -> None:
        pass

    def drive(self, *steps, on_start=None) -> list[tuple[float, float]]:
        """
        What the drivetrain received on each pass, one pass per step.
        """
        patch = mock.patch('donkeycar.templates.complete.get_input_controller',
                           return_value=self.pad)
        with driving(self.TEMPLATE, self.cfg, steps, [patch],
                     on_start=on_start) as (drivetrain, _):
            return drivetrain.received

    def throttles(self, *steps, on_start=None) -> list[float]:
        return [throttle for _, throttle in self.drive(*steps, on_start=on_start)]


class TestAHeldStickDrives(DrivingTest):

    def test_a_held_throttle_reaches_the_drivetrain_on_every_pass(self):
        assert self.throttles(
            self.stick('right_stick_vert', -1.0),
            self.idle, self.idle, self.idle,
        ) == [SCALE] * 4

    def test_held_steering_reaches_the_drivetrain_on_every_pass(self):
        received = self.drive(
            self.stick('left_stick_horz', 0.5), self.idle, self.idle)
        assert [steering for steering, _ in received] == [0.5] * 3

    def test_centring_the_stick_returns_to_neutral(self):
        assert self.throttles(
            self.stick('right_stick_vert', -1.0), self.idle,
            self.stick('right_stick_vert', 0.0), self.idle,
        ) == [SCALE, SCALE, 0.0, 0.0]


class TestTheWebPage(DrivingTest):

    def test_the_web_page_drives_until_the_controller_reports(self):
        """
        Until the pad has reported anything, nothing it drives writes, so
        the web page's throttle reaches the drivetrain.  Once the pad has
        reported, it owns the throttle, as legacy had it.
        """
        def web_page_at(parts) -> None:
            for part in parts:
                if isinstance(part, LocalWebController):
                    part.throttle = 0.3

        assert self.throttles(
            self.idle, self.idle,
            self.stick('right_stick_vert', -1.0), self.idle,
            on_start=web_page_at,
        ) == [0.3, 0.3, SCALE, SCALE]


class TestTheEmergencyStop(DrivingTest):

    def test_the_braking_sequence_reaches_the_drivetrain(self):
        """
        Full reverse, a blip, full reverse again, then winding back to zero.
        The throttle filter turns the second reverse in a row into 0.0 --
        its 'tap back for ESC reverse', which legacy's stop also went
        through.  Before the fix none of this reached the drivetrain.
        """
        throttles = self.throttles(
            self.stick('right_stick_vert', -1.0),
            self.press('y_button'), *[self.idle] * 14)

        assert throttles[0] == SCALE
        assert throttles[1] == -SCALE
        assert throttles[2] > 0.0
        assert throttles[3] == -SCALE
        assert min(throttles[4:]) < 0.0
        assert throttles[-1] == 0.0

    def test_a_stick_held_through_the_stop_does_not_drive_off_again(self):
        """
        Legacy left the throttle at zero after a stop until the stick
        moved.  With the stick's position held between events, a stick
        still held forward drove the car off the moment the stop finished.
        """
        throttles = self.throttles(
            self.stick('right_stick_vert', -1.0),
            self.press('y_button'), *[self.idle] * 20)

        assert throttles[-6:] == [0.0] * 6

    def test_moving_the_stick_after_the_stop_drives_again(self):
        throttles = self.throttles(
            self.stick('right_stick_vert', -1.0),
            self.press('y_button'), *[self.idle] * 16,
            self.stick('right_stick_vert', -0.5), self.idle)

        assert throttles[-2:] == [SCALE / 2] * 2

    def test_the_stop_ends_constant_throttle(self):
        """
        Constant throttle holds the throttle at the limit with the stick
        untouched.  Legacy's stop turned it off; without that the car drove
        off again afterwards.
        """
        throttles = self.throttles(
            self.press('menu'), self.idle,
            self.press('y_button'), *[self.idle] * 20)

        assert throttles[:2] == [SCALE, SCALE]
        assert throttles[-6:] == [0.0] * 6


class TestConstantThrottle(DrivingTest):

    def test_turning_it_off_gives_zero_not_the_stick(self):
        """
        The PR's hardware test plan, T4.5: "turning it off gives zero, not a
        lurch to whatever the stick reads".  With the stick's position held
        between events, turning it off with the stick at 60% gave 0.0 for a
        pass and then 0.3.
        """
        throttles = self.throttles(
            self.stick('right_stick_vert', -0.6),
            self.press('menu'), self.idle,
            self.press('menu'), self.idle, self.idle)

        assert throttles[0] == 0.6 * SCALE
        assert throttles[1:3] == [SCALE, SCALE]
        assert throttles[3:] == [0.0, 0.0, 0.0]

    def test_the_stick_drives_again_once_it_moves(self):
        throttles = self.throttles(
            self.press('menu'), self.idle, self.press('menu'), self.idle,
            self.stick('right_stick_vert', -1.0), self.idle)

        assert throttles[-2:] == [SCALE, SCALE]


class TestALostControllerStopsTheCar(DrivingTest):
    """
    Found by Copilot review: a disconnect only stopped the polling thread.
    The stick's position is held between events, so a pad lost
    mid-acceleration left the car driving indefinitely.  The PR's hardware
    test plan, T5.5, expects the loop to stop.
    """

    def lose_the_pad(self) -> None:
        self.pad.poll_error = OSError('/dev/input/js0 disconnected')

    def test_the_last_command_is_neutral_and_the_loop_ends(self):
        received = self.drive(
            self.stick('right_stick_vert', -1.0),
            self.stick('left_stick_horz', 0.5),
            self.lose_the_pad, self.idle, self.idle, self.idle)

        assert received[:2] == [(0.0, SCALE), (0.5, SCALE)]
        assert received[2:] == [(0.0, 0.0)]  # one neutral pass, then no more

    def test_it_stops_an_autopilot_run_too(self):
        """
        The pad was the way to stop the pilot; without it, the run ends.
        """
        def autopilot(parts) -> None:
            for part in parts:
                if isinstance(part, LocalWebController):
                    part.mode = 'local'

        received = self.drive(self.idle, self.lose_the_pad,
                              self.idle, self.idle, on_start=autopilot)

        assert received[-1] == (0.0, 0.0)
        assert len(received) == 2


class TestCvControl(DrivingTest):
    """
    cv_control.py calls the same functions, so it had the same defect.
    """

    TEMPLATE = cv_control
    TEMPLATE_NAME = 'cv_control'

    def test_a_held_throttle_reaches_the_drivetrain_on_every_pass(self):
        assert self.throttles(
            self.stick('right_stick_vert', -1.0), self.idle, self.idle,
        ) == [SCALE] * 3


class TestTheTemplatesAddDrivingBehaviorsFirst(unittest.TestCase):
    """
    Checked in the source as well, because path_follow.py cannot be
    imported on Python 3.12+ (it uses distutils), so it cannot be driven
    here.
    """

    TEMPLATES = Path(complete.__file__).parent

    def assert_driving_behaviors_come_first(self, name: str) -> None:
        source = (self.TEMPLATES / f'{name}.py').read_text()
        body = source[source.index('\ndef drive('):]
        driving_at = body.index('add_driving_behaviors(V, cfg)')
        assert body.index('add_user_controller(') < driving_at, name
        assert driving_at < body.index('V.add(DriveMode('), name
        assert driving_at < body.index('add_drivetrain(V, cfg)'), name

    def test_complete(self):
        self.assert_driving_behaviors_come_first('complete')

    def test_cv_control(self):
        self.assert_driving_behaviors_come_first('cv_control')

    def test_path_follow(self):
        self.assert_driving_behaviors_come_first('path_follow')


if __name__ == '__main__':
    unittest.main()
