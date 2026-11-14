#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import (
    PS3Joystick,
    PS3JoystickOld,
    PS3JoystickSixAd,
)
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device.
OLD_AXIS_CODES = tuple(sorted(PS3JoystickOld.AXIS_NAMES))
OLD_BUTTON_CODES = tuple(sorted(PS3JoystickOld.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> PS3JoystickOld:
    device = FakeJsDevice(
        name='Sony PLAYSTATION(R)3 Controller',
        axis_codes=OLD_AXIS_CODES,
        button_codes=OLD_BUTTON_CODES,
        events=events,
    )
    pad = PS3JoystickOld(device=device, **kwargs)
    pad.init()
    return pad


def axis_index(name: str) -> int:
    return OLD_AXIS_CODES.index(
        next(c for c, n in PS3JoystickOld.AXIS_NAMES.items() if n == name)
    )


def button_index(name: str) -> int:
    return OLD_BUTTON_CODES.index(
        next(c for c, n in PS3JoystickOld.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PS3JoystickOld


class TestThreeDriversThreeLayouts(unittest.TestCase):
    """
    One controller, three drivers, three different places for the right
    stick.  This is the clearest statement of why these maps are keyed to a
    driver rather than to a piece of hardware, and why 'it is the same pad'
    is never a reason to reuse a map.
    """

    def test_the_right_stick_is_in_three_different_places(self):
        def right_stick(pad) -> tuple[int, int]:
            names = pad.AXIS_NAMES
            horz = next(c for c, n in names.items() if n == 'right_stick_horz')
            vert = next(c for c, n in names.items() if n == 'right_stick_vert')
            return horz, vert

        assert right_stick(PS3Joystick) == (0x03, 0x04)      # modern in-kernel
        assert right_stick(PS3JoystickSixAd) == (0x02, 0x03)  # sixad
        assert right_stick(PS3JoystickOld) == (0x02, 0x05)    # Jessie-era

    def test_the_ps_button_is_in_three_different_places(self):
        def ps(pad) -> int:
            return next(c for c, n in pad.BUTTON_NAMES.items() if n == 'ps')

        assert ps(PS3Joystick) == 0x13C
        assert ps(PS3JoystickSixAd) == 0x130
        assert ps(PS3JoystickOld) == 0x2C0


class TestPressureSensitivity(unittest.TestCase):
    """
    What distinguishes this driver: the DualShock 3's analog pressure on
    every face button, shoulder and dpad direction, reported as axes
    alongside the ordinary digital buttons.
    """

    def test_every_pressure_sensitive_control_is_named(self):
        pressure = {
            n for n in PS3JoystickOld.AXIS_NAMES.values()
            if n.endswith('_pressure')
        }
        assert pressure == {
            'dpad_up_pressure', 'dpad_right_pressure',
            'dpad_down_pressure', 'dpad_left_pressure',
            'left_shoulder_pressure', 'right_shoulder_pressure',
            'triangle_pressure', 'circle_pressure',
            'cross_pressure', 'square_pressure',
        }

    def test_the_pressure_run_has_no_gaps(self):
        """
        The twelve pressure axes are consecutive, 0x2c to 0x37: the dpad,
        the four shoulders and triggers, then the face buttons.  The legacy
        map skipped 0x2f, so a left-dpad press arrived as an anonymous
        'axis(0x2f)'.  A gap here means a control nobody can bind.
        """
        run = [c for c in PS3JoystickOld.AXIS_NAMES if 0x2C <= c <= 0x37]
        assert sorted(run) == list(range(0x2C, 0x38))

    def test_the_analog_triggers_use_the_shared_names(self):
        """
        These are L2 and R2 pressure, but they are what every other pad
        calls the triggers, so a behavior map reads the same across pads.
        """
        assert PS3JoystickOld.AXIS_NAMES[0x30] == 'left_trigger'
        assert PS3JoystickOld.AXIS_NAMES[0x31] == 'right_trigger'

    def test_a_button_reports_as_both_press_and_pressure(self):
        pad = make_pad([
            button_event(button_index('cross'), 1),
            axis_event(axis_index('cross_pressure'), 32767),
        ])

        assert pad.poll().button == 'cross'
        assert pad.poll().axis == 'cross_pressure'


class TestSharesPlayStationNames(unittest.TestCase):

    def test_the_buttons_match_the_sixad_map(self):
        """
        Both present the pad through the generic joystick block, so apart
        from the PS button the button codes agree.
        """
        shared = {
            c for c in set(PS3JoystickOld.BUTTON_NAMES)
            & set(PS3JoystickSixAd.BUTTON_NAMES)
            if PS3JoystickOld.BUTTON_NAMES[c] == PS3JoystickSixAd.BUTTON_NAMES[c]
        }
        assert shared == set(range(0x120, 0x130))


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(button_index('cross'), 1)])
        change = pad.poll()

        assert change.button == 'cross'
        assert change.button_state == 1

    def test_the_ps_button_reports(self):
        pad = make_pad([button_event(button_index('ps'), 1)])
        assert pad.poll().button == 'ps'

    def test_the_right_stick_reports_from_this_drivers_codes(self):
        pad = make_pad([
            axis_event(axis_index('right_stick_horz'), -32767),
            axis_event(axis_index('right_stick_vert'), 32767),
        ])

        assert pad.poll().axis == 'right_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_the_left_dpad_pressure_is_no_longer_anonymous(self):
        pad = make_pad([axis_event(axis_index('dpad_left_pressure'), 32767)])
        assert pad.poll().axis == 'dpad_left_pressure'

    def test_the_tilt_axes_report(self):
        pad = make_pad([axis_event(axis_index('tilt_x'), 16384)])
        assert pad.poll().axis == 'tilt_x'
