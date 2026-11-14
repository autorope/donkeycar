#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checks the claims CONTROLLER_MIGRATION.md makes.

A migration guide that has drifted from the code is worse than none: it
sends someone to change a setting that no longer exists, or promises a name
that was renamed again afterwards.
"""

import unittest

from donkeycar.parts.controls import mapping as behaviors
from donkeycar.parts.controls.factory import (
    CONTROLLER_TYPES,
    DEFAULT_BEHAVIOR_MAPS,
    get_behavior_map,
    get_input_controller,
)
from donkeycar.parts.controls.gamepads import (
    Nimbus,
    PS3Joystick,
    PS4Joystick,
    WiiU,
    XboxOneJoystick,
)
from donkeycar.parts.controls.pygame_device import PyGamePS4Joystick


class TestTheRenameTable(unittest.TestCase):
    """
    Every 'new name' the table promises has to exist on the pad it names.
    """

    def assert_named(self, pad, *names: str) -> None:
        available = set(pad.AXIS_NAMES.values()) | set(pad.BUTTON_NAMES.values())
        for name in names:
            assert name in available, f'{pad.__name__} has no {name!r}'

    def test_shoulders_and_triggers(self):
        self.assert_named(PS3Joystick, 'left_shoulder', 'right_shoulder',
                          'left_trigger_button', 'right_trigger_button',
                          'left_trigger', 'right_trigger')
        self.assert_named(PS4Joystick, 'left_shoulder', 'right_shoulder',
                          'left_trigger_button', 'right_trigger_button')

    def test_stick_presses(self):
        self.assert_named(PS3Joystick, 'left_stick_press', 'right_stick_press')
        self.assert_named(PS4Joystick, 'left_stick_press', 'right_stick_press')

    def test_face_buttons(self):
        self.assert_named(Nimbus, 'a_button', 'b_button', 'x_button', 'y_button')
        self.assert_named(WiiU, 'a_button', 'b_button', 'x_button', 'y_button')

    def test_the_xbox_menu_button_is_not_called_options(self):
        """
        'options' is a PlayStation word; the table says so.
        """
        assert 'menu' in XboxOneJoystick.BUTTON_NAMES.values()
        assert 'options' not in XboxOneJoystick.BUTTON_NAMES.values()
        assert 'options' in PS4Joystick.BUTTON_NAMES.values()

    def test_the_nimbus_placeholders_are_gone(self):
        names = set(Nimbus.AXIS_NAMES.values())
        assert not names & {'hmm', 'what'}
        assert {'dpad_horiz', 'dpad_vert'} <= names

    def test_the_wiiu_dpad_has_no_stray_comma(self):
        assert 'dpad_down' in WiiU.BUTTON_NAMES.values()
        assert not any(',' in n for n in WiiU.BUTTON_NAMES.values())

    def test_the_ps4_touchpad_is_only_on_pygame(self):
        """
        On Linux it is a separate input device that never reaches the
        joystick node, so binding it never worked.
        """
        assert 'touchpad' not in PS4Joystick.BUTTON_NAMES.values()
        assert 'pad' not in PS4Joystick.BUTTON_NAMES.values()
        assert 'touchpad' in PyGamePS4Joystick.BUTTON_NAMES.values()


class TestEveryLegacyControllerTypeStillWorks(unittest.TestCase):
    """
    The guide promises that every value that worked before still works.  A
    car that will not start after an upgrade is the worst outcome here.
    """

    LEGACY_TYPES = ('ps3', 'ps3sixad', 'ps4', 'nimbus', 'xbox', 'xboxswapped',
                    'wiiu', 'F710', 'rc3', 'pygame', 'custom', 'mock')

    def test_all_of_them_are_known(self):
        for controller_type in self.LEGACY_TYPES:
            assert controller_type in CONTROLLER_TYPES, controller_type

    def test_all_of_them_build(self):
        class Config:
            JOYSTICK_DEVICE_FILE = '/dev/input/js0'

        for controller_type in self.LEGACY_TYPES:
            Config.CONTROLLER_TYPE = controller_type
            assert get_input_controller(Config()) is not None, controller_type

    def test_all_but_custom_have_a_behavior_map(self):
        class Config:
            JOYSTICK_DEVICE_FILE = '/dev/input/js0'

        for controller_type in self.LEGACY_TYPES:
            if controller_type == 'custom':
                continue  # nothing is named until the user names it
            Config.CONTROLLER_TYPE = controller_type
            assert get_behavior_map(Config()), controller_type


class TestTheRecipes(unittest.TestCase):
    """
    Every recipe in the guide, checked to name something real.
    """

    def test_the_behavior_names_it_imports_exist(self):
        for name in ('STEERING', 'THROTTLE', 'THROTTLE_FORWARD',
                     'THROTTLE_REVERSE', 'TOGGLE_PILOT_MODE',
                     'TOGGLE_RECORDING', 'ERASE_RECORDS', 'EMERGENCY_STOP',
                     'STOP_VEHICLE', 'STOP_VEHICLE_MODIFIER',
                     'INCREASE_MAX_THROTTLE', 'DECREASE_MAX_THROTTLE'):
            assert hasattr(behaviors, name), name
            assert getattr(behaviors, name) in behaviors.KNOWN_BEHAVIORS

    def test_the_swapped_stick_recipe_names_real_axes(self):
        axes = set(XboxOneJoystick.AXIS_NAMES.values())
        assert {'right_stick_horz', 'left_stick_vert'} <= axes

    def test_the_forza_recipe_names_real_axes(self):
        """
        This is the one that never ran: it was bound to codes an Xbox pad
        does not send.
        """
        axes = set(XboxOneJoystick.AXIS_NAMES.values())
        assert {'left_trigger', 'right_trigger'} <= axes

    def test_xboxswapped_swaps_the_sticks(self):
        swapped = DEFAULT_BEHAVIOR_MAPS['xboxswapped']
        normal = DEFAULT_BEHAVIOR_MAPS['xbox']

        assert swapped[behaviors.STEERING] != normal[behaviors.STEERING]
        assert swapped[behaviors.STEERING] == '/event/axis/right_stick_horz'
        assert swapped[behaviors.THROTTLE] == '/event/axis/left_stick_vert'


class TestTheEventKeyTable(unittest.TestCase):
    """
    The table of what a control offers has to match what the event pump
    actually publishes.
    """

    def test_every_key_shape_is_the_one_that_is_published(self):
        from donkeycar.parts.controls.events import (
            BUTTON_DOWN, BUTTON_HOLD, BUTTON_UP, format_axis_event,
            format_axis_key, format_button_click_event, format_button_event,
            format_button_key,
        )

        assert format_button_event('N', BUTTON_DOWN) == '/event/button/N/press'
        assert format_button_event('N', BUTTON_UP) == '/event/button/N/release'
        assert format_button_event('N', BUTTON_HOLD) == '/event/button/N/hold'
        assert format_button_click_event('N', 2) == '/event/button/N/click/2'
        assert format_button_key('N') == '/button/N'
        assert format_axis_event('N') == '/event/axis/N'
        assert format_axis_key('N') == '/axis/N'


class TestSettingsTheGuideSaysAreGone(unittest.TestCase):
    """
    The guide tells people to delete these.  If a template started reading
    one again, the advice would be wrong.
    """

    RETIRED = ('AI_LAUNCH_ENABLE_BUTTON', 'SAVE_PATH_BTN', 'LOAD_PATH_BTN',
               'ERASE_PATH_BTN', 'RESET_ORIGIN_BTN', 'TOGGLE_RECORDING_BTN',
               'INC_PID_P_BTN', 'DEC_PID_P_BTN', 'INC_PID_D_BTN',
               'DEC_PID_D_BTN')

    def test_no_template_reads_them(self):
        import pathlib

        templates = pathlib.Path('donkeycar/templates')
        if not templates.is_dir():  # running from an installed package
            return

        for path in templates.glob('*.py'):
            if path.name.startswith('cfg_'):
                continue  # configs may still define them; templates must not read them
            source = path.read_text()
            for setting in self.RETIRED:
                # mentions count too: the guide tells people to delete these,
                # so a comment still naming one sends them looking for it
                assert setting not in source, f'{path.name} mentions {setting}'
