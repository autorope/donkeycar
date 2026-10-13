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
test.  It uses the shipped configuration and no CONTROLLER_BEHAVIOR_MAP.
"""

import types
import unittest
from unittest import mock

import donkeycar as dk
import donkeycar.templates.cfg_complete as shipped
from donkeycar.parts.controls.events import InputControllerEvents
from donkeycar.parts.controls.rc import RCReceiver
from donkeycar.templates import complete
from donkeycar.tests.fake_rc import FakePigpioDevice
from donkeycar.tests.test_robohat_controller import FakeSerialPort


def shipped_config(**overrides) -> types.SimpleNamespace:
    """
    cfg_complete.py as shipped, with the overrides a user would put in
    myconfig.py.
    """
    settings = {k: getattr(shipped, k) for k in dir(shipped) if k.isupper()}
    settings.update(USE_JOYSTICK_AS_DEFAULT=True, **overrides)
    return types.SimpleNamespace(**settings)


class TemplateHarness:
    """
    The controller and driving parts complete.py adds, with the receiver's
    input injected and the event pump stepped by hand rather than on its
    thread.
    """

    def __init__(self, cfg) -> None:
        self.V = dk.vehicle.Vehicle()
        self.V.mem['user/steering'] = 0.0
        self.V.mem['user/throttle'] = 0.0
        complete.add_user_controller(self.V, cfg, use_joystick=True)
        complete.add_controller_behaviors(self.V, cfg)

        pumps = [entry['part'] for entry in self.V.parts
                 if isinstance(entry['part'], InputControllerEvents)]
        # the web buttons' pump comes first, the receiver's last
        self.pump = pumps[-1]
        assert self.pump._controller.init()

    def one_pass(self) -> tuple[float, float]:
        """
        Let the receiver report, then run the vehicle loop once.
        """
        for _ in range(4):  # one poll per channel, and one to spare
            self.pump.poll()
        self.V.update_parts()
        return self.V.mem['user/steering'], self.V.mem['user/throttle']


class TestMM1(unittest.TestCase):
    """
    The MM1 sends two pulse widths per line, steering then throttle.  Its
    steering reads inverted -- a rising pulse turns left -- which is how
    MM1 cars are wired, so 1750 us is -0.5.
    """

    def drive(self, *lines: str) -> list[tuple[float, float]]:
        port = FakeSerialPort()
        with mock.patch('donkeycar.parts.controls.RealSerialPort',
                        return_value=port):
            car = TemplateHarness(shipped_config(CONTROLLER_TYPE='MM1'))
        results = []
        for line in lines:
            port.lines.append(line)
            results.append(car.one_pass())
        return results

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

    def test_return_to_neutral(self):
        assert self.drive('1750, 1750', '1500, 1500') == [
            (-0.5, 0.5), (0.0, 0.0)]


class TestPigpioRC(unittest.TestCase):
    """
    Three GPIO channels: steering, throttle and a switch.  cfg_complete.py
    has no RC pin settings (see Phase 8 in the plan), so they are supplied
    here as myconfig.py would.
    """

    RC_PINS = dict(STEERING_RC_GPIO=26, THROTTLE_RC_GPIO=20,
                   DATA_WIPER_RC_GPIO=19, PIGPIO_INVERT=False,
                   PIGPIO_JITTER=0.025)

    def setUp(self) -> None:
        self.device = FakePigpioDevice()
        self.device.set_position(2, -1.0)  # switch down

        device = self.device

        def receiver(**kwargs) -> RCReceiver:
            return RCReceiver(device=device, **kwargs)

        with mock.patch('donkeycar.parts.controls.RCReceiver', receiver):
            self.car = TemplateHarness(
                shipped_config(CONTROLLER_TYPE='pigpio_rc', **self.RC_PINS))

    def drive(self, steering: float, throttle: float) -> tuple[float, float]:
        self.device.set_position(0, steering)
        self.device.set_position(1, throttle)
        return self.car.one_pass()

    def test_the_default_config_drives(self):
        assert self.drive(0.5, 0.5) == (0.5, 0.5)

    def test_forward_is_forward_at_full_value(self):
        assert self.drive(0.0, 1.0) == (0.0, 1.0)

    def test_reverse_is_reverse(self):
        assert self.drive(-0.5, -0.5) == (-0.5, -0.5)

    def test_return_to_neutral(self):
        self.drive(0.5, 0.5)
        assert self.drive(0.0, 0.0) == (0.0, 0.0)


if __name__ == '__main__':
    unittest.main()
