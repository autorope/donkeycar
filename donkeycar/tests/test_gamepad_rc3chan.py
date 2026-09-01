#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import RC3ChanJoystick, XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device.
RC_AXIS_CODES = tuple(sorted(RC3ChanJoystick.AXIS_NAMES))
RC_BUTTON_CODES = tuple(sorted(RC3ChanJoystick.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> RC3ChanJoystick:
    device = FakeJsDevice(
        name='RC 3-channel transmitter',
        axis_codes=RC_AXIS_CODES,
        button_codes=RC_BUTTON_CODES,
        events=events,
    )
    pad = RC3ChanJoystick(device=device, **kwargs)
    pad.init()
    return pad


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = RC3ChanJoystick


class TestItIsNotAGamepad(unittest.TestCase):
    """
    Three channels and nothing else.  Most of what a template binds by
    default simply does not exist here, which is the case the per-controller
    behavior map has to handle.
    """

    def test_the_axes_are_channels_not_sticks(self):
        assert set(RC3ChanJoystick.AXIS_NAMES.values()) == {'steering', 'throttle'}

    def test_there_are_no_sticks(self):
        names = set(RC3ChanJoystick.AXIS_NAMES.values())
        assert not any(n.startswith(('left_stick', 'right_stick')) for n in names)

    def test_there_is_no_dpad_and_there_are_no_face_buttons(self):
        names = set(RC3ChanJoystick.BUTTON_NAMES.values())
        assert not any(n.startswith('dpad_') for n in names)
        assert not any(n.endswith('_button') for n in names)

    def test_it_has_only_three_channels(self):
        assert len(RC3ChanJoystick.AXIS_NAMES) == 2
        assert len(RC3ChanJoystick.BUTTON_NAMES) == 2  # two positions, one switch

    def test_it_shares_no_control_names_with_a_gamepad(self):
        rc = set(RC3ChanJoystick.AXIS_NAMES.values()) | set(
            RC3ChanJoystick.BUTTON_NAMES.values()
        )
        pad = set(XboxOneJoystick.AXIS_NAMES.values()) | set(
            XboxOneJoystick.BUTTON_NAMES.values()
        )
        assert rc & pad == set()


class TestPolling(unittest.TestCase):

    def test_steering_reports_by_name(self):
        pad = make_pad([axis_event(0, -32767)])
        change = pad.poll()

        assert change.axis == 'steering'
        assert change.axis_value == -1.0

    def test_throttle_reports_by_name(self):
        pad = make_pad([axis_event(1, 32767)])
        change = pad.poll()

        assert change.axis == 'throttle'
        assert change.axis_value == 1.0

    def test_the_switch_positions_report_separately(self):
        pad = make_pad([button_event(0, 1), button_event(1, 1)])

        assert pad.poll().button == 'switch_up'
        assert pad.poll().button == 'switch_down'
