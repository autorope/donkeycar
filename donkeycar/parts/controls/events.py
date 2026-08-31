#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turns input device state changes into one-shot events in vehicle memory.

@author: ezward
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any, NamedTuple

from donkeycar.events import OneShotEvents
from donkeycar.memory import Memory
from donkeycar.parts.controls.device import AbstractInputController

logger = logging.getLogger(__name__)

BUTTON_DOWN = 'press'    # button changed to the down state
BUTTON_UP = 'release'    # button changed to the up state
BUTTON_CLICK = 'click'   # button completed one or more down-up cycles
BUTTON_HOLD = 'hold'     # button has been held down past the long-press time

BUTTON_EVENT = '/event/button/'
AXIS_EVENT = '/event/axis/'
BUTTON_STATE = '/button/'
AXIS_STATE = '/axis/'


def format_button_event(button: str, event: str) -> str:
    """
    Memory key for a button event, e.g. '/event/button/Y/press'.
    """
    return f'{BUTTON_EVENT}{button}/{event}'


def format_button_click_event(button: str, click_count: int) -> str:
    """
    Memory key for a click, e.g. '/event/button/Y/click/2' for a
    double-click.  The count makes each length of click distinct, so a part
    can listen for a double-click and ignore single clicks.
    """
    return format_button_event(button, f'{BUTTON_CLICK}/{click_count}')


def format_axis_event(axis: str) -> str:
    """
    Memory key for an axis event, e.g. '/event/axis/left_stick_horz'.
    """
    return f'{AXIS_EVENT}{axis}'


def format_button_key(button: str) -> str:
    """
    Memory key for a button's persistent state, e.g. '/button/X', holding 1
    while the button is down and 0 while it is up.
    """
    return f'{BUTTON_STATE}{button}'


def format_axis_key(axis: str) -> str:
    """
    Memory key for an axis' persistent state, e.g. '/axis/right_stick_vert',
    holding the axis position as a float from -1.0 to 1.0.
    """
    return f'{AXIS_STATE}{axis}'


class _PendingClick(NamedTuple):
    # not `count`: a NamedTuple field of that name shadows tuple.count
    clicks: int
    released_at: float


class InputControllerEvents:
    """
    A threaded part that polls an AbstractInputController and publishes what
    it reads into the vehicle memory, as both one-shot events and persistent
    state.

    Events last for exactly one pass through the vehicle loop, so they suit
    a part's run_condition -- the part runs once, when the event happens::

        V.add(InputControllerEvents(V.mem, LogitechJoystick()), threaded=True)
        V.add(TogglePilotMode(),
              inputs=['user/mode'], outputs=['user/mode'],
              run_condition=format_button_event('Y', BUTTON_DOWN))

    Add this part at the top of the vehicle loop.  Parts added after it see
    an event on the same pass it was emitted; parts added before it see the
    event on the next pass instead.

    Events published, for a button named 'Y':

        /event/button/Y/press      the button went down
        /event/button/Y/release    the button came up
        /event/button/Y/click/1    one click completed, 2 for a double, ...
        /event/button/Y/hold       held down past long_press_time

    and for an axis named 'left_stick_horz':

        /event/axis/left_stick_horz    the axis moved

    The value of a button event is the time it happened, on the injected
    clock -- monotonic seconds by default, so the values order correctly but
    are not wall-clock times.  The value of an axis event is the new axis
    position.

    Persistent state is published alongside, as '/button/Y' (1 down, 0 up)
    and '/axis/left_stick_horz' (-1.0 to 1.0).  Unlike the events these
    persist, so a part can read a control's current state without having to
    track the events itself, or use one control as a modifier for another --
    quit only when 'B' is double-clicked while 'X' is held, say.

    Clicks are deferred: a click is published once the burst of clicks has
    ended, so a double-click publishes only '/click/2'.  Publishing
    '/click/1' the moment the first button came up would fire every
    single-click behavior partway through every double-click.  The cost is
    fast_click_time of latency on clicks; press and release stay immediate.
    Pass defer_clicks=False for the older behavior.

    A press held past long_press_time publishes a hold, and that press will
    not go on to publish a click -- a long press is a gesture of its own,
    not a slow click.
    """

    def __init__(
        self,
        memory: Memory,
        controller: AbstractInputController,
        fast_click_time: float = 0.2,
        long_press_time: float = 0.5,
        defer_clicks: bool = True,
        init_retry_time: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        memory:          vehicle memory to publish into
        controller:      the input device to poll
        fast_click_time: longest gap between clicks counted as sequential
        long_press_time: how long a press must be held to publish a hold
        defer_clicks:    hold a click back until the burst of clicks ends
        init_retry_time: seconds between attempts to reach the device
        clock:           source of the current time, for testing
        sleep:           how to wait between init attempts, for testing
        """
        self._memory = memory
        self._controller = controller
        self._fast_click_time = fast_click_time
        self._long_press_time = long_press_time
        self._defer_clicks = defer_clicks
        self._init_retry_time = init_retry_time
        self._clock = clock
        self._sleep = sleep

        self._one_shot = OneShotEvents(memory)
        self._lock = threading.Lock()

        self._button_states: dict[str, int] = {}
        self._axis_states: dict[str, float] = {}
        self._last_release: dict[str, float] = {}
        self._burst_counts: dict[str, int] = {}
        self._pending_clicks: dict[str, _PendingClick] = {}
        self._pending_holds: dict[str, float] = {}
        self._held: set[str] = set()

        self._events: dict[str, Any] = {}
        self._state_changes: dict[str, Any] = {}

        # NOTE: the device is not opened here.  Doing that in the
        # constructor would block assembling the vehicle while an unpaired
        # gamepad was waited for, and fail the whole car if it never came.
        self.running = True

    def update(self) -> None:
        """
        Poll the controller until shutdown.  Runs on a background thread.
        """
        try:
            while self.running and not self._controller.init():
                logger.info('Waiting for the input controller...')
                self._sleep(self._init_retry_time)
            if not self.running:
                return

            self._controller.show_map()
            while self.running:
                self.poll()
        except Exception:
            # a bare `except:` here would also swallow KeyboardInterrupt and
            # stop the car with nothing in the log to say why
            logger.exception('Input controller polling stopped.')
            self.running = False

    def poll(self) -> None:
        """
        Read one state change from the controller and buffer it.
        """
        if not self.running:
            return

        try:
            change = self._controller.poll()
        except OSError as e:
            logger.error(f'Input controller disconnected: {e}')
            self.running = False
            return

        if change.button is None and change.axis is None:
            return

        with self._lock:
            now = self._clock()
            self._expire_pending(now)
            if change.axis is not None and change.axis_value is not None:
                self._on_axis(change.axis, change.axis_value)
            if change.button is not None and change.button_state is not None:
                self._on_button(change.button, change.button_state, now)

    def run_threaded(self) -> None:
        """
        Publish the buffered events and state into memory, and expire the
        events published on the previous pass.
        """
        now = self._clock()
        with self._lock:
            # clicks and holds are published by the passage of time rather
            # than by a device event, so they are resolved here too
            self._expire_pending(now)
            state_changes = self._state_changes
            self._state_changes = {}
            events = self._events
            self._events = {}

        if state_changes:
            self._memory.update(state_changes)
        self._one_shot.emit(events)

    def shutdown(self) -> None:
        self.running = False
        self._controller.shutdown()
        self._one_shot.clear()

    def _on_axis(self, axis: str, value: float) -> None:
        if self._axis_states.get(axis) == value:
            return
        self._axis_states[axis] = value
        self._events[format_axis_event(axis)] = value
        self._state_changes[format_axis_key(axis)] = value

    def _on_button(self, button: str, state: int, now: float) -> None:
        if self._button_states.get(button) == state:
            return
        self._button_states[button] = state
        self._state_changes[format_button_key(button)] = state

        if state:
            self._on_press(button, now)
        else:
            self._on_release(button, now)

    def _on_press(self, button: str, now: float) -> None:
        self._events[format_button_event(button, BUTTON_DOWN)] = now

        # a press this soon after the last release continues that burst of
        # clicks; anything slower starts a new one
        since_release = now - self._last_release.get(button, -_FOREVER)
        if since_release > self._fast_click_time:
            self._burst_counts[button] = 0

        # the burst is still growing, so the click it will eventually
        # publish is not the one that is pending
        self._pending_clicks.pop(button, None)

        self._pending_holds[button] = now
        self._held.discard(button)

    def _on_release(self, button: str, now: float) -> None:
        self._events[format_button_event(button, BUTTON_UP)] = now
        self._last_release[button] = now
        self._pending_holds.pop(button, None)

        if button in self._held:
            # this press already published a hold; it is not also a click
            self._held.discard(button)
            self._burst_counts[button] = 0
            return

        count = self._burst_counts.get(button, 0) + 1
        self._burst_counts[button] = count
        if self._defer_clicks:
            self._pending_clicks[button] = _PendingClick(count, now)
        else:
            self._events[format_button_click_event(button, count)] = now

    def _expire_pending(self, now: float) -> None:
        """
        Publish the clicks and holds that have come due.
        """
        for button, pending in list(self._pending_clicks.items()):
            if now - pending.released_at >= self._fast_click_time:
                key = format_button_click_event(button, pending.clicks)
                self._events[key] = pending.released_at
                del self._pending_clicks[button]

        for button, pressed_at in list(self._pending_holds.items()):
            due = pressed_at + self._long_press_time
            if now >= due:
                # the due time, not `now`, so the value does not depend on
                # when the vehicle loop happened to get here
                self._events[format_button_event(button, BUTTON_HOLD)] = due
                del self._pending_holds[button]
                self._held.add(button)


_FOREVER = float('inf')
