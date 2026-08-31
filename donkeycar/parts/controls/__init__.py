#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Donkeycar input control and event system.

Input devices report button and axis state changes (this package's `device`
and `linux` modules); those changes become one-shot events in the vehicle
memory, which ordinary parts consume as inputs and run_conditions.

See CONTROLLER_EVENTS_PLAN.md and issue #1097.
"""

from donkeycar.parts.controls.device import (
    NO_CHANGE as NO_CHANGE,
    AbstractInputController as AbstractInputController,
    ControlChange as ControlChange,
)
from donkeycar.parts.controls.events import (
    BUTTON_CLICK as BUTTON_CLICK,
    BUTTON_DOWN as BUTTON_DOWN,
    BUTTON_HOLD as BUTTON_HOLD,
    BUTTON_UP as BUTTON_UP,
    InputControllerEvents as InputControllerEvents,
    format_axis_event as format_axis_event,
    format_axis_key as format_axis_key,
    format_button_click_event as format_button_click_event,
    format_button_event as format_button_event,
    format_button_key as format_button_key,
)
from donkeycar.parts.controls.linux import (
    JsDevice as JsDevice,
    JsDeviceInfo as JsDeviceInfo,
    JsEvent as JsEvent,
    LinuxGameController as LinuxGameController,
    LinuxJsDevice as LinuxJsDevice,
)

__all__ = [
    'BUTTON_CLICK',
    'BUTTON_DOWN',
    'BUTTON_HOLD',
    'BUTTON_UP',
    'NO_CHANGE',
    'AbstractInputController',
    'ControlChange',
    'InputControllerEvents',
    'JsDevice',
    'JsDeviceInfo',
    'JsEvent',
    'LinuxGameController',
    'LinuxJsDevice',
    'format_axis_event',
    'format_axis_key',
    'format_button_click_event',
    'format_button_event',
    'format_button_key',
]
