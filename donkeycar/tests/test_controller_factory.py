#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

import pytest

from donkeycar.memory import Memory
from donkeycar.parts.controls.behaviors import AxisButton
from donkeycar.parts.controls.factory import (
    CONTROLLER_TYPES,
    DEFAULT_BEHAVIOR_MAPS,
    get_behavior_map,
    get_input_controller,
)
from donkeycar.parts.controls.gamepads import PS4Joystick, XboxOneJoystick
from donkeycar.parts.controls.mapping import (
    STEERING,
    THROTTLE,
    TOGGLE_RECORDING,
    BehaviorEventMapper,
)


class FakeConfig:
    def __init__(self, **kwargs) -> None:
        self.CONTROLLER_TYPE = 'xbox'
        self.JOYSTICK_DEVICE_FILE = '/dev/input/js0'
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestGetInputController(unittest.TestCase):

    def test_it_builds_the_configured_controller(self):
        controller = get_input_controller(FakeConfig(CONTROLLER_TYPE='xbox'))
        assert isinstance(controller, XboxOneJoystick)

    def test_every_controller_type_can_be_built(self):
        for controller_type in CONTROLLER_TYPES:
            controller = get_input_controller(
                FakeConfig(CONTROLLER_TYPE=controller_type)
            )
            assert isinstance(controller, CONTROLLER_TYPES[controller_type])

    def test_an_unknown_type_says_what_is_available(self):
        with pytest.raises(ValueError, match='Unknown CONTROLLER_TYPE'):
            get_input_controller(FakeConfig(CONTROLLER_TYPE='atari'))

    def test_a_missing_type_is_an_error_rather_than_a_default(self):
        """
        Guessing at a controller would mean a car that drives with the
        wrong bindings rather than telling the user what is wrong.
        """
        config = FakeConfig()
        del config.CONTROLLER_TYPE

        with pytest.raises(ValueError):
            get_input_controller(config)

    def test_a_control_can_be_renamed_from_the_configuration(self):
        controller = get_input_controller(
            FakeConfig(
                CONTROLLER_TYPE='xbox',
                JOYSTICK_BUTTON_NAMES={0x13C: 'guide'},
            )
        )
        assert controller._button_names[0x13C] == 'guide'
        # and the rest of the map is untouched
        assert controller._button_names[0x130] == 'a_button'

    def test_the_class_map_is_not_modified_by_a_rename(self):
        get_input_controller(
            FakeConfig(
                CONTROLLER_TYPE='xbox',
                JOYSTICK_BUTTON_NAMES={0x13C: 'guide'},
            )
        )
        assert XboxOneJoystick.BUTTON_NAMES[0x13C] == 'xbox'


class TestGetBehaviorMap(unittest.TestCase):

    def test_it_returns_the_default_for_the_controller(self):
        behavior_map = get_behavior_map(FakeConfig(CONTROLLER_TYPE='ps4'))
        assert behavior_map == DEFAULT_BEHAVIOR_MAPS['ps4']

    def test_a_configured_map_replaces_the_default(self):
        mine = {TOGGLE_RECORDING: '/event/button/x_button/press'}
        behavior_map = get_behavior_map(
            FakeConfig(CONTROLLER_TYPE='xbox', CONTROLLER_BEHAVIOR_MAP=mine)
        )
        assert behavior_map == mine

    def test_an_unknown_controller_binds_nothing_rather_than_guessing(self):
        assert get_behavior_map(FakeConfig(CONTROLLER_TYPE='atari')) == {}

    def test_the_custom_controller_binds_nothing_until_told(self):
        """
        It names no controls, so there is nothing to bind until the user
        has run it once and read show_map().
        """
        assert get_behavior_map(FakeConfig(CONTROLLER_TYPE='custom')) == {}


class TestTheDefaultMapsAreSound(unittest.TestCase):
    """
    Every default map is checked against the controller it is for.  A
    binding that names a control the pad does not have is a button the user
    presses to no effect, which is how the legacy Forza mode came to be
    dead code for years.
    """

    def control_names(self, controller_type: str) -> set[str]:
        controller_class = CONTROLLER_TYPES[controller_type]
        return set(controller_class.AXIS_NAMES.values()) | set(
            controller_class.BUTTON_NAMES.values()
        )

    def bound_controls(self, behavior_map) -> set[str]:
        """The control name out of each memory key a behavior is bound to."""
        names = set()
        for controls in behavior_map.values():
            controls = [controls] if isinstance(controls, str) else controls
            for control in controls:
                # '/event/button/a_button/press' -> 'a_button'
                # '/axis/dpad_vert'              -> 'dpad_vert'
                parts = control.strip('/').split('/')
                if parts[0] == 'event':
                    names.add(parts[2])
                else:
                    names.add(parts[1])
        return names

    def test_every_binding_names_a_control_the_pad_has(self):
        for controller_type, behavior_map in DEFAULT_BEHAVIOR_MAPS.items():
            if not behavior_map:
                continue
            missing = self.bound_controls(behavior_map) - self.control_names(
                controller_type
            )
            assert missing == set(), f'{controller_type} binds {missing}'

    def test_every_behavior_bound_is_one_a_template_uses(self):
        for controller_type, behavior_map in DEFAULT_BEHAVIOR_MAPS.items():
            mapper = BehaviorEventMapper(Memory(), behavior_map)
            assert mapper.unknown_behaviors() == (), controller_type

    def test_every_pad_can_steer_and_drive(self):
        """
        A car whose controller cannot steer is not a car.
        """
        for controller_type, behavior_map in DEFAULT_BEHAVIOR_MAPS.items():
            if not behavior_map:
                continue
            assert STEERING in behavior_map, controller_type
            assert THROTTLE in behavior_map, controller_type

    def test_the_xbox_throttle_reaches_the_stick_it_names(self):
        """
        Legacy bound the throttle to 'right_stick_vert', which on this
        driver was really the right trigger.  The binding is unchanged in
        intent; the axis it names is now the one measurement found.
        """
        assert DEFAULT_BEHAVIOR_MAPS['xbox'][THROTTLE] == (
            '/event/axis/right_stick_vert'
        )
        assert XboxOneJoystick.AXIS_NAMES[0x04] == 'right_stick_vert'

    def test_no_two_behaviors_on_one_pad_share_a_button_press(self):
        """
        Two behaviors on one press is legal and occasionally wanted, but on
        a default map it is a mistake.
        """
        for controller_type, behavior_map in DEFAULT_BEHAVIOR_MAPS.items():
            presses = [
                controls
                for controls in behavior_map.values()
                if isinstance(controls, str) and controls.endswith('/press')
            ]
            assert len(presses) == len(set(presses)), controller_type


class TestAgainstTheShippedConfiguration(unittest.TestCase):
    """
    The factory has to work with the configuration donkeycar actually
    ships, not only with a test double.
    """

    def test_it_builds_a_controller_from_cfg_complete(self):
        import donkeycar.templates.cfg_complete as cfg

        controller = get_input_controller(cfg)
        assert isinstance(controller, XboxOneJoystick)

    def test_it_finds_a_behavior_map_from_cfg_complete(self):
        import donkeycar.templates.cfg_complete as cfg

        behavior_map = get_behavior_map(cfg)
        assert STEERING in behavior_map
        assert THROTTLE in behavior_map

    def test_the_shipped_config_names_a_controller_that_exists(self):
        import donkeycar.templates.cfg_complete as cfg

        assert cfg.CONTROLLER_TYPE in CONTROLLER_TYPES
        assert cfg.CONTROLLER_TYPE in DEFAULT_BEHAVIOR_MAPS


class TestAxisButton(unittest.TestCase):
    """
    Some pads report the dpad as buttons and others as axes -- measured, a
    DualShock 3 does the first and an Xbox pad the second -- so a behavior
    bound to "dpad up" needs this on the pads taking the second route.
    """

    def test_it_fires_when_the_axis_crosses(self):
        assert AxisButton(direction=-1).run(-1.0) is True

    def test_it_does_not_fire_the_other_way(self):
        assert AxisButton(direction=-1).run(1.0) is False

    def test_it_fires_once_per_push_not_while_held(self):
        """
        Held, this would wind the throttle limit to maximum in a second.
        """
        button = AxisButton(direction=-1)

        assert button.run(-1.0) is True
        assert button.run(-1.0) is False
        assert button.run(-1.0) is False

    def test_releasing_and_pushing_again_fires_again(self):
        button = AxisButton(direction=-1)

        assert button.run(-1.0) is True
        assert button.run(0.0) is False
        assert button.run(-1.0) is True

    def test_a_partial_movement_does_not_count(self):
        assert AxisButton(direction=1, threshold=0.5).run(0.25) is False
        assert AxisButton(direction=1, threshold=0.5).run(0.75) is True

    def test_nothing_yet_is_not_pressed(self):
        assert AxisButton().run(None) is False
        assert AxisButton().run() is False

    def test_two_of_them_split_one_axis(self):
        """
        How a dpad axis is bound: one part per direction.
        """
        up = AxisButton(direction=-1)
        down = AxisButton(direction=1)

        assert (up.run(-1.0), down.run(-1.0)) == (True, False)
        assert (up.run(1.0), down.run(1.0)) == (False, True)
