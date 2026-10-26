#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.management.joystick_creator import CreateJoystick
from donkeycar.parts.controls.device import ControlChange
from donkeycar.parts.controls.factory import get_input_controller
from donkeycar.parts.controls.gamepads import CustomJoystick
from donkeycar.tests.fake_js import FakeJsDevice, axis_event, button_event


class TestReadingTheDriverCode(unittest.TestCase):
    """
    A control with no built-in name reports as 'button(0x133)', which is
    where the wizard gets the code to write down.
    """

    def test_a_button_code_is_read_back(self):
        assert CreateJoystick.code_for('button(0x133)', ()) == 0x133

    def test_an_axis_code_is_read_back(self):
        assert CreateJoystick.code_for('axis(0x03)', ()) == 0x03

    def test_a_control_that_already_has_a_name_is_skipped(self):
        assert CreateJoystick.code_for('a_button', ()) is None


class TestTheOutput(unittest.TestCase):
    """
    What the wizard prints has to be what the configuration reads, or a
    user pastes it in and nothing happens.
    """

    def setUp(self):
        self.wizard = CreateJoystick()
        self.wizard.button_names = {0x133: 'red_button'}
        self.wizard.axis_names = {0x03: 'throttle_lever'}

    def test_it_writes_the_settings_the_factory_reads(self):
        text = self.wizard.format_dict(
            'JOYSTICK_BUTTON_NAMES', self.wizard.button_names)

        assert text.startswith('JOYSTICK_BUTTON_NAMES = {')
        assert "0x133: 'red_button'," in text

    def test_the_output_is_valid_python(self):
        namespace = {}
        exec(self.wizard.format_dict('JOYSTICK_BUTTON_NAMES',
                                     self.wizard.button_names), namespace)
        assert namespace['JOYSTICK_BUTTON_NAMES'] == {0x133: 'red_button'}

    def test_naming_nothing_writes_none(self):
        """
        So a half-finished run still pastes in without breaking a config.
        """
        assert CreateJoystick.format_dict('JOYSTICK_AXIS_NAMES', {}) == (
            'JOYSTICK_AXIS_NAMES = None')

    def test_what_it_writes_actually_names_the_controls(self):
        """
        End to end: the wizard's output, fed back through the factory, has
        to produce a controller that reports those names.
        """
        class Config:
            CONTROLLER_TYPE = 'custom'
            JOYSTICK_BUTTON_NAMES = {0x133: 'red_button'}
            JOYSTICK_AXIS_NAMES = {0x03: 'throttle_lever'}

        controller = get_input_controller(Config())
        controller._device = FakeJsDevice(
            axis_codes=(0x03,), button_codes=(0x133,))
        controller.init()

        assert controller.button_map == ('red_button',)
        assert controller.axis_map == ('throttle_lever',)


class TestWaitingForAControl(unittest.TestCase):

    def make_wizard(self, events) -> CreateJoystick:
        wizard = CreateJoystick()
        controller = CustomJoystick(device=FakeJsDevice(
            axis_codes=(0x03,), button_codes=(0x133,), events=events))
        controller.init()
        wizard.controller = controller
        return wizard

    def test_a_button_press_is_taken(self):
        wizard = self.make_wizard([button_event(0, 1)])
        kind, code, name = wizard.wait_for_control()

        assert (kind, code) == ('button', 0x133)
        assert name == 'button(0x133)'

    def test_a_button_release_is_not_taken(self):
        """
        Only the press; otherwise letting go answers the next question.
        """
        wizard = self.make_wizard([button_event(0, 0), button_event(0, 1)])
        kind, code, _ = wizard.wait_for_control()

        assert (kind, code) == ('button', 0x133)

    def test_a_real_axis_movement_is_taken(self):
        wizard = self.make_wizard([axis_event(0, 32767)])
        kind, code, _ = wizard.wait_for_control()

        assert (kind, code) == ('axis', 0x03)

    def test_resting_stick_jitter_is_not_taken(self):
        """
        A resting stick trickles small changes continuously -- measured up
        to 0.1 on a real pad -- so taking the first would name whichever
        stick was twitching rather than the control the user pressed.
        """
        jitter = [axis_event(0, int(v * 32767)) for v in (0.05, 0.09, 0.1)]
        wizard = self.make_wizard(jitter + [button_event(0, 1)])
        kind, code, _ = wizard.wait_for_control()

        assert (kind, code) == ('button', 0x133)


class TestNoLongerGeneratesCode(unittest.TestCase):
    """
    The wizard used to write a Python file with a controller class and a
    button-to-behavior map in it.  Naming is configuration now, and what a
    control does is CONTROLLER_BEHAVIOR_MAP, so there is nothing to
    generate and nothing for a user to keep in step with the framework.
    """

    def test_it_writes_no_python_class(self):
        wizard = CreateJoystick()
        wizard.button_names = {0x133: 'red_button'}
        text = wizard.format_dict('JOYSTICK_BUTTON_NAMES', wizard.button_names)

        assert 'class ' not in text
        assert 'JoystickController' not in text
