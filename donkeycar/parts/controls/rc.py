#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A radio-control receiver read directly off GPIO pins with pigpio, rather
than through a joystick driver.

@author: ezward
"""

import logging
from collections import deque
from collections.abc import Sequence
from typing import Any, Protocol

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

#: A servo channel's pulse width in microseconds at each end of its travel.
MIN_PULSE_WIDTH = 1000.0
MAX_PULSE_WIDTH = 2000.0

#: Channels are reported over the same -1.0 to 1.0 range as a gamepad axis.
MIN_OUT = -1.0
MAX_OUT = 1.0

#: RC receivers jitter continuously, so a small change is not a movement.
DEFAULT_AXIS_EPSILON = 0.01


class PigpioDevice(Protocol):
    """
    The seam between RCReceiver and pigpio, so the receiver can be tested
    on a host with no pigpio, no GPIO and no transmitter.
    """

    def open(self, pins: Sequence[int]) -> None:
        """
        Start watching these GPIO pins.  Raises OSError if pigpio is
        unavailable or the daemon is not running.
        """
        ...

    def pulse_widths(self) -> tuple[float, ...]:
        """
        The most recent pulse width on each pin, in microseconds.  A channel
        that has not been seen yet reads 0.0.
        """
        ...

    def close(self) -> None: ...


class RealPigpioDevice:
    """
    Measures pulse widths with pigpio edge callbacks.
    """

    def __init__(self) -> None:
        self._pi: Any = None
        self._callbacks: list[Any] = []
        self._high_ticks: dict[int, int | None] = {}
        self._widths: dict[int, float] = {}

    def open(self, pins: Sequence[int]) -> None:
        try:
            import pigpio
        except ModuleNotFoundError as e:
            raise OSError('pigpio is not installed.') from e

        pi = pigpio.pi()
        if not pi.connected:
            raise OSError(
                'Could not reach the pigpio daemon; is pigpiod running?'
            )
        self._pi = pi

        for pin in pins:
            self._high_ticks[pin] = None
            self._widths[pin] = 0.0
            pi.set_mode(pin, pigpio.INPUT)
            self._callbacks.append(
                pi.callback(pin, pigpio.EITHER_EDGE, self._on_edge)
            )
        logger.info(f'Watching RC channels on GPIO {list(pins)}')

    def _on_edge(self, gpio: int, level: int, tick: int) -> None:
        """
        Called by pigpio on every edge.  A channel's value is the time the
        pin stayed high, so the rising edge is remembered and the falling
        edge measures against it.
        """
        import pigpio

        if level == 1:
            self._high_ticks[gpio] = tick
        elif level == 0:
            high = self._high_ticks.get(gpio)
            if high is not None:
                self._widths[gpio] = float(pigpio.tickDiff(high, tick))

    def pulse_widths(self) -> tuple[float, ...]:
        return tuple(self._widths[pin] for pin in self._widths)

    def close(self) -> None:
        # The legacy version indexed a list of callbacks with a Channel
        # object -- self.cbs[channel] -- so shutdown raised TypeError every
        # time it ran, and the pigpio connection was never released either.
        for callback in self._callbacks:
            callback.cancel()
        self._callbacks.clear()
        if self._pi is not None:
            self._pi.stop()
            self._pi = None


class RCReceiver(AbstractInputController):
    """
    A three-channel RC receiver wired to GPIO pins.

    Reports each channel as an axis over the same -1.0 to 1.0 range a
    gamepad stick uses, so the parts downstream do not need to know where
    the input came from.  The channels are named steering, throttle and
    switch, matching RC3ChanJoystick, so a behavior map written for one
    transmitter mostly carries to the other.

    One difference from RC3ChanJoystick worth knowing: there the driver
    reports the third channel as two buttons, one per switch position, while
    here it arrives as a raw analog channel like the other two.  Turning it
    into up and down is a decision about how a particular transmitter is
    wired, so it belongs in a behavior part rather than here -- this layer
    reports what the receiver sends and nothing more.

    That is a change from the legacy part, which read the channels and then
    decided the pilot mode and whether to record, all in the same place.
    Those are behaviors, and binding them to fixed channels is exactly what
    made the old controllers impossible to remap.

    Like a gamepad this reports positions rather than events -- pigpio
    updates pulse widths from its own callbacks whenever an edge arrives --
    so poll() drains a queue that a scan refills, and no channel moving at
    the same time as another is lost.

    NOT VERIFIED against hardware.  The pulse-width conversion is carried
    over unchanged from the legacy part.
    """

    #: Channel order is the order the pins are given.
    CHANNEL_NAMES = ('steering', 'throttle', 'switch')

    def __init__(
        self,
        pins: Sequence[int],
        device: PigpioDevice | None = None,
        invert: bool = False,
        axis_epsilon: float = DEFAULT_AXIS_EPSILON,
        channel_names: Sequence[str] | None = None,
    ) -> None:
        """
        pins:          GPIO pins for steering, throttle and the switch
        device:        where to read pulse widths from; defaults to pigpio
        invert:        reverse every channel, for receivers wired backwards
        axis_epsilon:  smallest movement to report, against receiver jitter
        channel_names: names for the channels, if not the default three
        """
        self._pins = tuple(pins)
        self._device: PigpioDevice = (
            device if device is not None else RealPigpioDevice()
        )
        self._invert = invert
        self._axis_epsilon = axis_epsilon
        self._names = tuple(channel_names or self.CHANNEL_NAMES)[: len(self._pins)]

        self._states: dict[str, float] = {}
        self._pending: deque[ControlChange] = deque()
        self._initialized = False

    @property
    def axis_map(self) -> tuple[str, ...]:
        return self._names

    def init(self) -> bool:
        if self._initialized:
            return True

        if len(self._names) != len(self._pins):
            raise ValueError(
                f'{len(self._pins)} pins but {len(self._names)} channel names'
            )

        try:
            self._device.open(self._pins)
        except OSError as e:
            logger.warning(f'{type(self).__name__} not initialized: {e}')
            return False

        self._states = {name: 0.0 for name in self._names}
        self._initialized = True
        return True

    def show_map(self) -> bool:
        if not self._initialized:
            return False

        channels = ', '.join(
            f'{name} (GPIO {pin})' for name, pin in zip(self._names, self._pins)
        )
        print(f'{len(self._names)} RC channels found: {channels}')
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
        widths = self._device.pulse_widths()
        for name, width in zip(self._names, widths):
            self._scan_channel(name, width)

    def _scan_channel(self, name: str, pulse_width: float) -> None:
        if pulse_width <= 0.0:
            # nothing received on this channel yet; a transmitter that is
            # switched off is not a transmitter centred
            return

        value = self._to_axis(pulse_width)
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

    def _to_axis(self, pulse_width: float) -> float:
        """
        A servo pulse width in microseconds, as an axis position.
        """
        span = MAX_PULSE_WIDTH - MIN_PULSE_WIDTH
        travel = (pulse_width - MIN_PULSE_WIDTH) * (MAX_OUT - MIN_OUT) / span
        value = MAX_OUT - travel if self._invert else MIN_OUT + travel
        return max(MIN_OUT, min(MAX_OUT, value))
