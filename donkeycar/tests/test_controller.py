#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
What used to be here tested the legacy joystick classes, which are gone.

It called PS3JoystickController's methods one after another and asserted
nothing -- it passed as long as nothing raised, and it could not run at all
without a joystick attached, so on any machine without one it was skipped.
The behaviors those methods held are now individual parts with tests of
their own, which do assert what they do:

    toggle_mode              -> test_recording_behaviors.TogglePilotMode
    toggle_manual_recording  -> test_recording_behaviors.ToggleRecording
    erase_last_N_records     -> test_recording_behaviors.EraseLastNRecords
    set_steering/throttle    -> test_driving_behaviors
    increase/decrease_max_throttle,
    toggle_constant_throttle -> test_throttle_limit_behaviors
    emergency_stop,
    chaos_monkey_*           -> test_safety_behaviors

What remains worth testing here is that the module still gives the
templates what they import from it.
"""

import unittest


class TestWebControllerReExports(unittest.TestCase):
    """
    Five templates do `from donkeycar.parts.controller import
    LocalWebController`, so this module has to keep providing it.
    """

    def test_the_web_controller_is_importable(self):
        from donkeycar.parts.controller import LocalWebController

        assert LocalWebController is not None

    def test_the_fpv_view_is_importable(self):
        from donkeycar.parts.controller import WebFpv

        assert WebFpv is not None


class TestTheLegacyJoystickClassesAreGone(unittest.TestCase):
    """
    Deliberately gone rather than deprecated.  A car importing any of these
    should fail loudly at startup rather than quietly running a controller
    that no longer matches the rest of the framework.
    """

    def assert_gone(self, name: str) -> None:
        import donkeycar.parts.controller as controller

        assert not hasattr(controller, name), f'{name} is still there'

    def test_the_controller_hierarchy_is_gone(self):
        for name in ('JoystickController', 'PS3JoystickController',
                     'PS4JoystickController', 'XboxOneJoystickController',
                     'LogitechJoystickController', 'NimbusController',
                     'WiiUController', 'RC3ChanJoystickController',
                     'JoystickCreatorController', 'get_js_controller'):
            self.assert_gone(name)

    def test_the_device_classes_are_gone(self):
        for name in ('Joystick', 'PS3Joystick', 'PS4Joystick',
                     'XboxOneJoystick', 'LogitechJoystick', 'Nimbus',
                     'WiiU', 'RC3ChanJoystick', 'PyGameJoystick',
                     'RCReceiver', 'JoyStickSub', 'JoyStickPub'):
            self.assert_gone(name)


class TestEverythingMovedSomewhere(unittest.TestCase):
    """
    Every class the old module had is either replaced or deliberately
    dropped, and this says which -- so the module docstring's list of where
    things went cannot go stale without a test noticing.
    """

    def test_the_gamepads_moved(self):
        from donkeycar.parts.controls.gamepads import (  # noqa: F401
            LogitechJoystick, Nimbus, PS3Joystick, PS3JoystickOld,
            PS3JoystickPC, PS3JoystickSixAd, PS4Joystick, RC3ChanJoystick,
            WiiU, XboxOneJoystick,
        )

    def test_the_pygame_controllers_moved(self):
        from donkeycar.parts.controls.pygame_device import (  # noqa: F401
            PyGameController, PyGamePS4Joystick,
        )

    def test_the_rc_receiver_moved(self):
        from donkeycar.parts.controls.rc import RCReceiver  # noqa: F401

    def test_the_networked_joystick_moved(self):
        from donkeycar.parts.controls.network import (  # noqa: F401
            ControllerPublisher, NetworkedController,
        )

    def test_the_factory_replaced_get_js_controller(self):
        from donkeycar.parts.controls.factory import (  # noqa: F401
            get_input_controller,
        )

    def test_the_controller_methods_became_parts(self):
        """
        JoystickController has no replacement class on purpose; each of its
        methods is a part now, which is what makes them rebindable.
        """
        from donkeycar.parts.controls.behaviors import (  # noqa: F401
            AdjustMaxThrottle, ChaosMonkey, EmergencyStop, EraseLastNRecords,
            ToggleConstantThrottle, TogglePilotMode, ToggleRecording,
            UserSteering, UserThrottle,
        )
