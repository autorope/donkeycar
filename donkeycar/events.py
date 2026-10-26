#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-shot event bookkeeping for Donkeycar parts.

@author: ezward
"""

from collections.abc import Mapping
from typing import Any

from donkeycar.memory import Memory


class OneShotEvents:
    """
    Publishes named events into a Memory and removes them again on the
    next call to emit(), so each event is visible for exactly one full
    pass through the vehicle loop.

    Contrast this with 'normal' memory state, which persists for the life
    of the vehicle loop.  A one-shot event triggers a part once, when it is
    emitted, rather than over and over on every subsequent pass.  That makes
    an event key usable as a part's run_condition:

        V.add(TogglePilotMode(),
              inputs=['user/mode'],
              outputs=['user/mode'],
              run_condition='/event/button/Y/press')

    Expiry is owned by the emitting part -- an event is removed when that
    part next emits -- rather than by the Vehicle at end-of-loop.  This is
    deliberate.  End-of-loop expiry would mean parts added *before* the
    emitter never observe the event at all; owning expiry here means they
    observe it one loop later instead.  The car's part topology is not a
    DAG, so parts do legitimately sit upstream of the part they react to.

    A part typically owns one OneShotEvents per stream of events it emits::

        self._events = OneShotEvents(memory)
        ...
        self._events.emit({'/event/button/Y/press': now})

    Note that an event key is removed on the next emit() even if some other
    part has since written a persistent value under that same key.  Keep
    event keys in their own namespace (Donkeycar uses a leading '/event/')
    so that cannot happen.
    """

    def __init__(self, memory: Memory) -> None:
        self._memory = memory
        self._emitted: tuple[str, ...] = ()

    @property
    def emitted(self) -> tuple[str, ...]:
        """
        The event keys currently live in memory, in emission order.
        """
        return self._emitted

    def emit(self, events: Mapping[str, Any]) -> None:
        """
        Expire the previously emitted events, then publish these ones.

        Call this once per pass through the vehicle loop, including when
        there is nothing to emit -- emit({}) is what expires the previous
        pass's events.
        """
        self._memory.remove(self._emitted)
        self._memory.update(dict(events))
        self._emitted = tuple(events)

    def clear(self) -> None:
        """
        Expire the previously emitted events without publishing new ones.

        Use this on shutdown so events do not outlive the part that emitted
        them.  Calling it more than once is harmless.
        """
        self._memory.remove(self._emitted)
        self._emitted = ()
