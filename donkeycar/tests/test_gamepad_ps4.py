#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import (
    PS3Joystick,
    PS4Joystick,
    XboxOneJoystick,
)
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
    duplicate_literal_keys,
)

# NOT a capture from a real device.
PS4_AXIS_CODES = tuple(sorted(PS4Joystick.AXIS_NAMES))
PS4_BUTTON_CODES = tuple(sorted(PS4Joystick.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> PS4Joystick:
    device = FakeJsDevice(
        name='Sony Interactive Entertainment Wireless Controller',
        axis_codes=PS4_AXIS_CODES,
        button_codes=PS4_BUTTON_CODES,
        events=events,
    )
    pad = PS4Joystick(device=device, **kwargs)
    pad.init()
    return pad


def axis_index(name: str) -> int:
    return PS4_AXIS_CODES.index(
        next(c for c, n in PS4Joystick.AXIS_NAMES.items() if n == name)
    )


def button_index(name: str) -> int:
    return PS4_BUTTON_CODES.index(
        next(c for c, n in PS4Joystick.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PS4Joystick


class TestTheDuplicateKeyDefect(unittest.TestCase):
    """
    The legacy map wrote 0x13a as both 'L3' and 'share', and 0x13b as both
    'R3' and 'options'.  Python keeps the last, so both stick presses were
    silently unreachable -- a control the user could see on the pad and
    never bind.
    """

    def test_the_source_has_no_repeated_keys(self):
        assert duplicate_literal_keys(PS4Joystick) == []

    def test_the_defect_is_invisible_in_the_finished_dict(self):
        """
        Why the check has to read the source: by the time the dict exists,
        the earlier entry is already gone and nothing looks wrong.
        """
        legacy_shape = {0x13A: 'L3', 0x13B: 'R3', 0x13A: 'share', 0x13B: 'options'}  # noqa: F601

        assert legacy_shape == {0x13A: 'share', 0x13B: 'options'}
        assert len(legacy_shape) == 2  # 'L3' and 'R3' left no trace

    def test_the_stick_presses_are_reachable(self):
        """
        The two controls the defect cost.  Both are bindable now.
        """
        names = set(PS4Joystick.BUTTON_NAMES.values())
        assert 'left_stick_press' in names
        assert 'right_stick_press' in names

    def test_share_and_options_keep_their_codes(self):
        assert PS4Joystick.BUTTON_NAMES[0x13A] == 'share'
        assert PS4Joystick.BUTTON_NAMES[0x13B] == 'options'

    def test_the_stick_presses_use_the_thumb_codes(self):
        assert PS4Joystick.BUTTON_NAMES[0x13D] == 'left_stick_press'
        assert PS4Joystick.BUTTON_NAMES[0x13E] == 'right_stick_press'


class TestResolvesTheLegacyDisagreement(unittest.TestCase):
    """
    The legacy PS3 and PS4 maps put the shoulders and triggers on opposite
    codes.  They cannot both be right about the same driver, and the kernel
    headers settle it: BTN_TL is 0x136, BTN_TL2 is 0x138.
    """

    def test_the_shoulders_and_triggers_match_the_other_sony_map(self):
        shared = set(PS4Joystick.BUTTON_NAMES) & set(PS3Joystick.BUTTON_NAMES)
        disagreements = {
            code: (PS4Joystick.BUTTON_NAMES[code], PS3Joystick.BUTTON_NAMES[code])
            for code in shared
            if PS4Joystick.BUTTON_NAMES[code] != PS3Joystick.BUTTON_NAMES[code]
        }
        # only the two buttons whose labels genuinely differ between the pads
        assert set(disagreements) == {0x13A, 0x13B}
        assert disagreements[0x13A] == ('share', 'select')
        assert disagreements[0x13B] == ('options', 'start')

    def test_the_shoulder_is_on_the_shoulder_code(self):
        assert PS4Joystick.BUTTON_NAMES[0x136] == 'left_shoulder'
        assert PS4Joystick.BUTTON_NAMES[0x138] == 'left_trigger_button'

    def test_no_touchpad_is_named(self):
        """
        Legacy called 0x13d 'pad'.  It is BTN_THUMBL, and the touchpad is
        its own input device rather than a button on the joystick node, so
        naming it here would bind a behavior to something never sent.
        """
        assert 'pad' not in PS4Joystick.BUTTON_NAMES.values()


class TestAgreesWithTheMeasuredAxisLayout(unittest.TestCase):

    def test_shared_axis_codes_agree_with_the_measured_pad(self):
        shared = set(PS4Joystick.AXIS_NAMES) & set(XboxOneJoystick.AXIS_NAMES)
        disagreements = {
            code: (PS4Joystick.AXIS_NAMES[code], XboxOneJoystick.AXIS_NAMES[code])
            for code in shared
            if PS4Joystick.AXIS_NAMES[code] != XboxOneJoystick.AXIS_NAMES[code]
        }
        assert disagreements == {}

    def test_the_dpad_is_axes_not_buttons(self):
        """
        Unlike the DualShock 3, whose dpad is four buttons.
        """
        assert PS4Joystick.AXIS_NAMES[0x10] == 'dpad_horiz'
        assert PS4Joystick.AXIS_NAMES[0x11] == 'dpad_vert'
        assert 'dpad_up' not in PS4Joystick.BUTTON_NAMES.values()


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(button_index('cross'), 1)])
        change = pad.poll()

        assert change.button == 'cross'
        assert change.button_state == 1

    def test_the_stick_presses_report(self):
        pad = make_pad([
            button_event(button_index('left_stick_press'), 1),
            button_event(button_index('right_stick_press'), 1),
        ])

        assert pad.poll().button == 'left_stick_press'
        assert pad.poll().button == 'right_stick_press'

    def test_share_and_options_report(self):
        pad = make_pad([
            button_event(button_index('share'), 1),
            button_event(button_index('options'), 1),
        ])

        assert pad.poll().button == 'share'
        assert pad.poll().button == 'options'

    def test_a_trigger_reports_on_both_axis_and_button(self):
        pad = make_pad([
            axis_event(axis_index('left_trigger'), 32767),
            button_event(button_index('left_trigger_button'), 1),
        ])

        assert pad.poll().axis == 'left_trigger'
        assert pad.poll().button == 'left_trigger_button'

    def test_the_dpad_reports_discrete_positions(self):
        pad = make_pad([
            axis_event(axis_index('dpad_horiz'), -32767),
            axis_event(axis_index('dpad_vert'), 32767),
        ])

        horiz = pad.poll()
        vert = pad.poll()
        assert (horiz.axis, horiz.axis_value) == ('dpad_horiz', -1.0)
        assert (vert.axis, vert.axis_value) == ('dpad_vert', 1.0)
