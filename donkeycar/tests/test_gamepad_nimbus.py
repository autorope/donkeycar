#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import Nimbus, XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device.
NIMBUS_AXIS_CODES = tuple(sorted(Nimbus.AXIS_NAMES))
NIMBUS_BUTTON_CODES = tuple(sorted(Nimbus.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> Nimbus:
    device = FakeJsDevice(
        name='Nimbus',
        axis_codes=NIMBUS_AXIS_CODES,
        button_codes=NIMBUS_BUTTON_CODES,
        events=events,
    )
    pad = Nimbus(device=device, **kwargs)
    pad.init()
    return pad


def axis_index(name: str) -> int:
    return NIMBUS_AXIS_CODES.index(
        next(c for c, n in Nimbus.AXIS_NAMES.items() if n == name)
    )


def button_index(name: str) -> int:
    return NIMBUS_BUTTON_CODES.index(
        next(c for c, n in Nimbus.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = Nimbus


class TestTheHatAxesAreTheDpad(unittest.TestCase):
    """
    The legacy map called these 'hmm' and 'what' -- placeholders that
    shipped.  0x10 and 0x11 are ABS_HAT0X and ABS_HAT0Y, and they were
    measured as the dpad on a real Xbox pad, so they are the dpad here too.
    """

    def test_the_hat_axes_are_named_as_the_dpad(self):
        assert Nimbus.AXIS_NAMES[0x10] == 'dpad_horiz'
        assert Nimbus.AXIS_NAMES[0x11] == 'dpad_vert'

    def test_they_agree_with_the_measured_pad(self):
        assert Nimbus.AXIS_NAMES[0x10] == XboxOneJoystick.AXIS_NAMES[0x10]
        assert Nimbus.AXIS_NAMES[0x11] == XboxOneJoystick.AXIS_NAMES[0x11]

    def test_no_placeholder_names_remain(self):
        """
        A name nobody understood is a control nobody will bind.
        """
        names = set(Nimbus.AXIS_NAMES.values()) | set(Nimbus.BUTTON_NAMES.values())
        assert not names & {'hmm', 'what'}


class TestSequentialButtonBlock(unittest.TestCase):
    """
    `hid-generic` numbers the buttons in descriptor order rather than by
    meaning, so this pad's codes deliberately do not line up with the
    Xbox-style ones.  Asserting the difference keeps someone from
    "correcting" it into agreement and moving every face button by one.
    """

    def test_the_buttons_run_consecutively(self):
        assert sorted(Nimbus.BUTTON_NAMES) == list(range(0x130, 0x138))

    def test_the_face_buttons_disagree_with_the_measured_pad(self):
        shared = set(Nimbus.BUTTON_NAMES) & set(XboxOneJoystick.BUTTON_NAMES)
        disagreements = {
            code
            for code in shared
            if Nimbus.BUTTON_NAMES[code] != XboxOneJoystick.BUTTON_NAMES[code]
        }
        # they agree on A and B and part ways from there
        assert disagreements == {0x133, 0x134, 0x136, 0x137}

    def test_y_is_where_the_xbox_pad_puts_x(self):
        assert Nimbus.BUTTON_NAMES[0x133] == 'y_button'
        assert XboxOneJoystick.BUTTON_NAMES[0x133] == 'x_button'

    def test_the_shoulders_follow_the_face_buttons(self):
        assert Nimbus.BUTTON_NAMES[0x134] == 'left_shoulder'
        assert Nimbus.BUTTON_NAMES[0x135] == 'right_shoulder'
        assert Nimbus.BUTTON_NAMES[0x136] == 'left_trigger_button'
        assert Nimbus.BUTTON_NAMES[0x137] == 'right_trigger_button'


class TestNoAnalogTriggers(unittest.TestCase):

    def test_the_triggers_are_buttons_only(self):
        """
        This driver reports six axes -- two sticks and the hat -- so a
        behavior map binding throttle to left_trigger would bind to nothing.
        """
        assert 'left_trigger' not in Nimbus.AXIS_NAMES.values()
        assert 'right_trigger' not in Nimbus.AXIS_NAMES.values()
        assert 'left_trigger_button' in Nimbus.BUTTON_NAMES.values()
        assert len(Nimbus.AXIS_NAMES) == 6


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(button_index('a_button'), 1)])
        change = pad.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_the_sticks_report_by_name(self):
        pad = make_pad([
            axis_event(axis_index('left_stick_horz'), -32767),
            axis_event(axis_index('right_stick_vert'), 32767),
        ])

        assert pad.poll().axis == 'left_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_the_dpad_reports_discrete_positions(self):
        pad = make_pad([
            axis_event(axis_index('dpad_horiz'), -32767),
            axis_event(axis_index('dpad_vert'), 32767),
        ])

        horiz = pad.poll()
        vert = pad.poll()
        assert (horiz.axis, horiz.axis_value) == ('dpad_horiz', -1.0)
        assert (vert.axis, vert.axis_value) == ('dpad_vert', 1.0)

    def test_a_shoulder_reports_by_name(self):
        pad = make_pad([button_event(button_index('left_shoulder'), 1)])
        assert pad.poll().button == 'left_shoulder'
