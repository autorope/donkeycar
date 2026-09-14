#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import XboxOneJoystick
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    GamepadMapChecks,
    axis_event,
    button_event,
)

# Exactly what a 'Microsoft X-Box One S pad' reported through the xpad
# driver on 2026-08-31.  Pinning the real enumeration is what makes these
# tests worth more than a check that the map agrees with itself: a map can
# be perfectly self-consistent and still describe a different device.
XBOX_AXIS_CODES = (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x10, 0x11)
XBOX_BUTTON_CODES = (
    0x130, 0x131, 0x133, 0x134, 0x136, 0x137,
    0x13A, 0x13B, 0x13C, 0x13D, 0x13E,
)


def make_pad(events=(), **kwargs) -> XboxOneJoystick:
    device = FakeJsDevice(
        name='Microsoft X-Box One S pad',
        axis_codes=XBOX_AXIS_CODES,
        button_codes=XBOX_BUTTON_CODES,
        events=events,
    )
    pad = XboxOneJoystick(device=device, **kwargs)
    pad.init()
    return pad


class TestMapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = XboxOneJoystick


class TestMapCoversTheDevice(unittest.TestCase):
    """
    Every control the real pad reports must get a real name.  The legacy
    map failed exactly here: it named codes the device never sends and left
    the ones it does send unnamed.
    """

    def test_every_axis_is_named(self):
        unnamed = [n for n in make_pad().axis_map if n.startswith('axis(')]
        assert unnamed == []

    def test_every_button_is_named(self):
        unnamed = [n for n in make_pad().button_map if n.startswith('button(')]
        assert unnamed == []

    def test_the_map_names_nothing_the_device_lacks(self):
        """
        A name for a code the pad never sends is a control the user can bind
        a behavior to and then watch do nothing.  Legacy bound Forza mode to
        two such names, so it never once ran.
        """
        extra_axes = set(XboxOneJoystick.AXIS_NAMES) - set(XBOX_AXIS_CODES)
        extra_buttons = set(XboxOneJoystick.BUTTON_NAMES) - set(XBOX_BUTTON_CODES)

        assert extra_axes == set()
        assert extra_buttons == set()

    def test_the_device_has_the_expected_shape(self):
        pad = make_pad()
        assert len(pad.axis_map) == 8
        assert len(pad.button_map) == 11


class TestMeasuredAxisAttribution(unittest.TestCase):
    """
    Each of these was established by moving one control in isolation with
    the axis events timestamped; see CONTROLLER_EVENTS_PLAN.md.  Legacy had
    all four of them wrong.
    """

    def test_left_trigger(self):
        assert XboxOneJoystick.AXIS_NAMES[0x02] == 'left_trigger'

    def test_right_trigger(self):
        assert XboxOneJoystick.AXIS_NAMES[0x05] == 'right_trigger'

    def test_right_stick_horizontal(self):
        assert XboxOneJoystick.AXIS_NAMES[0x03] == 'right_stick_horz'

    def test_right_stick_vertical(self):
        assert XboxOneJoystick.AXIS_NAMES[0x04] == 'right_stick_vert'

    def test_triggers_are_not_the_right_stick(self):
        """
        The specific legacy defect: 0x02 and 0x05 were called the right
        stick, so an Xbox user's 'right stick' was really their triggers,
        sitting pegged at -1.0 whenever they were not being squeezed.
        """
        assert XboxOneJoystick.AXIS_NAMES[0x02] != 'right_stick_horz'
        assert XboxOneJoystick.AXIS_NAMES[0x05] != 'right_stick_vert'


class TestPolling(unittest.TestCase):

    def test_a_face_button_reports_by_name(self):
        pad = make_pad([button_event(0, 1)])
        change = pad.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_the_stick_press_buttons_report(self):
        # index 9 and 10 are 0x13d and 0x13e, unnamed by the legacy map
        pad = make_pad([button_event(9, 1), button_event(10, 1)])

        assert pad.poll().button == 'left_stick_press'
        assert pad.poll().button == 'right_stick_press'

    def test_a_trigger_reports_by_name(self):
        # index 2 is 0x02, the left trigger
        pad = make_pad([axis_event(2, 32767)])
        change = pad.poll()

        assert change.axis == 'left_trigger'
        assert change.axis_value == 1.0

    def test_a_released_trigger_reads_full_negative(self):
        """
        Triggers rest at -1.0 rather than centring at 0.0, as measured.  A
        part that assumes a trigger centres will read 'released' as full
        deflection.
        """
        pad = make_pad([axis_event(5, -32767)])
        change = pad.poll()

        assert change.axis == 'right_trigger'
        assert change.axis_value == -1.0

    def test_the_right_stick_reports_by_name(self):
        # indexes 3 and 4 are 0x03 and 0x04, unnamed by the legacy map
        pad = make_pad([axis_event(3, -32767), axis_event(4, 32767)])

        assert pad.poll().axis == 'right_stick_horz'
        assert pad.poll().axis == 'right_stick_vert'

    def test_the_dpad_reports_discrete_positions(self):
        """
        The dpad is an axis pair reporting only -1, 0 and +1, as measured.
        """
        pad = make_pad([
            axis_event(6, -32767),
            axis_event(6, 0),
            axis_event(7, 32767),
        ])

        assert [(c.axis, c.axis_value) for c in (pad.poll() for _ in range(3))] == [
            ('dpad_horiz', -1.0),
            ('dpad_horiz', 0.0),
            ('dpad_vert', 1.0),
        ]


class TestJitterFilter(unittest.TestCase):

    def test_resting_stick_jitter_can_be_filtered(self):
        """
        The test pad's resting sticks produced a steady trickle of events up
        to about 0.1; measured values were 0.048, 0.068 and 0.099.
        """
        jitter = [axis_event(3, int(v * 32767)) for v in (0.048, 0.068, 0.099)]
        pad = make_pad(jitter, axis_epsilon=0.1)

        assert [pad.poll().axis for _ in jitter] == [None, None, None]

    def test_a_real_movement_still_gets_through(self):
        pad = make_pad([axis_event(3, -32767)], axis_epsilon=0.1)
        assert pad.poll().axis == 'right_stick_horz'
