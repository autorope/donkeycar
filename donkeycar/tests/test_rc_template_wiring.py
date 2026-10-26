#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RC receivers through complete.py's own wiring, from raw input to
user/steering and user/throttle.

The receiver tests check the conversion and the factory tests check the
maps, and both passed while an MM1 car drove nowhere: its input reached
the event layer and stopped, because nothing bound it.  Once bound by
hand, forward drove it backwards at a quarter of its input.  Only a test
that runs the template's wiring end to end sees either, so this is that
test.  It uses the shipped configuration and no CONTROLLER_BEHAVIOR_MAP,
and it looks at what the drivetrain receives: a first version looked at
memory at the end of a pass, and passed while nothing reached the wheels.
"""

import logging
import tempfile
import unittest
from unittest import mock

from donkeycar.parts.controls.rc import RCReceiver
from donkeycar.templates import complete
from donkeycar.tests.drive_harness import driving, load_template_config
from donkeycar.tests.fake_rc import FakePigpioDevice
from donkeycar.tests.test_robohat_controller import FakeSerialPort


class ReceiverTest(unittest.TestCase):
    """
    complete.drive() with the shipped configuration and no custom map,
    looking at what the drivetrain receives.
    """

    MYCONFIG: dict = {}

    def setUp(self) -> None:
        logging.disable(logging.WARNING)
        self.addCleanup(logging.disable, logging.NOTSET)
        car_dir = tempfile.TemporaryDirectory()
        self.addCleanup(car_dir.cleanup)
        self.cfg = load_template_config(car_dir.name, **self.MYCONFIG)

    def run_car(self, steps, patch) -> list[tuple[float, float]]:
        with driving(complete, self.cfg, steps, [patch]) as (drivetrain, _):
            return drivetrain.received


class TestMM1(ReceiverTest):
    """
    The MM1 sends two pulse widths per line, steering then throttle.  Its
    steering reads inverted -- a rising pulse turns left -- which is how
    MM1 cars are wired, so 1750 us is -0.5.
    """

    MYCONFIG = {'CONTROLLER_TYPE': 'MM1'}

    def drive(self, *lines: str) -> list[tuple[float, float]]:
        port = FakeSerialPort()
        steps = [lambda line=line: port.lines.append(line) for line in lines]
        return self.run_car(steps, mock.patch(
            'donkeycar.parts.controls.RealSerialPort', return_value=port))

    def test_the_default_config_drives(self):
        assert self.drive('1750, 1750') == [(-0.5, 0.5)]

    def test_forward_is_forward_at_full_value(self):
        """
        Not flipped by JOYSTICK_THROTTLE_DIR and not scaled by
        JOYSTICK_MAX_THROTTLE: the shipped -1.0 and 0.5 made this -0.25.
        """
        assert self.drive('1500, 2000') == [(0.0, 1.0)]

    def test_reverse_is_reverse(self):
        assert self.drive('1250, 1250') == [(0.5, -0.5)]

    def test_a_held_position_keeps_driving(self):
        """
        The MM1 reports only when a reading changes, so a stick held still
        sends nothing; the car must keep going.
        """
        assert self.drive('1750, 1750', '1750, 1750', '1750, 1750') == [
            (-0.5, 0.5)] * 3

    def test_return_to_neutral(self):
        assert self.drive('1750, 1750', '1500, 1500') == [
            (-0.5, 0.5), (0.0, 0.0)]


class TestPigpioRC(ReceiverTest):
    """
    Three GPIO channels: steering, throttle and a switch.  cfg_complete.py
    has no RC pin settings (see Phase 8 in the plan), so they are supplied
    here as myconfig.py would.
    """

    MYCONFIG = {'CONTROLLER_TYPE': 'pigpio_rc', 'STEERING_RC_GPIO': 26,
                'THROTTLE_RC_GPIO': 20, 'DATA_WIPER_RC_GPIO': 19,
                'PIGPIO_INVERT': False, 'PIGPIO_JITTER': 0.025}

    def drive(self, *positions) -> list[tuple[float, float]]:
        device = FakePigpioDevice()
        device.set_position(2, -1.0)  # switch down

        def receiver(**kwargs) -> RCReceiver:
            return RCReceiver(device=device, **kwargs)

        def move(steering: float, throttle: float) -> None:
            device.set_position(0, steering)
            device.set_position(1, throttle)

        steps = [lambda p=p: move(*p) for p in positions]
        return self.run_car(steps, mock.patch(
            'donkeycar.parts.controls.RCReceiver', receiver))

    def test_the_default_config_drives(self):
        assert self.drive((0.5, 0.5)) == [(0.5, 0.5)]

    def test_forward_is_forward_at_full_value(self):
        assert self.drive((0.0, 1.0)) == [(0.0, 1.0)]

    def test_reverse_is_reverse(self):
        assert self.drive((-0.5, -0.5)) == [(-0.5, -0.5)]

    def test_return_to_neutral(self):
        assert self.drive((0.5, 0.5), (0.0, 0.0)) == [(0.5, 0.5), (0.0, 0.0)]


if __name__ == '__main__':
    unittest.main()
