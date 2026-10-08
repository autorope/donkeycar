#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A test double for PyGame's joystick interface, so the PyGame controllers can
be tested on a host with neither PyGame nor a pad attached.

Not named test_*.py: this is the fixture, not tests of its own.
"""

from donkeycar.parts.controls.pygame_device import PyGameDevice, PyGameDeviceInfo


class FakePyGameDevice:
    """
    Holds the current position of every control, as PyGame does.  A test
    moves controls with the set_* methods and then lets the controller
    scan, which is the same shape as the real thing: PyGame never reports
    an event, only where things are now.
    """

    def __init__(
        self,
        name: str = 'Fake PyGame Pad',
        num_axes: int = 4,
        num_buttons: int = 14,
        num_hats: int = 1,
        open_error: OSError | None = None,
    ) -> None:
        self.name = name
        self.num_axes = num_axes
        self.num_buttons = num_buttons
        self.num_hats = num_hats
        self.open_error = open_error

        self.axes = [0.0] * num_axes
        self.buttons = [0] * num_buttons
        self.hats = [(0, 0)] * num_hats

        self.open_count = 0
        self.pump_count = 0
        self.closed = False

    def open(self, which: int) -> PyGameDeviceInfo:
        self.open_count += 1
        if self.open_error is not None:
            raise self.open_error
        return PyGameDeviceInfo(
            name=self.name,
            num_axes=self.num_axes,
            num_buttons=self.num_buttons,
            num_hats=self.num_hats,
        )

    def pump(self) -> None:
        self.pump_count += 1

    def axis(self, index: int) -> float:
        return self.axes[index]

    def button(self, index: int) -> int:
        return self.buttons[index]

    def hat(self, index: int) -> tuple[int, int]:
        return self.hats[index]

    def close(self) -> None:
        self.closed = True

    # -- what a test drives ------------------------------------------------

    def set_axis(self, index: int, value: float) -> None:
        self.axes[index] = value

    def set_button(self, index: int, value: int) -> None:
        self.buttons[index] = value

    def set_hat(self, index: int, position: tuple[int, int]) -> None:
        self.hats[index] = position


#: Fail the type check here if the fake stops matching the real contract.
_protocol_check: PyGameDevice = FakePyGameDevice()
