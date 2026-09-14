#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import (
    PS3Joystick,
    PS3JoystickSixAd,
    XboxOneJoystick,
)
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device.  And unlike the other maps there is no
# convention to fall back on: sixad builds its own uinput device and picks
# its own control codes, so these are its assignments and nothing else.
SIXAD_AXIS_CODES = tuple(sorted(PS3JoystickSixAd.AXIS_NAMES))
SIXAD_BUTTON_CODES = tuple(sorted(PS3JoystickSixAd.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> PS3JoystickSixAd:
    device = FakeJsDevice(
        name='PLAYSTATION(R)3 Controller',
        axis_codes=SIXAD_AXIS_CODES,
        button_codes=SIXAD_BUTTON_CODES,
        events=events,
    )
    pad = PS3JoystickSixAd(device=device, **kwargs)
    pad.init()
    return pad


def index_of(name: str) -> int:
    """Driver index of a named button, as poll() reports it."""
    return SIXAD_BUTTON_CODES.index(
        next(c for c, n in PS3JoystickSixAd.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PS3JoystickSixAd


class TestDeliberatelyDisagreesWithTheConvention(unittest.TestCase):
    """
    This map must NOT match the measured Xbox layout, and that is the point.

    `sixad` numbers its axes sequentially -- left stick, then right stick --
    so the right stick lands on the codes that mean the triggers on every
    in-kernel driver.  These tests exist so that nobody later "fixes" the
    map to agree with the others and quietly moves steering onto a control
    the driver never sends.
    """

    def test_the_right_stick_is_not_where_the_other_pads_put_it(self):
        assert PS3JoystickSixAd.AXIS_NAMES[0x02] == 'right_stick_horz'
        assert PS3JoystickSixAd.AXIS_NAMES[0x03] == 'right_stick_vert'

        # the same codes on the pad we measured
        assert XboxOneJoystick.AXIS_NAMES[0x02] == 'left_trigger'
        assert XboxOneJoystick.AXIS_NAMES[0x03] == 'right_stick_horz'

    def test_the_same_pad_reports_differently_through_the_two_drivers(self):
        """
        PS3Joystick and this are the same physical controller.  The codes
        share almost nothing, which is why driver, not hardware, is what a
        map is written against.
        """
        shared_axes = {
            code
            for code in set(PS3Joystick.AXIS_NAMES) & set(PS3JoystickSixAd.AXIS_NAMES)
            if PS3Joystick.AXIS_NAMES[code] == PS3JoystickSixAd.AXIS_NAMES[code]
        }
        assert shared_axes == {0x00, 0x01}  # only the left stick agrees

        assert set(PS3Joystick.BUTTON_NAMES) & set(PS3JoystickSixAd.BUTTON_NAMES) == {
            0x130,
        }

    def test_there_are_no_analog_triggers(self):
        """
        sixad reports L2 and R2 only as digital buttons, so proportional
        trigger control is unavailable on this driver.  A behavior map that
        binds throttle to left_trigger here would bind to nothing.
        """
        assert 'left_trigger' not in PS3JoystickSixAd.AXIS_NAMES.values()
        assert 'right_trigger' not in PS3JoystickSixAd.AXIS_NAMES.values()
        assert 'left_trigger_button' in PS3JoystickSixAd.BUTTON_NAMES.values()
        assert 'right_trigger_button' in PS3JoystickSixAd.BUTTON_NAMES.values()

    def test_the_buttons_are_in_the_generic_joystick_block(self):
        """
        sixad presents the pad as a plain joystick, so its buttons sit at
        0x120-0x12f rather than the gamepad block at 0x130+.
        """
        gamepad_block = [c for c in PS3JoystickSixAd.BUTTON_NAMES if c >= 0x131]
        assert gamepad_block == []


class TestSharesPlayStationNames(unittest.TestCase):
    """
    Same pad, so a behavior map should mostly carry across between the two
    PS3 drivers even though the codes underneath do not.
    """

    def test_the_button_names_match_the_other_ps3_map(self):
        common = set(PS3Joystick.BUTTON_NAMES.values()) & set(
            PS3JoystickSixAd.BUTTON_NAMES.values()
        )
        # everything sixad reports, except that it has no separate dpad
        # axes and PS3Joystick has no extra buttons sixad lacks
        assert {'cross', 'circle', 'triangle', 'square'} <= common
        assert {'select', 'start', 'ps'} <= common
        assert {'left_shoulder', 'right_shoulder'} <= common
        assert {'left_stick_press', 'right_stick_press'} <= common
        assert {'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right'} <= common


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(index_of('cross'), 1)])
        change = pad.poll()

        assert change.button == 'cross'
        assert change.button_state == 1

    def test_the_ps_button_reports(self):
        pad = make_pad([button_event(index_of('ps'), 1)])
        assert pad.poll().button == 'ps'

    def test_a_dpad_button_reports_by_name(self):
        pad = make_pad([button_event(index_of('dpad_left'), 1)])
        assert pad.poll().button == 'dpad_left'

    def test_the_left_stick_reports_by_name(self):
        pad = make_pad([axis_event(0, -32767), axis_event(1, 32767)])

        assert pad.poll().axis == 'left_stick_horz'
        assert pad.poll().axis == 'left_stick_vert'

    def test_the_right_stick_reports_from_the_sixad_codes(self):
        pad = make_pad([axis_event(2, -32767), axis_event(3, 32767)])

        assert pad.poll().axis == 'right_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'
