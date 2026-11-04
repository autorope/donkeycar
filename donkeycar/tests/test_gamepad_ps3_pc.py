#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import (
    PS3Joystick,
    PS3JoystickOld,
    PS3JoystickPC,
)
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# NOT a capture from a real device.
PC_AXIS_CODES = tuple(sorted(PS3JoystickPC.AXIS_NAMES))
PC_BUTTON_CODES = tuple(sorted(PS3JoystickPC.BUTTON_NAMES))


def make_pad(events=(), **kwargs) -> PS3JoystickPC:
    device = FakeJsDevice(
        name='Sony PLAYSTATION(R)3 Controller',
        axis_codes=PC_AXIS_CODES,
        button_codes=PC_BUTTON_CODES,
        events=events,
    )
    pad = PS3JoystickPC(device=device, **kwargs)
    pad.init()
    return pad


def axis_index(name: str) -> int:
    return PC_AXIS_CODES.index(
        next(c for c, n in PS3JoystickPC.AXIS_NAMES.items() if n == name)
    )


def button_index(name: str) -> int:
    return PC_BUTTON_CODES.index(
        next(c for c, n in PS3JoystickPC.BUTTON_NAMES.items() if n == name)
    )


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PS3JoystickPC


class TestExtendsRatherThanContradicts(unittest.TestCase):
    """
    The one PlayStation variant that is not a different layout.  Every code
    it shares with PS3Joystick means the same thing; it only adds.  If that
    ever stops being true, these two should not be related by inheritance.

    They stay two maps rather than merging into one that names everything.
    Naming an axis the driver does not report is how the legacy Forza mode
    came to be dead code, so a map describes the driver in front of it and
    not the union of every driver the pad has ever had.
    """

    def test_they_stay_two_separate_controller_types(self):
        """
        A deliberate choice, not an omission.  Which one a user wants
        depends on what their driver reports, which only they can see.
        """
        from donkeycar.parts.controls.factory import CONTROLLER_TYPES

        assert CONTROLLER_TYPES['ps3'] is PS3Joystick
        assert CONTROLLER_TYPES['ps3pc'] is PS3JoystickPC
        assert CONTROLLER_TYPES['ps3'] is not CONTROLLER_TYPES['ps3pc']

    def test_the_plain_map_names_only_what_that_driver_reports(self):
        """
        PS3Joystick stays six axes.  Adding the pressure axes to it would
        name controls a Pi driver does not send, which is exactly the
        defect this refactor spent Phase 1 removing.
        """
        assert len(PS3Joystick.AXIS_NAMES) == 6
        assert not any(n.endswith('_pressure')
                       for n in PS3Joystick.AXIS_NAMES.values())

    def test_it_derives_from_the_in_kernel_map(self):
        assert issubclass(PS3JoystickPC, PS3Joystick)

    def test_the_buttons_are_unchanged(self):
        assert PS3JoystickPC.BUTTON_NAMES == PS3Joystick.BUTTON_NAMES

    def test_every_inherited_axis_keeps_its_meaning(self):
        disagreements = {
            code: (PS3Joystick.AXIS_NAMES[code], PS3JoystickPC.AXIS_NAMES[code])
            for code in PS3Joystick.AXIS_NAMES
            if PS3Joystick.AXIS_NAMES[code] != PS3JoystickPC.AXIS_NAMES[code]
        }
        assert disagreements == {}

    def test_it_adds_pressure_and_tilt(self):
        added = set(PS3JoystickPC.AXIS_NAMES) - set(PS3Joystick.AXIS_NAMES)
        added_names = {PS3JoystickPC.AXIS_NAMES[c] for c in added}

        assert all(
            n.endswith('_pressure') or n.startswith('tilt_') for n in added_names
        )
        assert len(added) == 14


class TestPressureBlock(unittest.TestCase):

    def test_the_dpad_pressure_run_has_no_gaps(self):
        """
        As in PS3JoystickOld, legacy left 0x2f unnamed, so a left-dpad press
        arrived as an anonymous axis nothing could bind.
        """
        dpad = [c for c in PS3JoystickPC.AXIS_NAMES if 0x2C <= c <= 0x2F]
        assert sorted(dpad) == [0x2C, 0x2D, 0x2E, 0x2F]

    def test_the_triggers_are_not_in_the_pressure_block(self):
        """
        Deliberate difference from PS3JoystickOld: this driver reports the
        analog triggers at 0x02/0x05 alongside the sticks, so 0x30 and 0x31
        stay unnamed here rather than being filled in by analogy.
        """
        assert 0x30 not in PS3JoystickPC.AXIS_NAMES
        assert 0x31 not in PS3JoystickPC.AXIS_NAMES

        assert PS3JoystickPC.AXIS_NAMES[0x02] == 'left_trigger'
        assert PS3JoystickPC.AXIS_NAMES[0x05] == 'right_trigger'

        # where the other driver puts them
        assert PS3JoystickOld.AXIS_NAMES[0x30] == 'left_trigger'
        assert PS3JoystickOld.AXIS_NAMES[0x31] == 'right_trigger'

    def test_the_face_pressure_axes_match_the_other_pressure_map(self):
        faces = (0x34, 0x35, 0x36, 0x37)
        assert all(
            PS3JoystickPC.AXIS_NAMES[c] == PS3JoystickOld.AXIS_NAMES[c]
            for c in faces
        )


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(button_index('cross'), 1)])
        change = pad.poll()

        assert change.button == 'cross'
        assert change.button_state == 1

    def test_the_sticks_report_from_the_inherited_codes(self):
        pad = make_pad([
            axis_event(axis_index('right_stick_horz'), -32767),
            axis_event(axis_index('right_stick_vert'), 32767),
        ])

        assert pad.poll().axis == 'right_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_a_trigger_reports_by_name(self):
        pad = make_pad([axis_event(axis_index('left_trigger'), 32767)])
        assert pad.poll().axis == 'left_trigger'

    def test_a_pressure_axis_reports_by_name(self):
        pad = make_pad([axis_event(axis_index('triangle_pressure'), 32767)])
        assert pad.poll().axis == 'triangle_pressure'

    def test_the_left_dpad_pressure_is_no_longer_anonymous(self):
        pad = make_pad([axis_event(axis_index('dpad_left_pressure'), 32767)])
        assert pad.poll().axis == 'dpad_left_pressure'

    def test_a_tilt_axis_reports_by_name(self):
        pad = make_pad([axis_event(axis_index('tilt_y'), -16384)])
        assert pad.poll().axis == 'tilt_y'
