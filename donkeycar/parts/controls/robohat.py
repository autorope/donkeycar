#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The RoboHAT MM1 by Robotics Masters, which reads an RC receiver on its own
SAMD51 and reports the result over a serial line.

@author: ezward
"""

import logging
from collections import deque
from typing import Any, Protocol

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

#: The MM1 reports servo pulse widths in microseconds.
MIN_PULSE_WIDTH = 1000.0
MID_PULSE_WIDTH = 1500.0
MAX_PULSE_WIDTH = 2000.0

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1.0

#: Positions are rounded to this many places, as the legacy part did.  It
#: is coarse -- about two hundred steps across the travel -- but changing it
#: would change how every existing MM1 car steers, so it stays.
POSITION_PLACES = 2


class SerialPort(Protocol):
    """
    The seam between RoboHATController and pyserial, so the controller can
    be tested with no serial port and no hardware.
    """

    def open(self) -> None:
        """
        Open the port.  Raises OSError if it cannot be opened.
        """
        ...

    def readline(self) -> str:
        """
        One line from the port, or '' if none arrived before the timeout.
        """
        ...

    def close(self) -> None: ...


class RealSerialPort:
    """
    A pyserial port.  Imported lazily, since most cars have no MM1.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: Any = None

    def open(self) -> None:
        try:
            import serial
        except ModuleNotFoundError as e:
            raise OSError(
                'PySerial is not installed; try `pip install pyserial`.'
            ) from e

        try:
            self._serial = serial.Serial(
                self._port, self._baudrate, timeout=self._timeout
            )
        except serial.SerialException as e:
            raise OSError(f'Could not open {self._port}: {e}') from e

    def readline(self) -> str:
        if self._serial is None:
            return ''
        line: bytes = self._serial.readline()
        return line.decode(errors='replace').strip()

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None


class RoboHATController(AbstractInputController):
    """
    Reads steering and throttle from a RoboHAT MM1.

    The MM1 does the radio work on its own microcontroller and sends the
    result down a serial line as two pulse widths per line, steering first:

        1500, 1500

    Reports them as the axes steering and throttle over -1.0 to 1.0, the
    same range every other controller here uses, so nothing downstream needs
    to know an MM1 is involved.

    Steering is reported inverted with respect to pulse width -- a rising
    pulse turns left -- which is how the legacy part behaved and how MM1
    cars are wired.  steering_mid is the pulse width the wheel rests at, and
    the two halves of the travel are scaled separately so a receiver whose
    centre is off-centre still reaches full lock both ways.

    As with the RC receiver, deciding the pilot mode and whether to record
    is not this layer's business; the legacy part did both here, and binding
    them to fixed channels is what made the old controllers unremappable.

    NOT VERIFIED against hardware.  The conversion is carried over
    unchanged, and its arithmetic is pinned by the same values the existing
    RoboHAT tests use.

    One thing worth someone checking who has the hardware: the legacy part
    took MM1_STOPPED_PWM, MM1_MAX_FORWARD and MM1_MAX_REVERSE and mapped
    throttle through them twice -- raw range into the configured range, then
    the configured range into -1..1.  Those two maps cancel exactly, so the
    three settings had no effect whatever on throttle.  This keeps that
    behavior rather than quietly changing how every MM1 car drives, but if
    they were meant to do something, they never did it.
    """

    #: What the two numbers on each line are called.
    CHANNEL_NAMES = ('steering', 'throttle')

    def __init__(
        self,
        port: SerialPort,
        steering_mid: float = MID_PULSE_WIDTH,
        axis_epsilon: float = 0.0,
        show_steering: bool = False,
    ) -> None:
        """
        port:          where the MM1 is talking
        steering_mid:  the pulse width the steering rests at
        axis_epsilon:  smallest movement to report, against receiver jitter
        show_steering: print each steering reading, for calibration
        """
        self._port = port
        self._steering_mid = steering_mid
        self._axis_epsilon = axis_epsilon
        self._show_steering = show_steering

        self._states: dict[str, float] = {}
        self._pending: deque[ControlChange] = deque()
        self._initialized = False

    @property
    def axis_map(self) -> tuple[str, ...]:
        return self.CHANNEL_NAMES

    def init(self) -> bool:
        if self._initialized:
            return True

        try:
            self._port.open()
        except OSError as e:
            logger.warning(f'{type(self).__name__} not initialized: {e}')
            return False

        self._states = {name: 0.0 for name in self.CHANNEL_NAMES}
        self._initialized = True
        return True

    def show_map(self) -> bool:
        if not self._initialized:
            return False
        print(f'2 MM1 channels found: {", ".join(self.CHANNEL_NAMES)}')
        return True

    def poll(self) -> ControlChange:
        if not self._initialized:
            return NO_CHANGE

        if not self._pending:
            self._read()
        if not self._pending:
            return NO_CHANGE
        return self._pending.popleft()

    def shutdown(self) -> None:
        self._initialized = False
        self._pending.clear()
        self._port.close()

    def _read(self) -> None:
        line = self._port.readline()
        if not line:
            return  # the read timed out, which is just a quiet radio

        reading = self._parse(line)
        if reading is None:
            return

        steering_pwm, throttle_pwm = reading
        if self._show_steering:
            print(f'MM1: steering={steering_pwm}')

        self._report('steering', self._to_steering(steering_pwm))
        self._report('throttle', self._to_throttle(throttle_pwm))

    def _parse(self, line: str) -> tuple[float, float] | None:
        """
        Two numbers separated by a comma.  The legacy version split on
        ', ' exactly, so a firmware that omitted the space produced a line
        that silently parsed to nothing.
        """
        parts = [part.strip() for part in line.split(',')]
        if len(parts) != 2:
            logger.debug(f'MM1: ignoring unparseable line {line!r}')
            return None

        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            logger.debug(f'MM1: ignoring non-numeric line {line!r}')
            return None

    def _to_steering(self, pulse_width: float) -> float:
        """
        Pulse width to steering position, inverted, with each half of the
        travel scaled to its own side of centre.
        """
        mid = self._steering_mid
        if pulse_width >= mid:
            span = MAX_PULSE_WIDTH - mid
            value = -(pulse_width - mid) / span if span else 0.0
        else:
            span = mid - MIN_PULSE_WIDTH
            value = (mid - pulse_width) / span if span else 0.0
        return self._clamp(value)

    def _to_throttle(self, pulse_width: float) -> float:
        span = MAX_PULSE_WIDTH - MID_PULSE_WIDTH
        return self._clamp((pulse_width - MID_PULSE_WIDTH) / span)

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(-1.0, min(1.0, value)), POSITION_PLACES)

    def _report(self, name: str, value: float) -> None:
        last = self._states.get(name, 0.0)
        if value == last:
            return
        if (
            self._axis_epsilon > 0.0
            and value != 0.0
            and abs(value - last) < self._axis_epsilon
        ):
            return

        self._states[name] = value
        self._pending.append(ControlChange(axis=name, axis_value=value))
