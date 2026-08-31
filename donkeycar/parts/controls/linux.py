#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game controllers read through the Linux joystick device tree,
/dev/input/js0 and friends.

@author: ezward
"""

import array
import logging
import os
import struct
from collections.abc import Mapping, Sequence
from io import BufferedReader
from typing import NamedTuple, Protocol

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

# js_event.type bits, from linux/joystick.h
JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

# ioctl request codes, from linux/joystick.h
JSIOCGAXES = 0x80016A11
JSIOCGBUTTONS = 0x80016A12
JSIOCGAXMAP = 0x80406A32
JSIOCGBTNMAP = 0x80406A34
JSIOCGNAME = 0x80006A13

# a js_event is 8 bytes: u32 time, s16 value, u8 type, u8 number
JS_EVENT_FORMAT = 'IhBB'
JS_EVENT_SIZE = 8

# axis values arrive as a signed 16 bit int
AXIS_SCALE = 32767.0


class JsEvent(NamedTuple):
    """
    One raw event as read from the joystick device.
    """

    time: int
    value: int
    type: int
    number: int


class JsDeviceInfo(NamedTuple):
    """
    What the driver reports about a device when it is opened.

    axis_codes and button_codes are the driver's numbers for each control,
    in the order the driver reports them; that order is the index space the
    events in JsEvent.number refer to.
    """

    name: str
    axis_codes: tuple[int, ...]
    button_codes: tuple[int, ...]


class JsDevice(Protocol):
    """
    The seam between LinuxGameController and the operating system.

    LinuxJsDevice is the real implementation.  Keeping this narrow means the
    controller -- and so every per-gamepad button and axis map built on it --
    can be tested without a physical device attached.
    """

    def open(self) -> JsDeviceInfo:
        """
        Open the device and report the controls it has.  Raises OSError if
        the device is not present or cannot be opened.
        """
        ...

    def read_event(self) -> JsEvent | None:
        """
        Read one event, or None if none is available.
        """
        ...

    def close(self) -> None:
        """
        Release the device.  Safe to call more than once.
        """
        ...


class LinuxJsDevice:
    """
    Reads a Linux joystick device node using ioctl and struct.
    """

    def __init__(self, dev_fn: str = '/dev/input/js0') -> None:
        self.dev_fn = dev_fn
        self._jsdev: BufferedReader | None = None

    def open(self) -> JsDeviceInfo:
        try:
            from fcntl import ioctl
        except ModuleNotFoundError as e:
            raise OSError(
                'No support for the fcntl module; '
                'LinuxJsDevice needs a Linux host.'
            ) from e

        if not os.path.exists(self.dev_fn):
            raise FileNotFoundError(f'No such device: {self.dev_fn}')

        logger.info(f'Opening {self.dev_fn}...')
        # buffered, so that read_event() can peek before it commits to a
        # read that would otherwise block on a partial event
        jsdev = open(self.dev_fn, 'rb')
        self._jsdev = jsdev

        buf = array.array('B', [0] * 64)
        ioctl(jsdev, JSIOCGNAME + (0x10000 * len(buf)), buf)
        name = buf.tobytes().rstrip(b'\x00').decode('utf-8', errors='replace')

        buf = array.array('B', [0])
        ioctl(jsdev, JSIOCGAXES, buf)
        num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(jsdev, JSIOCGBUTTONS, buf)
        num_buttons = buf[0]

        buf = array.array('B', [0] * 0x40)
        ioctl(jsdev, JSIOCGAXMAP, buf)
        axis_codes = tuple(buf[:num_axes])

        btn_buf = array.array('H', [0] * 200)
        ioctl(jsdev, JSIOCGBTNMAP, btn_buf)
        button_codes = tuple(btn_buf[:num_buttons])

        logger.info(f'Device name: {name}')
        return JsDeviceInfo(name, axis_codes, button_codes)

    def read_event(self) -> JsEvent | None:
        jsdev = self._jsdev
        if jsdev is None:
            return None

        # peek first; read() would block until a whole event is available
        if len(jsdev.peek(JS_EVENT_SIZE)) < JS_EVENT_SIZE:
            return None

        evbuf = jsdev.read(JS_EVENT_SIZE)
        if not evbuf or len(evbuf) < JS_EVENT_SIZE:
            return None

        time, value, kind, number = struct.unpack(JS_EVENT_FORMAT, evbuf)
        return JsEvent(time, value, kind, number)

    def close(self) -> None:
        if self._jsdev is not None:
            self._jsdev.close()
            self._jsdev = None


class LinuxGameController(AbstractInputController):
    """
    A game controller on the Linux joystick device tree.

    Subclasses supply the make-specific control names as the class
    constants BUTTON_NAMES and AXIS_NAMES, keyed by the driver's code for
    each control.  Names passed to the constructor are layered on top of
    those, so a user can rename an individual control -- or name the
    controls of a pad we have no built-in map for -- without subclassing.

    Any control with no name gets a default one built from its driver code,
    'button(0x133)' or 'axis(0x03)', so an unmapped pad is still usable and
    its codes are discoverable via show_map().
    """

    #: driver button code -> name, supplied by subclasses
    BUTTON_NAMES: Mapping[int, str] = {}

    #: driver axis code -> name, supplied by subclasses
    AXIS_NAMES: Mapping[int, str] = {}

    def __init__(
        self,
        device: JsDevice | None = None,
        button_names: Mapping[int, str] | None = None,
        axis_names: Mapping[int, str] | None = None,
        dev_fn: str = '/dev/input/js0',
        axis_epsilon: float = 0.0,
    ) -> None:
        """
        device:       where to read events from; defaults to the Linux
                      joystick device node at dev_fn
        button_names: driver button code -> name, overriding BUTTON_NAMES
        axis_names:   driver axis code -> name, overriding AXIS_NAMES
        dev_fn:       device node, used when no device is given
        axis_epsilon: smallest axis movement to report, as a deadband
                      against stick jitter; 0.0 reports every change
        """
        # copy into instance state; a shared mapping that init() went on to
        # mutate would leak one controller's names into the next
        self._button_names: dict[int, str] = {
            **self.BUTTON_NAMES,
            **(button_names or {}),
        }
        self._axis_names: dict[int, str] = {
            **self.AXIS_NAMES,
            **(axis_names or {}),
        }

        self._device: JsDevice = (
            device if device is not None else LinuxJsDevice(dev_fn)
        )
        self._axis_epsilon = axis_epsilon

        self._name = ''
        self._axis_map: tuple[str, ...] = ()
        self._button_map: tuple[str, ...] = ()
        self._axis_states: dict[str, float] = {}
        self._button_states: dict[str, int] = {}
        self._initialized = False

    @property
    def name(self) -> str:
        """
        The device name the driver reported, or '' before init().
        """
        return self._name

    @property
    def axis_map(self) -> tuple[str, ...]:
        """
        Axis names, indexed by the driver's axis number.
        """
        return self._axis_map

    @property
    def button_map(self) -> tuple[str, ...]:
        """
        Button names, indexed by the driver's button number.
        """
        return self._button_map

    def init(self) -> bool:
        if self._initialized:
            return True

        try:
            info = self._device.open()
        except OSError as e:
            logger.warning(f'{type(self).__name__} not initialized: {e}')
            return False

        self._name = info.name
        self._axis_map = tuple(
            self._axis_names.get(code, f'axis(0x{code:02x})')
            for code in info.axis_codes
        )
        self._button_map = tuple(
            self._button_names.get(code, f'button(0x{code:03x})')
            for code in info.button_codes
        )
        self._axis_states = {name: 0.0 for name in self._axis_map}
        self._button_states = {name: 0 for name in self._button_map}

        self._initialized = True
        return True

    def show_map(self) -> bool:
        if not self._initialized:
            return False

        print(f'{len(self._axis_map)} axes found: {", ".join(self._axis_map)}')
        print(
            f'{len(self._button_map)} buttons found: '
            f'{", ".join(self._button_map)}'
        )
        return True

    def poll(self) -> ControlChange:
        if not self._initialized:
            return NO_CHANGE

        event = self._device.read_event()
        if event is None:
            return NO_CHANGE

        # the driver replays the current state of every control when the
        # device is opened; those are not real changes
        if event.type & JS_EVENT_INIT:
            return NO_CHANGE

        if event.type & JS_EVENT_BUTTON:
            return self._button_change(event)

        if event.type & JS_EVENT_AXIS:
            return self._axis_change(event)

        return NO_CHANGE

    def shutdown(self) -> None:
        self._initialized = False
        self._device.close()

    def _button_change(self, event: JsEvent) -> ControlChange:
        button = _name_at(self._button_map, event.number, 'button')
        if button is None:
            return NO_CHANGE

        state = 1 if event.value else 0
        self._button_states[button] = state
        logger.debug(f'button: {button} state: {state}')
        return ControlChange(button=button, button_state=state)

    def _axis_change(self, event: JsEvent) -> ControlChange:
        axis = _name_at(self._axis_map, event.number, 'axis')
        if axis is None:
            return NO_CHANGE

        value = event.value / AXIS_SCALE
        last = self._axis_states.get(axis, 0.0)
        if value == last:
            return NO_CHANGE

        # Compare against the last value we *reported*, not the last one we
        # read, so that jitter is suppressed but a slow, sustained push
        # still gets through once it accumulates past the deadband.  A
        # return to exact center is always reported: swallowing it would
        # leave the throttle or steering stuck a little off zero.
        if (
            self._axis_epsilon > 0.0
            and value != 0.0
            and abs(value - last) < self._axis_epsilon
        ):
            return NO_CHANGE

        self._axis_states[axis] = value
        logger.debug(f'axis: {axis} val: {value}')
        return ControlChange(axis=axis, axis_value=value)


def _name_at(names: Sequence[str], index: int, kind: str) -> str | None:
    """
    Look up a control name by the driver's index for it, tolerating an
    index the driver never declared when the device was opened.
    """
    if 0 <= index < len(names):
        return names[index]
    logger.warning(f'Ignoring event for undeclared {kind} number {index}')
    return None
