#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Donkeycar input control and event system.

Input devices report button and axis state changes (this package's `device`
and `linux` modules); those changes become one-shot events in the vehicle
memory, which ordinary parts consume as inputs and run_conditions.

See CONTROLLER_EVENTS_PLAN.md and issue #1097.
"""

from donkeycar.parts.controls.behaviors import (
    PILOT_MODES as PILOT_MODES,
    AdjustMaxThrottle as AdjustMaxThrottle,
    AutoRecordOnThrottle as AutoRecordOnThrottle,
    ChaosMonkey as ChaosMonkey,
    ConstantThrottle as ConstantThrottle,
    EmergencyStop as EmergencyStop,
    EraseLastNRecords as EraseLastNRecords,
    ShowRecordCount as ShowRecordCount,
    StopVehicle as StopVehicle,
    TogglePilotMode as TogglePilotMode,
    ToggleConstantThrottle as ToggleConstantThrottle,
    ToggleRecording as ToggleRecording,
    TriggerThrottle as TriggerThrottle,
    UserSteering as UserSteering,
    UserThrottle as UserThrottle,
)
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
from donkeycar.parts.controls.gamepads import (
    CustomJoystick as CustomJoystick,
    LogitechJoystick as LogitechJoystick,
    Nimbus as Nimbus,
    PS3Joystick as PS3Joystick,
    PS3JoystickOld as PS3JoystickOld,
    PS3JoystickPC as PS3JoystickPC,
    PS3JoystickSixAd as PS3JoystickSixAd,
    PS4Joystick as PS4Joystick,
    RC3ChanJoystick as RC3ChanJoystick,
    WiiU as WiiU,
    XboxOneJoystick as XboxOneJoystick,
)
from donkeycar.parts.controls.web import (
    WebButtonController as WebButtonController,
)
from donkeycar.parts.controls.network import (
    ControllerPublisher as ControllerPublisher,
    MessagePublisher as MessagePublisher,
    MessageSubscriber as MessageSubscriber,
    NetworkedController as NetworkedController,
    ZmqPublisher as ZmqPublisher,
    ZmqSubscriber as ZmqSubscriber,
)
from donkeycar.parts.controls.robohat import (
    RealSerialPort as RealSerialPort,
    RoboHATController as RoboHATController,
    SerialPort as SerialPort,
)
from donkeycar.parts.controls.rc import (
    PigpioDevice as PigpioDevice,
    RCReceiver as RCReceiver,
    RealPigpioDevice as RealPigpioDevice,
)
from donkeycar.parts.controls.pygame_device import (
    PyGameController as PyGameController,
    PyGameDevice as PyGameDevice,
    PyGamePS4Joystick as PyGamePS4Joystick,
    RealPyGameDevice as RealPyGameDevice,
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
    'PILOT_MODES',
    'AbstractInputController',
    'AdjustMaxThrottle',
    'AutoRecordOnThrottle',
    'ChaosMonkey',
    'ConstantThrottle',
    'ControlChange',
    'ControllerPublisher',
    'EmergencyStop',
    'EraseLastNRecords',
    'CustomJoystick',
    'InputControllerEvents',
    'JsDevice',
    'JsDeviceInfo',
    'JsEvent',
    'LinuxGameController',
    'LinuxJsDevice',
    'MessagePublisher',
    'MessageSubscriber',
    'NetworkedController',
    'LogitechJoystick',
    'Nimbus',
    'PS3Joystick',
    'PS3JoystickOld',
    'PS3JoystickPC',
    'PS3JoystickSixAd',
    'PS4Joystick',
    'PigpioDevice',
    'PyGameController',
    'PyGameDevice',
    'PyGamePS4Joystick',
    'RCReceiver',
    'RealPigpioDevice',
    'RealSerialPort',
    'RealPyGameDevice',
    'RoboHATController',
    'SerialPort',
    'ShowRecordCount',
    'StopVehicle',
    'ToggleConstantThrottle',
    'TogglePilotMode',
    'ToggleRecording',
    'TriggerThrottle',
    'UserSteering',
    'UserThrottle',
    'ZmqPublisher',
    'ZmqSubscriber',
    'RC3ChanJoystick',
    'WebButtonController',
    'WiiU',
    'XboxOneJoystick',
    'format_axis_event',
    'format_axis_key',
    'format_button_click_event',
    'format_button_event',
    'format_button_key',
]
