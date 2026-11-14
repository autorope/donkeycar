#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
An opt-in trace of what the controller is doing, for a car that seems to
ignore its pad.

The event pump and the driving behaviors run on every pass, so they are
silent by default.  Set DONKEY_CONTROLLER_DEBUG to turn the trace on:

    DONKEY_CONTROLLER_DEBUG=1 python manage.py drive --js

It is read when each part is constructed, so set it before starting the
car.  The trace logs at INFO, so it shows with the templates' default
logging -- LOGLEVEL=DEBUG would also turn on every other library's debug
output -- and goes to its own logger, TRACE_LOGGER, so it can be silenced
or redirected on its own.

@author: ezward
"""

import logging
import os

#: The environment variable that turns the trace on.
TRACE_ENV = 'DONKEY_CONTROLLER_DEBUG'

#: The spellings of TRACE_ENV that turn the trace on, in any case.
TRACE_ON_VALUES = frozenset({'1', 'true', 'yes', 'on'})

#: The name of the logger the trace goes to.
TRACE_LOGGER = 'donkeycar.parts.controls.trace'

trace_logger = logging.getLogger(TRACE_LOGGER)


def trace_enabled() -> bool:
    """
    True if TRACE_ENV is set to one of TRACE_ON_VALUES.
    """
    value = os.environ.get(TRACE_ENV, '')
    return value.strip().lower() in TRACE_ON_VALUES


def trace(message: str) -> None:
    """
    Write one trace line.  Callers check trace_enabled() first, once.
    """
    trace_logger.info(message)


class ChangeTrace:
    """
    Traces a value a part answers on every pass, but only when it changes,
    so a stick held still logs once rather than at the loop rate.

        self._trace = ChangeTrace('steering') if trace_enabled() else None
        ...
        if self._trace:
            self._trace.report(steering, f'axis {axis_value:.3f}')

    Values are compared rounded to three places, as they are printed, so
    float noise below what the line shows does not log a repeat.
    """

    def __init__(self, name: str) -> None:
        """
        name: what the value is, as the line starts -- 'steering', say
        """
        self.name = name
        self._last: float | None = None
        self._released = False

    def report(self, value: float, detail: str = '') -> None:
        """
        Log value if it differs from the last one logged.
        """
        self._released = False
        rounded = round(value, 3)
        if rounded == self._last:
            return
        self._last = rounded
        suffix = f' ({detail})' if detail else ''
        trace(f'{self.name} {rounded:.3f}{suffix}')

    def release(self, why: str) -> None:
        """
        Log that the part has stopped answering, once until it answers
        again.  The next value is logged whatever it is.
        """
        if self._released:
            return
        self._released = True
        self._last = None
        trace(f'{self.name} released ({why})')
