#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import LogitechJoystick, XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    axis_event,
    button_event,
    duplicate_literal_keys,
    duplicate_values,
)

# What an F710 in XInput mode is expected to report.  Unlike the Xbox tests,
# this is NOT a capture from a real device -- no F710 was available -- so
# these tests can only check the map against itself and against the driver
# layout the Xbox measurement established.  See the class docstring.
F710_AXIS_CODES = tuple(sorted(LogitechJoystick.AXIS_NAMES))
F710_BUTTON_CODES = tuple(sorted(LogitechJoystick.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> LogitechJoystick:
    device = FakeJsDevice(
        name='Logitech Gamepad F710',
        axis_codes=F710_AXIS_CODES,
        button_codes=F710_BUTTON_CODES,
        events=events,
    )
    pad = LogitechJoystick(device=device, **kwargs)
    pad.init()
    return pad


class TestMapIsSound(unittest.TestCase):

    def test_no_duplicate_control_codes(self):
        assert duplicate_literal_keys(LogitechJoystick) == []

    def test_no_duplicate_axis_names(self):
        assert duplicate_values(LogitechJoystick.AXIS_NAMES) == []

    def test_no_duplicate_button_names(self):
        assert duplicate_values(LogitechJoystick.BUTTON_NAMES) == []

    def test_every_control_is_named(self):
        pad = make_pad()
        unnamed = [
            n for n in pad.axis_map + pad.button_map
            if n.startswith(('axis(', 'button('))
        ]
        assert unnamed == []


class TestAgreesWithTheMeasuredDriverLayout(unittest.TestCase):
    """
    The F710 in XInput mode is driven by `xpad`, the same driver measured on
    a real Xbox pad.  One driver cannot report the same code as two
    different controls, so the codes shared between these two pads must
    agree.  This is the strongest check available without an F710 to hand,
    and it is the check the legacy Xbox map would have failed.
    """

    def test_axis_codes_mean_the_same_as_on_the_measured_pad(self):
        shared = set(LogitechJoystick.AXIS_NAMES) & set(XboxOneJoystick.AXIS_NAMES)
        disagreements = {
            code: (LogitechJoystick.AXIS_NAMES[code], XboxOneJoystick.AXIS_NAMES[code])
            for code in shared
            if LogitechJoystick.AXIS_NAMES[code] != XboxOneJoystick.AXIS_NAMES[code]
        }
        assert disagreements == {}

    def test_the_triggers_are_where_measurement_put_them(self):
        assert LogitechJoystick.AXIS_NAMES[0x02] == 'left_trigger'
        assert LogitechJoystick.AXIS_NAMES[0x05] == 'right_trigger'

    def test_the_right_stick_is_where_measurement_put_it(self):
        assert LogitechJoystick.AXIS_NAMES[0x03] == 'right_stick_horz'
        assert LogitechJoystick.AXIS_NAMES[0x04] == 'right_stick_vert'

    def test_only_the_labelled_buttons_differ_from_the_measured_pad(self):
        """
        Same driver, same codes; the F710 just prints different words on
        three of its buttons.
        """
        differing = {
            code
            for code in set(LogitechJoystick.BUTTON_NAMES)
            & set(XboxOneJoystick.BUTTON_NAMES)
            if LogitechJoystick.BUTTON_NAMES[code]
            != XboxOneJoystick.BUTTON_NAMES[code]
        }
        assert differing == {0x13A, 0x13B, 0x13C}


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(0, 1)])
        change = pad.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_the_logitech_button_reports(self):
        # index 8 is 0x13c, the guide button
        pad = make_pad([button_event(8, 1)])
        assert pad.poll().button == 'logitech'

    def test_back_and_start_report(self):
        pad = make_pad([button_event(6, 1), button_event(7, 1)])

        assert pad.poll().button == 'back'
        assert pad.poll().button == 'start'

    def test_a_stick_reports_by_name(self):
        pad = make_pad([axis_event(0, -32767)])
        change = pad.poll()

        assert change.axis == 'left_stick_horz'
        assert change.axis_value == -1.0

    def test_a_trigger_reports_by_name(self):
        # index 2 is 0x02, the left trigger
        pad = make_pad([axis_event(2, 32767)])
        assert pad.poll().axis == 'left_trigger'

    def test_the_dpad_reports_discrete_positions(self):
        pad = make_pad([axis_event(6, -32767), axis_event(7, 32767)])

        horiz = pad.poll()
        vert = pad.poll()
        assert (horiz.axis, horiz.axis_value) == ('dpad_horiz', -1.0)
        assert (vert.axis, vert.axis_value) == ('dpad_vert', 1.0)
