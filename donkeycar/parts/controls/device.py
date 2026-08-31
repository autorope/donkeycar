#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The contract an input device must implement to take part in the input
event system.

@author: ezward
"""

import abc
from typing import NamedTuple


class ControlChange(NamedTuple):
    """
    One state change read from an input device.

    A single read yields at most one button change and at most one axis
    change; fields that did not change are None.  This is a NamedTuple so
    that it still unpacks as the four-tuple the older joystick code used::

        button, button_state, axis, axis_value = controller.poll()

    button:       name of the button that changed, else None
    button_state: 1 for down, 0 for up, else None
    axis:         name of the axis that changed, else None
    axis_value:   -1.0 to 1.0 inclusive, else None
    """

    button: str | None = None
    button_state: int | None = None
    axis: str | None = None
    axis_value: float | None = None


#: Returned by poll() when the device had nothing to report.
NO_CHANGE = ControlChange()


class AbstractInputController(abc.ABC):
    """
    An input device that can be polled for button and axis state changes.

    Implement this to make a device -- a game controller, an RC receiver, a
    networked controller -- usable by InputControllerEvents, which turns the
    changes reported here into one-shot events in the vehicle memory.

    Naming is this layer's job: poll() reports the human-readable name of
    the control ('left_stick_horz', 'start'), not the driver's number for
    it, so that the event keys downstream are stable and predictable.
    """

    @abc.abstractmethod
    def init(self) -> bool:
        """
        Attempt to initialize the device.

        Returns True when the device is ready to be polled and False when
        it is not yet available -- an unpaired gamepad, a device node that
        has not appeared yet -- in which case the caller may retry.  Raise
        only for errors that retrying cannot fix.
        """

    @abc.abstractmethod
    def show_map(self) -> bool:
        """
        Print the names of the buttons and axes found on this device.

        Returns True if the device is initialized, False if it is not, in
        which case there is nothing to print.
        """

    @abc.abstractmethod
    def poll(self) -> ControlChange:
        """
        Read one button or axis state change from the device.

        Returns NO_CHANGE when there is nothing to report.  This must be
        called continuously -- it is driven from InputControllerEvents'
        background thread -- because device drivers buffer input, so polling
        slowly returns stale values rather than fewer of them.

        Implementations may block waiting on the device, and are expected to
        be called from a single reader thread.
        """

    def shutdown(self) -> None:
        """
        Release the device.  Safe to call more than once.
        """
