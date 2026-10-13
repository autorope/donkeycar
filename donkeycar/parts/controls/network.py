#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driving a car from a controller attached to a different machine, with the
control changes carried over the network.

@author: ezward
"""

import json
import logging
from collections import deque
from typing import Any, Protocol

from donkeycar.parts.controls.device import (
    NO_CHANGE,
    AbstractInputController,
    ControlChange,
)

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5556

#: How long a receive waits before giving the caller back control.  This is
#: what lets shutdown be noticed; it does not delay messages, which wake the
#: receive as soon as they arrive.
DEFAULT_RECEIVE_TIMEOUT = 0.05


def encode(change: ControlChange) -> str:
    """
    A control change as a line of JSON.

    The legacy format was four space-separated fields with '0' standing in
    for 'nothing happened', which had two problems.  A control whose name
    contained a space split into too many fields and killed the receiver,
    and a control actually named '0' could never be reported.  JSON has a
    real null and needs no delimiter to be safe.
    """
    return json.dumps(change._asdict())


def decode(message: str) -> ControlChange | None:
    """
    A line of JSON as a control change, or None if it is not one.
    """
    try:
        fields = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        logger.debug(f'Ignoring unreadable control message {message!r}')
        return None

    if not isinstance(fields, dict):
        logger.debug(f'Ignoring control message that is not an object: {message!r}')
        return None

    try:
        return ControlChange(
            button=fields.get('button'),
            button_state=fields.get('button_state'),
            axis=fields.get('axis'),
            axis_value=fields.get('axis_value'),
        )
    except TypeError:
        logger.debug(f'Ignoring malformed control message {message!r}')
        return None


class MessageSubscriber(Protocol):
    """
    The seam between NetworkedController and the network, so the controller
    can be tested without one.
    """

    def open(self) -> None:
        """
        Start listening.  Raises OSError if it cannot.
        """
        ...

    def receive(self) -> str | None:
        """
        One message, or None if none arrived before the timeout.  This must
        return on a timeout rather than blocking indefinitely, so that a
        caller can notice it has been shut down.
        """
        ...

    def close(self) -> None: ...


class MessagePublisher(Protocol):
    def open(self) -> None: ...
    def send(self, message: str) -> None: ...
    def close(self) -> None: ...


class ZmqSubscriber:
    """
    Subscribes to a publisher over ZeroMQ.
    """

    def __init__(
        self,
        address: str,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_RECEIVE_TIMEOUT,
    ) -> None:
        self._address = address
        self._port = port
        self._timeout = timeout
        self._socket: Any = None
        self._context: Any = None

    def open(self) -> None:
        try:
            import zmq
        except ModuleNotFoundError as e:
            raise OSError('pyzmq is not installed.') from e

        self._context = zmq.Context()
        socket = self._context.socket(zmq.SUB)
        socket.connect(f'tcp://{self._address}:{self._port}')
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        # Without this the receive blocks forever, and the legacy version
        # did exactly that: shutdown set a flag and slept, while the thread
        # sat in recv() waiting for a message that would never come.
        socket.setsockopt(zmq.RCVTIMEO, int(self._timeout * 1000))
        self._socket = socket
        logger.info(f'Listening for a controller on {self._address}:{self._port}')

    def receive(self) -> str | None:
        import zmq

        if self._socket is None:
            return None
        try:
            payload: bytes = self._socket.recv()
        except zmq.Again:
            return None
        return payload.decode('utf-8', errors='replace')

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._context is not None:
            self._context.term()
            self._context = None


class ZmqPublisher:
    def __init__(self, port: int = DEFAULT_PORT) -> None:
        self._port = port
        self._socket: Any = None
        self._context: Any = None

    def open(self) -> None:
        try:
            import zmq
        except ModuleNotFoundError as e:
            raise OSError('pyzmq is not installed.') from e

        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(f'tcp://*:{self._port}')
        logger.info(f'Publishing controller changes on port {self._port}')

    def send(self, message: str) -> None:
        if self._socket is not None:
            self._socket.send_string(message)

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._context is not None:
            self._context.term()
            self._context = None


class NetworkedController(AbstractInputController):
    """
    A controller attached to another machine.

    Behaves like any other input controller, so a template binds behaviors
    to it exactly as it would to a pad plugged into the car.  That is a
    change from the legacy arrangement, where the networked joystick was
    pushed into an existing controller after the fact -- `ctr.js = netwkJs`
    -- which only worked because both happened to have a poll() method.

    Messages are queued as they arrive, so a burst delivered between two
    polls is kept.  The legacy version held one button and one axis in
    fields and overwrote them on every message, so anything that arrived
    faster than the vehicle loop read it was lost -- and a network delivers
    bursts by nature.
    """

    def __init__(self, subscriber: MessageSubscriber) -> None:
        self._subscriber = subscriber
        self._pending: deque[ControlChange] = deque()
        self._seen_controls: set[str] = set()
        self._initialized = False

    @property
    def seen_controls(self) -> tuple[str, ...]:
        """
        Controls that have reported at least once.  A remote controller
        cannot be enumerated in advance, so this is all that can be known.
        """
        return tuple(sorted(self._seen_controls))

    def init(self) -> bool:
        if self._initialized:
            return True

        try:
            self._subscriber.open()
        except OSError as e:
            logger.warning(f'{type(self).__name__} not initialized: {e}')
            return False

        self._initialized = True
        return True

    def show_map(self) -> bool:
        if not self._initialized:
            return False

        if self._seen_controls:
            print(f'Controls seen so far: {", ".join(self.seen_controls)}')
        else:
            print(
                'Listening to a remote controller; its controls are not '
                'known until it sends something.'
            )
        return True

    def poll(self) -> ControlChange:
        if not self._initialized:
            return NO_CHANGE

        if not self._pending:
            self._receive()
        if not self._pending:
            return NO_CHANGE
        return self._pending.popleft()

    def shutdown(self) -> None:
        self._initialized = False
        self._pending.clear()
        self._subscriber.close()

    def _receive(self) -> None:
        message = self._subscriber.receive()
        if message is None:
            return  # nothing arrived, which is not a failure

        change = decode(message)
        if change is None:
            return  # a bad message must not take the receiver down with it

        if change.button is None and change.axis is None:
            return

        for name in (change.button, change.axis):
            if name is not None:
                self._seen_controls.add(name)
        self._pending.append(change)


class ControllerPublisher:
    """
    Reads a controller attached to this machine and publishes what it
    reports, for a car running NetworkedController to pick up.

    Run on the machine holding the pad::

        publisher = ControllerPublisher(LogitechJoystick(), ZmqPublisher())
        publisher.run()

    Any AbstractInputController will do.  The legacy publisher hardcoded a
    PS3 pad, so driving from anything else meant editing the class.
    """

    def __init__(
        self,
        controller: AbstractInputController,
        publisher: MessagePublisher,
    ) -> None:
        self._controller = controller
        self._publisher = publisher
        self.running = True

    def init(self) -> bool:
        if not self._controller.init():
            return False
        try:
            self._publisher.open()
        except OSError as e:
            logger.error(f'Could not publish controller changes: {e}')
            return False
        self._controller.show_map()
        return True

    def poll(self) -> None:
        """
        Read one change from the controller and publish it.
        """
        if not self.running:
            return

        try:
            change = self._controller.poll()
        except OSError as e:
            logger.error(f'Controller disconnected: {e}')
            self.running = False
            return

        if change.button is None and change.axis is None:
            return
        self._publisher.send(encode(change))

    def run(self) -> None:
        """
        Publish until shutdown.
        """
        if not self.init():
            return
        try:
            while self.running:
                self.poll()
        except Exception:
            logger.exception('Controller publishing stopped.')
            self.running = False

    def shutdown(self) -> None:
        self.running = False
        self._controller.shutdown()
        self._publisher.close()
