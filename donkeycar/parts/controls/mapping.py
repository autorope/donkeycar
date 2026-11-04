#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translating a particular controller's events into the behaviors a template
asks for.

A template should not have to know what controller is attached.  If it
binds a part to '/behavior/toggle_recording', then which button does that
is a line in myconfig.py rather than an edit to the template -- which is
the point of the whole refactor.

@author: ezward
"""

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from prettytable import PrettyTable

from donkeycar.events import OneShotEvents
from donkeycar.memory import Memory
from donkeycar.parts.controls.device import AbstractInputController
from donkeycar.parts.controls.events import (
    AXIS_EVENT,
    AXIS_STATE,
    BUTTON_CLICK,
    BUTTON_EVENT,
    BUTTON_STATE,
)

logger = logging.getLogger(__name__)

BEHAVIOR = '/behavior/'


def format_behavior(name: str) -> str:
    return f'{BEHAVIOR}{name}'


#
# The behaviors the shipped templates bind to.  A template uses these
# rather than a control name, and a controller's map says which of its
# controls drives each one.
#
# Driving
STEERING = format_behavior('steering')
THROTTLE = format_behavior('throttle')
THROTTLE_FORWARD = format_behavior('throttle_forward')
THROTTLE_REVERSE = format_behavior('throttle_reverse')

# Mode and recording
TOGGLE_PILOT_MODE = format_behavior('toggle_pilot_mode')
TOGGLE_RECORDING = format_behavior('toggle_recording')
ERASE_RECORDS = format_behavior('erase_records')
SHOW_RECORD_COUNT = format_behavior('show_record_count')

# Throttle limits
INCREASE_MAX_THROTTLE = format_behavior('increase_max_throttle')
DECREASE_MAX_THROTTLE = format_behavior('decrease_max_throttle')
TOGGLE_CONSTANT_THROTTLE = format_behavior('toggle_constant_throttle')

# Safety
EMERGENCY_STOP = format_behavior('emergency_stop')
STOP_VEHICLE = format_behavior('stop_vehicle')
STOP_VEHICLE_MODIFIER = format_behavior('stop_vehicle_modifier')
CHAOS_MONKEY_LEFT = format_behavior('chaos_monkey_left')
CHAOS_MONKEY_RIGHT = format_behavior('chaos_monkey_right')

# Pilot
ENABLE_AI_LAUNCH = format_behavior('enable_ai_launch')
INCREMENT_BEHAVIOR_STATE = format_behavior('increment_behavior_state')

# Path following
SAVE_PATH = format_behavior('save_path')
LOAD_PATH = format_behavior('load_path')
ERASE_PATH = format_behavior('erase_path')
RESET_ORIGIN = format_behavior('reset_origin')

# Tuning
INCREASE_PID_P = format_behavior('increase_pid_p')
DECREASE_PID_P = format_behavior('decrease_pid_p')
INCREASE_PID_D = format_behavior('increase_pid_d')
DECREASE_PID_D = format_behavior('decrease_pid_d')


#: Every behavior the shipped templates use, for checking a map over.
KNOWN_BEHAVIORS = frozenset({
    STEERING, THROTTLE, THROTTLE_FORWARD, THROTTLE_REVERSE,
    TOGGLE_PILOT_MODE, TOGGLE_RECORDING, ERASE_RECORDS, SHOW_RECORD_COUNT,
    INCREASE_MAX_THROTTLE, DECREASE_MAX_THROTTLE, TOGGLE_CONSTANT_THROTTLE,
    EMERGENCY_STOP, STOP_VEHICLE, STOP_VEHICLE_MODIFIER,
    CHAOS_MONKEY_LEFT, CHAOS_MONKEY_RIGHT,
    ENABLE_AI_LAUNCH, INCREMENT_BEHAVIOR_STATE,
    SAVE_PATH, LOAD_PATH, ERASE_PATH, RESET_ORIGIN,
    INCREASE_PID_P, DECREASE_PID_P, INCREASE_PID_D, DECREASE_PID_D,
})

#: A behavior may be bound to one control or to several.
BehaviorMap = Mapping[str, str | Iterable[str]]


def describe_binding(key: str) -> tuple[str, str]:
    """
    The control a memory key belongs to and what about it a behavior is
    bound to, as a user holding the controller would put it::

        '/event/button/cross/press'    -> ('cross', 'press')
        '/event/button/cross/click/2'  -> ('cross', 'click x2')
        '/event/axis/left_stick_horz'  -> ('left_stick_horz', 'move')
        '/button/view'                 -> ('view', 'held')
        '/axis/right_trigger'          -> ('right_trigger', 'position')

    A key of no recognised form is its own control with no action, so a
    template's own bindings are still listed.
    """
    if key.startswith(BUTTON_EVENT):
        button, _, event = key[len(BUTTON_EVENT):].partition('/')
        kind, _, clicks = event.partition('/')
        if kind == BUTTON_CLICK and clicks not in ('', '1'):
            return button, f'{BUTTON_CLICK} x{clicks}'
        return button, kind
    if key.startswith(AXIS_EVENT):
        return key[len(AXIS_EVENT):], 'move'
    if key.startswith(BUTTON_STATE):
        return key[len(BUTTON_STATE):], 'held'
    if key.startswith(AXIS_STATE):
        return key[len(AXIS_STATE):], 'position'
    return key, ''


class BehaviorEventMapper:
    """
    Publishes a behavior whenever one of the controls bound to it does
    something.

        V.add(BehaviorEventMapper(V.mem, cfg.CONTROLLER_BEHAVIOR_MAP))

    Add it directly after InputControllerEvents, so that a behavior lands
    in the same pass as the event that caused it.

    The map is behavior to control, because that is the question a user is
    answering -- "what toggles recording?" -- and because a behavior can
    then be bound to more than one control at once::

        {
            TOGGLE_RECORDING: [
                '/event/button/circle/press',
                '/event/button/web_w1/press',
            ],
            TOGGLE_PILOT_MODE: '/event/button/share/press',
            STEERING: '/event/axis/left_stick_horz',
        }

    Binding both a gamepad button and a web button to one behavior is the
    case the templates handle today by writing every binding twice, once
    per route in.

    The value is carried across unchanged, so a behavior means exactly what
    the control meant: an axis behavior carries the axis position, and a
    button behavior carries the time it happened.  That is what lets a part
    take a behavior as both its input and its run condition.

    A behavior is published for exactly as long as the control's event
    exists.  Input events are one-shot, so the behaviors they drive are
    one-shot too; control *states* persist, so a behavior bound to one
    persists with it.  Either way a behavior never outlives what caused it.
    """

    def __init__(self, memory: Memory, behavior_map: BehaviorMap) -> None:
        self._memory = memory
        self._bindings = self._normalize(behavior_map)
        self._one_shot = OneShotEvents(memory)

    @staticmethod
    def _normalize(behavior_map: BehaviorMap) -> dict[str, tuple[str, ...]]:
        """
        A behavior may name one control or several; store both the same
        way.
        """
        bindings: dict[str, tuple[str, ...]] = {}
        for behavior, controls in behavior_map.items():
            if isinstance(controls, str):
                bindings[behavior] = (controls,)
            else:
                bindings[behavior] = tuple(controls)
        return bindings

    @property
    def bindings(self) -> dict[str, tuple[str, ...]]:
        return dict(self._bindings)

    def unknown_behaviors(self) -> tuple[str, ...]:
        """
        Behaviors in the map that no shipped template asks for.

        Usually a typo -- a behavior nothing listens to does nothing and
        says nothing -- though a template of one's own may legitimately
        define its own.
        """
        return tuple(sorted(set(self._bindings) - KNOWN_BEHAVIORS))

    def unbound_behaviors(self) -> tuple[str, ...]:
        """
        Behaviors the templates know about that this map does not bind.

        Not an error: a controller with eight buttons cannot drive
        twenty-odd behaviors, and a template only asks for what it needs.
        """
        return tuple(sorted(KNOWN_BEHAVIORS - set(self._bindings)))

    def show_map(self, *controllers: AbstractInputController) -> None:
        """
        Print which controllers are in use and what each of their controls
        does, so that a user can see it without reading the template.

        Call it once the controllers are found -- InputControllerEvents'
        on_ready -- so that it names the device actually found, and so that
        it comes after the start-up logs rather than buried in them.

        A bound control that no controller has is warned about, since
        pressing it does nothing.  A controller that cannot say whether it
        has a control is taken to have it.
        """
        for controller in controllers:
            print(f'Input controller: {controller.description}')

        if not self._bindings:
            print('No behaviors are bound to this controller.')
            return

        table = PrettyTable()
        table.field_names = ['control', 'action', 'behavior']
        table.align = 'l'
        missing: set[str] = set()
        rows = []
        for behavior, controls in self._bindings.items():
            for key in controls:
                control, action = describe_binding(key)
                rows.append((control, action, behavior.removeprefix(BEHAVIOR)))
                if controllers and all(
                    controller.has_control(control) is False
                    for controller in controllers
                ):
                    missing.add(control)
        table.add_rows([list(row) for row in sorted(rows)])
        print(table)

        if missing:
            logger.warning(
                f'These controls are bound but the controller does not have '
                f'them, so they do nothing: {", ".join(sorted(missing))}'
            )

        unknown = self.unknown_behaviors()
        if unknown:
            logger.warning(
                f'These behaviors are bound but nothing uses them, which is '
                f'usually a typo: {", ".join(unknown)}'
            )

    def run(self) -> None:
        behaviors: dict[str, Any] = {}
        for behavior, controls in self._bindings.items():
            for control in controls:
                value = self._memory.get([control])[0]
                if value is not None:
                    # the first control bound to this behavior that has
                    # something to say wins; two at once is a user pressing
                    # both, and doing the behavior twice would be worse
                    behaviors[behavior] = value
                    break

        self._one_shot.emit(behaviors)

    def shutdown(self) -> None:
        self._one_shot.clear()
