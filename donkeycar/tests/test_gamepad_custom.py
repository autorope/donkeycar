#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.gamepads import CustomJoystick, XboxOneJoystick
from donkeycar.tests.fake_js import FakeJsDevice, axis_event, button_event

# a pad nothing has a map for: some codes that look like a gamepad's, some
# that do not
UNKNOWN_AXIS_CODES = (0x00, 0x01, 0x07)
UNKNOWN_BUTTON_CODES = (0x130, 0x2FF)


def make_pad(events=(), **kwargs) -> CustomJoystick:
    device = FakeJsDevice(
        name='Some Unsupported Controller',
        axis_codes=UNKNOWN_AXIS_CODES,
        button_codes=UNKNOWN_BUTTON_CODES,
        events=events,
    )
    pad = CustomJoystick(device=device, **kwargs)
    pad.init()
    return pad


class TestWorksWithNoMapAtAll(unittest.TestCase):
    """
    An unsupported pad has to be usable before anyone can name anything on
    it -- you cannot write the map until you can see what the device sends.
    """

    def test_it_declares_nothing(self):
        assert CustomJoystick.AXIS_NAMES == {}
        assert CustomJoystick.BUTTON_NAMES == {}

    def test_every_control_still_gets_a_usable_name(self):
        pad = make_pad()

        assert pad.axis_map == ('axis(0x00)', 'axis(0x01)', 'axis(0x07)')
        assert pad.button_map == ('button(0x130)', 'button(0x2ff)')

    def test_the_default_names_carry_the_code_to_map(self):
        """
        The default name is the driver code, so show_map() tells the user
        exactly what to put in myconfig.py.
        """
        pad = make_pad()
        assert pad.show_map() is True
        assert all('0x' in name for name in pad.axis_map + pad.button_map)

    def test_it_polls_by_the_default_names(self):
        pad = make_pad([button_event(1, 1), axis_event(2, 32767)])

        assert pad.poll().button == 'button(0x2ff)'
        assert pad.poll().axis == 'axis(0x07)'


class TestNamingFromConfig(unittest.TestCase):
    """
    The path a user takes: run it, read show_map(), name the controls that
    matter in myconfig.py.
    """

    def test_named_controls_take_the_given_name(self):
        pad = make_pad(
            axis_names={0x07: 'throttle_lever'},
            button_names={0x2FF: 'red_button'},
        )

        assert 'throttle_lever' in pad.axis_map
        assert 'red_button' in pad.button_map

    def test_unnamed_controls_keep_working(self):
        """
        Only the controls worth binding need names; the rest still report.
        """
        pad = make_pad(button_names={0x2FF: 'red_button'})
        assert pad.button_map == ('button(0x130)', 'red_button')

    def test_a_named_control_polls_by_its_new_name(self):
        pad = make_pad(
            [button_event(1, 1)],
            button_names={0x2FF: 'red_button'},
        )
        assert pad.poll().button == 'red_button'


class TestRenamingAPadThatHasAMap(unittest.TestCase):
    """
    The same mechanism retunes a supported pad, so a user who dislikes one
    name does not have to restate the whole map or fork a class.
    """

    def test_one_control_can_be_renamed_without_restating_the_rest(self):
        device = FakeJsDevice(
            axis_codes=tuple(sorted(XboxOneJoystick.AXIS_NAMES)),
            button_codes=tuple(sorted(XboxOneJoystick.BUTTON_NAMES)),
        )
        pad = XboxOneJoystick(device=device, button_names={0x13C: 'guide'})
        pad.init()

        assert 'guide' in pad.button_map
        assert 'xbox' not in pad.button_map
        # everything else is untouched
        assert 'a_button' in pad.button_map
        assert 'left_trigger' in pad.axis_map

    def test_the_class_map_is_not_modified(self):
        device = FakeJsDevice(
            axis_codes=tuple(sorted(XboxOneJoystick.AXIS_NAMES)),
            button_codes=tuple(sorted(XboxOneJoystick.BUTTON_NAMES)),
        )
        XboxOneJoystick(device=device, button_names={0x13C: 'guide'}).init()

        assert XboxOneJoystick.BUTTON_NAMES[0x13C] == 'xbox'
