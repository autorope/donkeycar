#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web controller re-exports, kept so that `from donkeycar.parts.controller
import LocalWebController` goes on working.

The joystick classes that used to live here are gone.  A controller is now
an AbstractInputController that reports which of its controls moved, and
what those movements mean is decided by parts bound to behaviors -- see
donkeycar/parts/controls/ and issue #1097.

Where things went:

    Joystick, PS3Joystick, PS4Joystick, XboxOneJoystick,
    LogitechJoystick, Nimbus, WiiU, RC3ChanJoystick, and the PS3
    variants          -> donkeycar.parts.controls.gamepads
    PyGameJoystick,
    PyGamePS4Joystick -> donkeycar.parts.controls.pygame_device
    RCReceiver        -> donkeycar.parts.controls.rc
    JoyStickPub,
    JoyStickSub       -> donkeycar.parts.controls.network
    get_js_controller -> donkeycar.parts.controls.factory.get_input_controller

    JoystickController and every *JoystickController subclass have no
    replacement, deliberately.  Each of their methods is now a part in
    donkeycar.parts.controls.behaviors that a template binds to a behavior,
    which is what makes a control remappable without editing a template.
"""

from donkeycar.parts.web_controller.web import LocalWebController
from donkeycar.parts.web_controller.web import WebFpv

__all__ = ['LocalWebController', 'WebFpv']
