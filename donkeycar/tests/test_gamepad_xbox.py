#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import XboxOneJoystick, XboxOneUsbJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# Exactly what an 'Xbox Wireless Controller' reported through hid-microsoft
# over Bluetooth on 2026-10-07.  The driver declares every code from 0x130
# to 0x13E, though six of them never moved.
XBOX_BT_AXIS_CODES = (0x00, 0x01, 0x02, 0x05, 0x09, 0x0A, 0x10, 0x11)
XBOX_BT_BUTTON_CODES = tuple(range(0x130, 0x13F))

#: Declared by the driver, silent when every control on the pad was worked.
SILENT_BUTTON_CODES = {0x132, 0x135, 0x138, 0x139, 0x13A, 0x13C}


def make_pad(events=(), **kwargs) -> XboxOneJoystick:
    device = FakeJsDevice(
        name='Xbox Wireless Controller',
        axis_codes=XBOX_BT_AXIS_CODES,
        button_codes=XBOX_BT_BUTTON_CODES,
        events=events,
    )
    pad = XboxOneJoystick(device=device, **kwargs)
    pad.init()
    return pad


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = XboxOneJoystick


class TestMapCoversTheDevice(unittest.TestCase):

    def test_every_axis_is_named(self):
        unnamed = [n for n in make_pad().axis_map if n.startswith('axis(')]
        assert unnamed == []

    def test_only_the_silent_buttons_are_unnamed(self):
        """
        Naming a button that never reports gives the user something to bind
        and then watch do nothing.
        """
        unnamed = {
            code for code in XBOX_BT_BUTTON_CODES
            if code not in XboxOneJoystick.BUTTON_NAMES
        }
        assert unnamed == SILENT_BUTTON_CODES

    def test_the_map_names_nothing_the_device_lacks(self):
        extra_axes = set(XboxOneJoystick.AXIS_NAMES) - set(XBOX_BT_AXIS_CODES)
        extra_buttons = set(XboxOneJoystick.BUTTON_NAMES) - set(XBOX_BT_BUTTON_CODES)

        assert extra_axes == set()
        assert extra_buttons == set()


class TestMeasuredAttribution(unittest.TestCase):
    """
    Each moved in isolation with the capture tool.
    """

    def test_right_stick(self):
        assert XboxOneJoystick.AXIS_NAMES[0x02] == 'right_stick_horz'
        assert XboxOneJoystick.AXIS_NAMES[0x05] == 'right_stick_vert'

    def test_triggers(self):
        assert XboxOneJoystick.AXIS_NAMES[0x0A] == 'left_trigger'
        assert XboxOneJoystick.AXIS_NAMES[0x09] == 'right_trigger'

    def test_view_and_xbox_cannot_be_bound(self):
        """
        hid-microsoft sends them as keyboard keys, which never reach the
        joystick device.
        """
        names = set(XboxOneJoystick.BUTTON_NAMES.values())
        assert 'view' not in names
        assert 'xbox' not in names


class TestTheTwoDriversDisagree(unittest.TestCase):
    """
    The point of having two maps.  The USB map on a Bluetooth pad would
    drive with a trigger; tidying them into one would bring that back.
    """

    def test_0x02_and_0x05_are_the_right_stick_here_and_triggers_on_usb(self):
        for code in (0x02, 0x05):
            assert 'stick' in XboxOneJoystick.AXIS_NAMES[code]
            assert 'trigger' in XboxOneUsbJoystick.AXIS_NAMES[code]

    def test_they_agree_on_the_left_stick_dpad_and_buttons(self):
        for code in (0x00, 0x01, 0x10, 0x11):
            assert XboxOneJoystick.AXIS_NAMES[code] == XboxOneUsbJoystick.AXIS_NAMES[code]
        for code, name in XboxOneJoystick.BUTTON_NAMES.items():
            assert XboxOneUsbJoystick.BUTTON_NAMES[code] == name

    def test_the_same_names_are_offered_but_view_and_xbox(self):
        """
        So a behavior map written for one reads the same on the other.
        """
        bluetooth = set(XboxOneJoystick.AXIS_NAMES.values()) | set(
            XboxOneJoystick.BUTTON_NAMES.values())
        usb = set(XboxOneUsbJoystick.AXIS_NAMES.values()) | set(
            XboxOneUsbJoystick.BUTTON_NAMES.values())

        assert usb - bluetooth == {'view', 'xbox'}
        assert bluetooth - usb == set()


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(0, 1)])
        change = pad.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_menu_reports_by_name(self):
        # index 11 is 0x13b
        assert make_pad([button_event(11, 1)]).poll().button == 'menu'

    def test_the_right_stick_reports_by_name(self):
        # indexes 2 and 3 are 0x02 and 0x05
        pad = make_pad([axis_event(2, -32767), axis_event(3, 32767)])

        assert pad.poll().axis == 'right_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_the_triggers_report_by_name(self):
        # indexes 4 and 5 are 0x09 and 0x0a
        pad = make_pad([axis_event(4, 32767), axis_event(5, -32767)])

        right = pad.poll()
        left = pad.poll()
        assert (right.axis, right.axis_value) == ('right_trigger', 1.0)
        assert (left.axis, left.axis_value) == ('left_trigger', -1.0)

    def test_a_silent_button_keeps_its_code_name(self):
        # index 2 is 0x132, declared but never seen to move
        assert make_pad([button_event(2, 1)]).poll().button == 'button(0x132)'
