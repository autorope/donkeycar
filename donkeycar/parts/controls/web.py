#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The web interface's buttons, as an input controller.

@author: ezward
"""

import logging
import queue
import threading
from collections.abc import Mapping

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

#: Web button names are prefixed so they cannot collide with a gamepad's.
DEFAULT_PREFIX = 'web_'

#: How long poll() waits for a push before giving the caller back control.
DEFAULT_POLL_TIMEOUT = 0.05


class WebButtonController(AbstractInputController):
    """
    Presents the web interface's buttons as an ordinary input controller, so
    that a web button and a gamepad button produce the same events and a
    behavior can be bound to either without the template caring which.

    Before this, the two were handled quite differently.  The web
    controller latched a push into a dictionary, a part exploded that into
    memory as 'web/w1', and a template bound to it directly -- while a
    gamepad button went through set_button_down_trigger on the controller
    object.  So every binding in path_follow.py and cv_control.py was
    written twice, once for each route in, and the two had different ideas
    of what a press meant.  Now a web push is
    '/event/button/web_w1/press' and gets press, release, click and
    multi-click from the same event pump as everything else.

    This bridges two loops, so it has a foot in each.  run() is called from
    the vehicle loop with the button dictionary the web controller emits,
    and poll() is called from InputControllerEvents' thread.  Wire it as::

        web_buttons = WebButtonController()
        V.add(web_buttons, inputs=['web/buttons'])
        V.add(InputControllerEvents(V.mem, web_buttons), threaded=True)

    The web interface reports a push as a latched true that it clears on the
    following pass, so a push arrives here as a press and then a release.
    Nothing in the web interface reports how long a button was held, so a
    hold event will not come from this controller however long the user
    keeps the mouse down.
    """

    def __init__(
        self,
        prefix: str = DEFAULT_PREFIX,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> None:
        self._prefix = prefix
        self._poll_timeout = poll_timeout
        self._queue: queue.Queue[ControlChange] = queue.Queue()
        self._states: dict[str, int] = {}
        self._lock = threading.Lock()
        self._running = True

    @property
    def button_map(self) -> tuple[str, ...]:
        """
        Buttons that have been pushed at least once.  The web interface
        does not announce which buttons it has, so this is all that can be
        known.
        """
        with self._lock:
            return tuple(sorted(self._states))

    def init(self) -> bool:
        return True

    def show_map(self) -> bool:
        pushed = self.button_map
        if pushed:
            print(f'Web buttons pushed so far: {", ".join(pushed)}')
        else:
            print('Web buttons are known once they are pushed.')
        return True

    def poll(self) -> ControlChange:
        """
        Called from the event pump's thread.  Waits briefly rather than
        spinning, and returns so that shutdown can be noticed.
        """
        if not self._running:
            return NO_CHANGE
        try:
            return self._queue.get(timeout=self._poll_timeout)
        except queue.Empty:
            return NO_CHANGE

    def run(self, buttons: Mapping[str, bool] | None = None) -> None:
        """
        Called from the vehicle loop with the web interface's latched
        buttons.
        """
        if not self._running:
            return

        reported = {
            self._name(button): 1 if is_pushed else 0
            for button, is_pushed in (buttons or {}).items()
        }
        with self._lock:
            # A button that has dropped out of the dictionary is no longer
            # pushed, so it is released rather than left held down for ever.
            for name in set(self._states) | set(reported):
                self._change(name, reported.get(name, 0))

    def shutdown(self) -> None:
        self._running = False

    def _name(self, button: str) -> str:
        return f'{self._prefix}{button}'

    def _change(self, name: str, state: int) -> None:
        if self._states.get(name, 0) == state:
            return
        self._states[name] = state
        self._queue.put(ControlChange(button=name, button_state=state))
