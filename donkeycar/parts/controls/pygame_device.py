#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game controllers read through PyGame rather than the Linux joystick device
tree, for hosts where /dev/input/js0 is not the way in -- macOS, Windows,
and setups using ScpToolkit.

The module is named pygame_device rather than pygame so that reading a
traceback does not require knowing which one you are looking at.

@author: ezward
"""

import logging
from collections import deque
from collections.abc import Mapping
from typing import Any, NamedTuple, Protocol

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

#: Movement smaller than this reads as centred.  PyGame reports sticks as
#: floats that rarely sit at exactly zero, so without this a resting stick
#: never stops producing changes.
DEFAULT_DEAD_ZONE = 0.07

#: A hat is reported as a pair of positions rather than as buttons, so each
#: one is expanded into four pseudo-buttons in this order.
HAT_DIRECTIONS = ('left', 'right', 'down', 'up')


class PyGameDeviceInfo(NamedTuple):
    name: str
    num_axes: int
    num_buttons: int
    num_hats: int


class PyGameDevice(Protocol):
    """
    The seam between PyGameController and PyGame itself, so the controller
    and its name maps can be tested on a host with no PyGame and no pad.
    """

    def open(self, which: int) -> PyGameDeviceInfo: ...
    def pump(self) -> None: ...
    def axis(self, index: int) -> float: ...
    def button(self, index: int) -> int: ...
    def hat(self, index: int) -> tuple[int, int]: ...
    def close(self) -> None: ...


class RealPyGameDevice:
    """
    Talks to PyGame.  Imported lazily, since most cars never need it.
    """

    def __init__(self) -> None:
        self._joystick: Any = None

    def open(self, which: int) -> PyGameDeviceInfo:
        try:
            import pygame
        except ModuleNotFoundError as e:
            raise OSError(
                'PyGame is not installed, so PyGameController cannot run.'
            ) from e

        pygame.init()
        pygame.joystick.init()
        if which >= pygame.joystick.get_count():
            raise OSError(f'No PyGame joystick at index {which}.')

        joystick = pygame.joystick.Joystick(which)
        joystick.init()
        self._joystick = joystick

        return PyGameDeviceInfo(
            name=joystick.get_name(),
            num_axes=joystick.get_numaxes(),
            num_buttons=joystick.get_numbuttons(),
            num_hats=joystick.get_numhats(),
        )

    def pump(self) -> None:
        import pygame

        # PyGame only refreshes device state when its event queue is
        # serviced, so this has to happen before any read
        pygame.event.get()

    def axis(self, index: int) -> float:
        return float(self._joystick.get_axis(index))

    def button(self, index: int) -> int:
        return int(self._joystick.get_button(index))

    def hat(self, index: int) -> tuple[int, int]:
        horz, vert = self._joystick.get_hat(index)
        return int(horz), int(vert)

    def close(self) -> None:
        if self._joystick is not None:
            self._joystick.quit()
            self._joystick = None


class PyGameController(AbstractInputController):
    """
    A game controller read through PyGame.

    PyGame does not hand out input events; it exposes the current position
    of every control and leaves the caller to notice what moved.  So one
    scan can turn up several changes at once, and this class queues them and
    returns them one per poll().

    That queue is not a detail.  The legacy version scanned every control
    and overwrote a single pair of return values as it went, so when two
    controls moved together it reported only the last and discarded the
    rest -- while still recording their new positions, so the discarded
    changes were never reported at all.  Moving a stick diagonally, which
    changes two axes at once, lost one of them on every scan.

    Names here are keyed by PyGame's own index for each control, not by a
    Linux input code, so a map written for this class does not transfer to
    LinuxGameController or the other way about.

    Hats are expanded into four pseudo-buttons each -- left, right, down,
    up -- numbered after the real buttons, because a hat has no button of
    its own to report.
    """

    #: PyGame button index -> name, supplied by subclasses
    BUTTON_NAMES: Mapping[int, str] = {}

    #: PyGame axis index -> name, supplied by subclasses
    AXIS_NAMES: Mapping[int, str] = {}

    def __init__(
        self,
        device: PyGameDevice | None = None,
        which_js: int = 0,
        button_names: Mapping[int, str] | None = None,
        axis_names: Mapping[int, str] | None = None,
        dead_zone: float = DEFAULT_DEAD_ZONE,
    ) -> None:
        self._button_names: dict[int, str] = {
            **self.BUTTON_NAMES,
            **(button_names or {}),
        }
        self._axis_names: dict[int, str] = {
            **self.AXIS_NAMES,
            **(axis_names or {}),
        }

        self._device: PyGameDevice = (
            device if device is not None else RealPyGameDevice()
        )
        self._which_js = which_js
        self._dead_zone = dead_zone

        self._name = ''
        self._axis_map: tuple[str, ...] = ()
        self._button_map: tuple[str, ...] = ()
        self._num_axes = 0
        self._num_buttons = 0
        self._num_hats = 0
        self._axis_states: list[float] = []
        self._button_states: list[int] = []
        self._pending: deque[ControlChange] = deque()
        self._initialized = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def axis_map(self) -> tuple[str, ...]:
        return self._axis_map

    @property
    def button_map(self) -> tuple[str, ...]:
        """
        Button names by index, the hat pseudo-buttons included.
        """
        return self._button_map

    def init(self) -> bool:
        if self._initialized:
            return True

        try:
            info = self._device.open(self._which_js)
        except OSError as e:
            logger.warning(f'{type(self).__name__} not initialized: {e}')
            return False

        self._name = info.name
        self._num_axes = info.num_axes
        self._num_buttons = info.num_buttons
        self._num_hats = info.num_hats

        total_buttons = info.num_buttons + info.num_hats * len(HAT_DIRECTIONS)
        self._axis_map = tuple(
            self._axis_names.get(i, f'axis({i})') for i in range(info.num_axes)
        )
        self._button_map = tuple(
            self._button_names.get(i, f'button({i})') for i in range(total_buttons)
        )
        self._axis_states = [0.0] * info.num_axes
        self._button_states = [0] * total_buttons

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

        if not self._pending:
            self._scan()
        if not self._pending:
            return NO_CHANGE
        return self._pending.popleft()

    def shutdown(self) -> None:
        self._initialized = False
        self._pending.clear()
        self._device.close()

    def _scan(self) -> None:
        """
        Read every control and queue each one that moved.
        """
        try:
            self._device.pump()
            for index in range(self._num_axes):
                self._scan_axis(index, self._device.axis(index))
            for index in range(self._num_buttons):
                self._scan_button(index, self._device.button(index))
            for index in range(self._num_hats):
                self._scan_hat(index, self._device.hat(index))
        except OSError as e:
            logger.error(f'PyGame controller disconnected: {e}')
            raise

    def _scan_axis(self, index: int, value: float) -> None:
        if abs(value) < self._dead_zone:
            value = 0.0
        if self._axis_states[index] == value:
            return
        self._axis_states[index] = value
        self._pending.append(
            ControlChange(axis=self._axis_map[index], axis_value=value)
        )

    def _scan_button(self, index: int, value: int) -> None:
        state = 1 if value else 0
        if self._button_states[index] == state:
            return
        self._button_states[index] = state
        self._pending.append(
            ControlChange(button=self._button_map[index], button_state=state)
        )

    def _scan_hat(self, index: int, position: tuple[int, int]) -> None:
        horz, vert = position
        # order matches HAT_DIRECTIONS; PyGame reports vert 1 as up
        pressed = (horz == -1, horz == 1, vert == -1, vert == 1)
        first = self._num_buttons + index * len(HAT_DIRECTIONS)
        for offset, is_pressed in enumerate(pressed):
            self._scan_button(first + offset, int(is_pressed))


class PyGamePS4Joystick(PyGameController):
    """
    Sony DualShock 4 through PyGame.

    The same controller as PS4Joystick, indexed by PyGame rather than by
    Linux input codes, so the two maps share no numbering at all: the right
    stick is at axes 2 and 3 here and at 0x03/0x04 there, and this pad's
    buttons are 0 to 13 rather than 0x130 upward.

    PyGame also surfaces the touchpad click as an ordinary button, which the
    Linux driver does not -- there it is a separate input device that never
    reaches the joystick node.

    Windows setup for this pad used ScpToolkit:
    https://github.com/nefarius/ScpToolkit/releases/tag/v1.6.238.16010

    NOT VERIFIED against hardware.  The indices come from the map Donkeycar
    has shipped.
    """

    AXIS_NAMES = {
        0: 'left_stick_horz',
        1: 'left_stick_vert',
        2: 'right_stick_horz',
        3: 'right_stick_vert',
    }

    BUTTON_NAMES = {
        0: 'square',
        1: 'cross',
        2: 'circle',
        3: 'triangle',
        4: 'left_shoulder',
        5: 'right_shoulder',
        6: 'left_trigger_button',
        7: 'right_trigger_button',
        8: 'share',
        9: 'options',
        10: 'left_stick_press',
        11: 'right_stick_press',
        13: 'touchpad',
        # 14-17 are the hat, expanded in HAT_DIRECTIONS order
        14: 'dpad_left',
        15: 'dpad_right',
        16: 'dpad_down',
        17: 'dpad_up',
    }
