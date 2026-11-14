#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A test double for pigpio's edge-callback interface, so the RC receiver can
be tested with no pigpio, no GPIO and no transmitter.

Not named test_*.py: this is the fixture, not tests of its own.
"""

from collections.abc import Sequence

from donkeycar.parts.controls.rc import PigpioDevice


class FakePigpioDevice:
    """
    Holds the current pulse width on each channel, as pigpio's callbacks
    do.  A test sets widths and lets the receiver scan.

    Widths are in microseconds: 1000 and 2000 are the ends of a servo
    channel's travel and 1500 is centre.  A channel that has never been
    seen reads 0.0, which is what an unpowered transmitter looks like.
    """

    def __init__(
        self,
        num_channels: int = 3,
        open_error: OSError | None = None,
    ) -> None:
        self.widths = [0.0] * num_channels
        self.open_error = open_error
        self.pins: tuple[int, ...] = ()
        self.open_count = 0
        self.closed = False

    def open(self, pins: Sequence[int]) -> None:
        self.open_count += 1
        if self.open_error is not None:
            raise self.open_error
        self.pins = tuple(pins)

    def pulse_widths(self) -> tuple[float, ...]:
        return tuple(self.widths)

    def close(self) -> None:
        self.closed = True

    # -- what a test drives ------------------------------------------------

    def set_width(self, channel: int, microseconds: float) -> None:
        self.widths[channel] = microseconds

    def set_position(self, channel: int, position: float) -> None:
        """
        Set a channel by where the stick is, -1.0 to 1.0, rather than by
        pulse width.
        """
        self.widths[channel] = 1500.0 + position * 500.0


#: Fail the type check here if the fake stops matching the real contract.
_protocol_check: PigpioDevice = FakePigpioDevice()
