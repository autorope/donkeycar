#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import PS3Joystick, XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device -- no DualShock 3 was available.  See the
# class docstring; these tests check the map against itself and against the
# conventional ABS layout the Xbox measurement confirmed.
PS3_AXIS_CODES = tuple(sorted(PS3Joystick.AXIS_NAMES))
PS3_BUTTON_CODES = tuple(sorted(PS3Joystick.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> PS3Joystick:
    device = FakeJsDevice(
        name='Sony PLAYSTATION(R)3 Controller',
        axis_codes=PS3_AXIS_CODES,
        button_codes=PS3_BUTTON_CODES,
        events=events,
    )
    pad = PS3Joystick(device=device, **kwargs)
    pad.init()
    return pad


def index_of(name: str) -> int:
    """Driver index of a named button, as poll() reports it."""
    return PS3_BUTTON_CODES.index(
        next(c for c, n in PS3Joystick.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PS3Joystick


class TestAgreesWithTheMeasuredAxisLayout(unittest.TestCase):
    """
    The ABS codes are kernel-wide constants, and `hid-sony` follows the same
    convention `xpad` does, so the axes this map shares with the measured
    Xbox pad should mean the same thing.  Weaker than the same-driver check
    used for the F710 -- nothing forces a driver to follow the convention --
    but it is the strongest check available without a pad.
    """

    def test_shared_axis_codes_agree_with_the_measured_pad(self):
        shared = set(PS3Joystick.AXIS_NAMES) & set(XboxOneJoystick.AXIS_NAMES)
        disagreements = {
            code: (PS3Joystick.AXIS_NAMES[code], XboxOneJoystick.AXIS_NAMES[code])
            for code in shared
            if PS3Joystick.AXIS_NAMES[code] != XboxOneJoystick.AXIS_NAMES[code]
        }
        assert disagreements == {}

    def test_the_triggers_are_where_measurement_put_them(self):
        assert PS3Joystick.AXIS_NAMES[0x02] == 'left_trigger'
        assert PS3Joystick.AXIS_NAMES[0x05] == 'right_trigger'

    def test_the_right_stick_is_where_measurement_put_it(self):
        assert PS3Joystick.AXIS_NAMES[0x03] == 'right_stick_horz'
        assert PS3Joystick.AXIS_NAMES[0x04] == 'right_stick_vert'


class TestPlayStationShape(unittest.TestCase):
    """
    Where this pad genuinely differs from the Xbox-style ones.
    """

    def test_the_dpad_is_buttons_not_axes(self):
        assert 0x10 not in PS3Joystick.AXIS_NAMES
        assert 0x11 not in PS3Joystick.AXIS_NAMES
        assert set(PS3Joystick.BUTTON_NAMES.values()) >= {
            'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right',
        }

    def test_the_triggers_are_both_axis_and_button(self):
        """
        A DualShock 3 squeeze produces an analog axis event and a digital
        button event.  Both are named, so a part can use either.
        """
        assert PS3Joystick.AXIS_NAMES[0x02] == 'left_trigger'
        assert PS3Joystick.BUTTON_NAMES[0x138] == 'left_trigger_button'
        assert PS3Joystick.AXIS_NAMES[0x05] == 'right_trigger'
        assert PS3Joystick.BUTTON_NAMES[0x139] == 'right_trigger_button'

    def test_the_face_buttons_keep_playstation_names(self):
        faces = {PS3Joystick.BUTTON_NAMES[c] for c in (0x130, 0x131, 0x133, 0x134)}
        assert faces == {'cross', 'circle', 'triangle', 'square'}

    def test_face_buttons_follow_the_standard_positions(self):
        """
        South is the bottom face button, east the right, north the top.
        Getting these transposed is a classic gamepad-map error.
        """
        assert PS3Joystick.BUTTON_NAMES[0x130] == 'cross'      # BTN_SOUTH
        assert PS3Joystick.BUTTON_NAMES[0x131] == 'circle'     # BTN_EAST
        assert PS3Joystick.BUTTON_NAMES[0x133] == 'triangle'   # BTN_NORTH
        assert PS3Joystick.BUTTON_NAMES[0x134] == 'square'     # BTN_WEST


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(index_of('cross'), 1)])
        change = pad.poll()

        assert change.button == 'cross'
        assert change.button_state == 1

    def test_a_dpad_button_reports_by_name(self):
        pad = make_pad([button_event(index_of('dpad_up'), 1)])
        assert pad.poll().button == 'dpad_up'

    def test_the_ps_button_reports(self):
        pad = make_pad([button_event(index_of('ps'), 1)])
        assert pad.poll().button == 'ps'

    def test_a_stick_reports_by_name(self):
        pad = make_pad([axis_event(0, -32767)])
        change = pad.poll()

        assert change.axis == 'left_stick_horz'
        assert change.axis_value == -1.0

    def test_a_trigger_reports_on_both_axis_and_button(self):
        pad = make_pad([
            axis_event(2, 32767),
            button_event(index_of('left_trigger_button'), 1),
        ])

        assert pad.poll().axis == 'left_trigger'
        assert pad.poll().button == 'left_trigger_button'
