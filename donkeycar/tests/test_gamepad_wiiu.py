#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import PS3Joystick, WiiU, XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device, and less certain than most: the legacy
# map was transcribed from a third-party config and shipped with "need
# testing!" attached.
WIIU_AXIS_CODES = tuple(sorted(WiiU.AXIS_NAMES))
WIIU_BUTTON_CODES = tuple(sorted(WiiU.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> WiiU:
    device = FakeJsDevice(
        name='Nintendo Wii U Pro Controller',
        axis_codes=WIIU_AXIS_CODES,
        button_codes=WIIU_BUTTON_CODES,
        events=events,
    )
    pad = WiiU(device=device, **kwargs)
    pad.init()
    return pad


def axis_index(name: str) -> int:
    return WIIU_AXIS_CODES.index(
        next(c for c, n in WiiU.AXIS_NAMES.items() if n == name)
    )


def button_index(name: str) -> int:
    return WIIU_BUTTON_CODES.index(
        next(c for c, n in WiiU.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = WiiU


class TestTheDpadDefects(unittest.TestCase):
    """
    The legacy map had two problems in the dpad, one cosmetic and one that
    stopped a direction working at all.
    """

    def test_no_name_contains_stray_punctuation(self):
        """
        Legacy wrote 'PAD_DOWN,' -- a comma inside the string rather than
        after it -- so the event key carried the comma too.
        """
        names = set(WiiU.AXIS_NAMES.values()) | set(WiiU.BUTTON_NAMES.values())
        assert [n for n in names if ',' in n or n != n.strip()] == []

    def test_the_dpad_run_is_unbroken(self):
        """
        Up, down, left and right are 0x220 to 0x223.  Legacy had three of
        them right and put down on 0x224, which is not a dpad code, so dpad
        down could never fire and 0x221 went unnamed.
        """
        dpad = {c: n for c, n in WiiU.BUTTON_NAMES.items() if n.startswith('dpad_')}
        assert dpad == {
            0x220: 'dpad_up',
            0x221: 'dpad_down',
            0x222: 'dpad_left',
            0x223: 'dpad_right',
        }

    def test_the_dpad_matches_the_other_pad_that_uses_buttons(self):
        for code in (0x220, 0x221, 0x222, 0x223):
            assert WiiU.BUTTON_NAMES[code] == PS3Joystick.BUTTON_NAMES[code]


class TestNintendoFaceButtonLayout(unittest.TestCase):
    """
    Nintendo arranges the face buttons the opposite way round from everyone
    else, and the codes follow the position rather than the letter.  This
    looks like a transposition bug, so it is asserted deliberately.
    """

    def test_a_and_b_are_swapped_relative_to_the_measured_pad(self):
        assert WiiU.BUTTON_NAMES[0x130] == 'b_button'
        assert WiiU.BUTTON_NAMES[0x131] == 'a_button'

        assert XboxOneJoystick.BUTTON_NAMES[0x130] == 'a_button'
        assert XboxOneJoystick.BUTTON_NAMES[0x131] == 'b_button'

    def test_x_and_y_keep_the_usual_codes(self):
        assert WiiU.BUTTON_NAMES[0x133] == 'x_button'
        assert WiiU.BUTTON_NAMES[0x134] == 'y_button'

    def test_the_bottom_button_is_the_south_code_on_both_pads(self):
        """
        The codes agree on position; only the letters printed there differ.
        """
        assert 0x130 in WiiU.BUTTON_NAMES  # BTN_SOUTH, the bottom button
        assert 0x130 in XboxOneJoystick.BUTTON_NAMES


class TestSharedControls(unittest.TestCase):

    def test_the_shoulders_match_the_measured_pad(self):
        assert WiiU.BUTTON_NAMES[0x136] == XboxOneJoystick.BUTTON_NAMES[0x136]
        assert WiiU.BUTTON_NAMES[0x137] == XboxOneJoystick.BUTTON_NAMES[0x137]

    def test_the_sticks_match_the_measured_pad(self):
        for code in WiiU.AXIS_NAMES:
            assert WiiU.AXIS_NAMES[code] == XboxOneJoystick.AXIS_NAMES[code]

    def test_there_are_no_analog_triggers(self):
        assert 'left_trigger' not in WiiU.AXIS_NAMES.values()
        assert 'left_trigger_button' in WiiU.BUTTON_NAMES.values()
        assert len(WiiU.AXIS_NAMES) == 4


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(button_index('a_button'), 1)])
        change = pad.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_dpad_down_now_fires(self):
        pad = make_pad([button_event(button_index('dpad_down'), 1)])
        assert pad.poll().button == 'dpad_down'

    def test_the_sticks_report_by_name(self):
        pad = make_pad([
            axis_event(axis_index('left_stick_horz'), -32767),
            axis_event(axis_index('right_stick_vert'), 32767),
        ])

        assert pad.poll().axis == 'left_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_select_and_start_report(self):
        pad = make_pad([
            button_event(button_index('select'), 1),
            button_event(button_index('start'), 1),
        ])

        assert pad.poll().button == 'select'
        assert pad.poll().button == 'start'
