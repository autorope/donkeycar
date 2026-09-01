#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Building the configured controller, and the default binding of its controls
to behaviors.

The maps here follow the legacy controllers' bindings wherever they were
sound, so that a car keeps driving the way its owner expects.  Where they
were not sound -- where the legacy binding named a control the driver never
sends -- the note says so.

@author: ezward
"""

import logging
from typing import Any

from donkeycar.parts.controls.device import AbstractInputController
from donkeycar.parts.controls.events import (
    BUTTON_DOWN,
    BUTTON_UP,
    format_axis_event,
    format_axis_key,
    format_button_event,
    format_button_key,
)
from donkeycar.parts.controls.gamepads import (
    CustomJoystick,
    LogitechJoystick,
    Nimbus,
    PS3Joystick,
    PS3JoystickOld,
    PS3JoystickPC,
    PS3JoystickSixAd,
    PS4Joystick,
    RC3ChanJoystick,
    WiiU,
    XboxOneJoystick,
)
from donkeycar.parts.controls.mapping import (
    CHAOS_MONKEY_LEFT,
    CHAOS_MONKEY_RIGHT,
    DECREASE_MAX_THROTTLE,
    EMERGENCY_STOP,
    ERASE_RECORDS,
    INCREASE_MAX_THROTTLE,
    STEERING,
    STOP_VEHICLE,
    STOP_VEHICLE_MODIFIER,
    THROTTLE,
    TOGGLE_CONSTANT_THROTTLE,
    TOGGLE_PILOT_MODE,
    TOGGLE_RECORDING,
    BehaviorMap,
)

logger = logging.getLogger(__name__)

#: The controller classes, by the name a configuration uses.
CONTROLLER_TYPES: dict[str, type[AbstractInputController]] = {
    'xbox': XboxOneJoystick,
    'F710': LogitechJoystick,
    'ps3': PS3Joystick,
    'ps3sixad': PS3JoystickSixAd,
    'ps3old': PS3JoystickOld,
    'ps3pc': PS3JoystickPC,
    'ps4': PS4Joystick,
    'nimbus': Nimbus,
    'wiiu': WiiU,
    'rc3': RC3ChanJoystick,
    'custom': CustomJoystick,
}


def _press(button: str) -> str:
    return format_button_event(button, BUTTON_DOWN)


def _release(button: str) -> str:
    return format_button_event(button, BUTTON_UP)


#
# The face buttons every Xbox-style pad shares, so the four maps that use
# this layout cannot drift apart.  Follows the legacy Xbox bindings.
#
_XBOX_FACE_BUTTONS: dict[str, str] = {
    TOGGLE_PILOT_MODE: _press('a_button'),
    TOGGLE_RECORDING: _press('b_button'),
    ERASE_RECORDS: _press('x_button'),
    EMERGENCY_STOP: _press('y_button'),
}

#
# And the PlayStation ones.  Legacy bound these the same way on PS3 and
# PS4 apart from which button toggles the mode, which differs because the
# pads print different words on it.
#
_PLAYSTATION_FACE_BUTTONS: dict[str, str] = {
    TOGGLE_RECORDING: _press('circle'),
    ERASE_RECORDS: _press('triangle'),
    EMERGENCY_STOP: _press('cross'),
}

_STICKS: dict[str, str] = {
    STEERING: format_axis_event('left_stick_horz'),
    THROTTLE: format_axis_event('right_stick_vert'),
}


DEFAULT_BEHAVIOR_MAPS: dict[str, BehaviorMap] = {
    #
    # Xbox.  Legacy bound the throttle to 'right_stick_vert', which on this
    # driver was really the right trigger -- the axis names were wrong, as
    # 1.7 established by measurement.  The binding here is what the legacy
    # one meant, and now reaches the stick it names.
    #
    'xbox': {
        **_XBOX_FACE_BUTTONS,
        **_STICKS,
        INCREASE_MAX_THROTTLE: _press('right_shoulder'),
        DECREASE_MAX_THROTTLE: _press('left_shoulder'),
        TOGGLE_CONSTANT_THROTTLE: _press('menu'),
        STOP_VEHICLE: _press('xbox'),
        STOP_VEHICLE_MODIFIER: format_button_key('view'),
    },
    #
    # Logitech F710 in XInput mode.  Legacy put the throttle limits on the
    # dpad, which this pad reports as an axis; AxisButton is what makes
    # that bindable, so the template wires those two through it.
    #
    'F710': {
        TOGGLE_PILOT_MODE: _press('start'),
        TOGGLE_RECORDING: _press('b_button'),
        ERASE_RECORDS: _press('y_button'),
        EMERGENCY_STOP: _press('a_button'),
        **_STICKS,
        TOGGLE_CONSTANT_THROTTLE: _press('back'),
        CHAOS_MONKEY_LEFT: format_button_key('left_shoulder'),
        CHAOS_MONKEY_RIGHT: format_button_key('right_shoulder'),
        INCREASE_MAX_THROTTLE: format_axis_key('dpad_vert'),
        DECREASE_MAX_THROTTLE: format_axis_key('dpad_vert'),
        STOP_VEHICLE: _press('logitech'),
        STOP_VEHICLE_MODIFIER: format_button_key('back'),
    },
    #
    # PS3.  Its dpad is four buttons, so the throttle limits bind directly.
    #
    'ps3': {
        **_PLAYSTATION_FACE_BUTTONS,
        **_STICKS,
        TOGGLE_PILOT_MODE: _press('select'),
        INCREASE_MAX_THROTTLE: _press('dpad_up'),
        DECREASE_MAX_THROTTLE: _press('dpad_down'),
        TOGGLE_CONSTANT_THROTTLE: _press('start'),
        CHAOS_MONKEY_LEFT: format_button_key('left_shoulder'),
        CHAOS_MONKEY_RIGHT: format_button_key('right_shoulder'),
        STOP_VEHICLE: _press('ps'),
        STOP_VEHICLE_MODIFIER: format_button_key('select'),
    },
    #
    # PS4.  Same pad shape, but its dpad is an axis pair, so the throttle
    # limits go on the shoulders as the legacy PS4 map had them.
    #
    'ps4': {
        **_PLAYSTATION_FACE_BUTTONS,
        **_STICKS,
        TOGGLE_PILOT_MODE: _press('share'),
        INCREASE_MAX_THROTTLE: _press('left_shoulder'),
        DECREASE_MAX_THROTTLE: _press('right_shoulder'),
        TOGGLE_CONSTANT_THROTTLE: _press('options'),
        STOP_VEHICLE: _press('ps'),
        STOP_VEHICLE_MODIFIER: format_button_key('share'),
    },
    #
    # Nimbus.  Eight buttons and no dpad buttons, so it gets the four
    # behaviors legacy gave it and no more.
    #
    'nimbus': {
        TOGGLE_PILOT_MODE: _press('b_button'),
        ERASE_RECORDS: _press('y_button'),
        EMERGENCY_STOP: _press('a_button'),
        **_STICKS,
        INCREASE_MAX_THROTTLE: _press('right_shoulder'),
        DECREASE_MAX_THROTTLE: _press('left_shoulder'),
    },
    #
    # Wii U Pro.  Nintendo's face buttons sit the opposite way round, and
    # the names follow the position, so a_button here is where an Xbox pad
    # has b_button -- which is why legacy bound the mode toggle to B.
    #
    'wiiu': {
        TOGGLE_PILOT_MODE: _press('b_button'),
        ERASE_RECORDS: _press('y_button'),
        EMERGENCY_STOP: _press('a_button'),
        **_STICKS,
        INCREASE_MAX_THROTTLE: _press('right_shoulder'),
        DECREASE_MAX_THROTTLE: _press('left_shoulder'),
        TOGGLE_CONSTANT_THROTTLE: _press('start'),
    },
    #
    # Three-channel RC transmitter.  Two channels and a switch, so most
    # behaviors have nothing to bind to; that is the point of the map being
    # per-controller.
    #
    'rc3': {
        STEERING: format_axis_event('steering'),
        THROTTLE: format_axis_event('throttle'),
        TOGGLE_PILOT_MODE: _press('switch_down'),
        EMERGENCY_STOP: _press('switch_up'),
    },
    #
    # An unsupported pad names nothing, so nothing can be bound until the
    # user has run it once, read show_map() and named the controls that
    # matter in myconfig.py.
    #
    'custom': {},
}


def get_input_controller(cfg: Any) -> AbstractInputController:
    """
    The controller a configuration asks for.

    Reads CONTROLLER_TYPE, and JOYSTICK_DEVICE_FILE for the device node.
    JOYSTICK_BUTTON_NAMES and JOYSTICK_AXIS_NAMES, if set, are layered over
    whatever the controller class declares, so one control can be renamed
    without restating the map or forking a class.
    """
    controller_type = getattr(cfg, 'CONTROLLER_TYPE', None)
    if controller_type not in CONTROLLER_TYPES:
        raise ValueError(
            f'Unknown CONTROLLER_TYPE {controller_type!r}. '
            f'Try one of: {", ".join(sorted(CONTROLLER_TYPES))}'
        )

    controller_class = CONTROLLER_TYPES[controller_type]
    return controller_class(  # type: ignore[call-arg]
        dev_fn=getattr(cfg, 'JOYSTICK_DEVICE_FILE', '/dev/input/js0'),
        axis_epsilon=getattr(cfg, 'JOYSTICK_AXIS_EPSILON', 0.0),
        button_names=getattr(cfg, 'JOYSTICK_BUTTON_NAMES', None),
        axis_names=getattr(cfg, 'JOYSTICK_AXIS_NAMES', None),
    )


def get_behavior_map(cfg: Any) -> BehaviorMap:
    """
    The behavior bindings a configuration asks for.

    CONTROLLER_BEHAVIOR_MAP replaces the default outright if it is set, so
    a user who wants a different layout writes only the bindings they want
    rather than editing around the ones they do not.
    """
    override: BehaviorMap | None = getattr(cfg, 'CONTROLLER_BEHAVIOR_MAP', None)
    if override:
        return override

    controller_type = str(getattr(cfg, 'CONTROLLER_TYPE', ''))
    behavior_map = DEFAULT_BEHAVIOR_MAPS.get(controller_type)
    if behavior_map is None:
        logger.warning(
            f'No default behavior map for CONTROLLER_TYPE '
            f'{controller_type!r}; set CONTROLLER_BEHAVIOR_MAP in '
            f'myconfig.py to say what its controls should do.'
        )
        return {}
    return behavior_map
