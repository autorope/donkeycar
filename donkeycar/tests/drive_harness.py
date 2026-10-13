#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runs a template's real drive() with a scripted controller and a recording
drivetrain, so a test can see what reaches the wheels.

Not named test_*.py: this is the fixture, not tests of its own.

Checking memory at the end of a pass is not enough.  A value can be right
there and still never reach the drivetrain, because the part that wrote it
ran after the drivetrain did -- and the next pass begins with the web
controller writing over it.  That is how a physical controller came to
drive nothing on this branch while every test passed.
"""

import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from typing import Any
from unittest import mock

import donkeycar as dk
from donkeycar.parts.controls.events import InputControllerEvents
from donkeycar.parts.controls.web import WebButtonController
from donkeycar.tests.setup import custom_template

#: What a step does before its pass: feed the controller, press a button.
Step = Callable[[], None]


class RecordingDrivetrain:
    """
    Stands in for the drivetrain, keeping what it was asked to do.
    """

    def __init__(self) -> None:
        self.received: list[tuple[float, float]] = []

    def run(self, steering: float, throttle: float) -> None:
        self.received.append((steering, throttle))


def load_template_config(
    car_dir: str, template: str = 'complete', **myconfig: Any
) -> Any:
    """
    A shipped template's configuration in a new car directory, with a mock
    camera and the given overrides, as a user's myconfig.py would set them.

    Use a fresh directory per car: a tub left behind by one template
    refuses to open for another that records different fields.
    """
    path = custom_template(car_dir, template=template)
    settings = {'CAMERA_TYPE': 'MOCK', 'DRIVE_TRAIN_TYPE': 'MOCK',
                'USE_SSD1306_128_32': False, 'USE_JOYSTICK_AS_DEFAULT': True}
    settings.update(myconfig)
    with open(os.path.join(path, 'myconfig.py'), 'w') as f:
        for key, value in settings.items():
            f.write(f'{key} = {value!r}\n')
    return dk.load_config(os.path.join(path, 'config.py'))


@contextmanager
def driving(
    template: Any,
    cfg: Any,
    steps: Sequence[Step],
    patches: Sequence[Any] = (),
    on_start: Callable[[list[Any]], None] | None = None,
) -> Iterator[tuple[RecordingDrivetrain, list[Any]]]:
    """
    Run template.drive(cfg) for one pass per step, then hand back the
    drivetrain and the vehicle's parts in the order they run.

    Each step runs before its pass, and the controller's event pump is
    stepped by hand in place of its thread, so the test is deterministic.
    patches are further context managers, for swapping in a fake device.
    on_start is given the parts once the vehicle is built, before the first
    pass, for a test that needs to reach one of them.
    """
    drivetrain = RecordingDrivetrain()
    parts: list[Any] = []

    def add_drivetrain(V: Any, cfg: Any) -> None:
        V.add(drivetrain, inputs=['steering', 'throttle'])

    def start(self: Any, rate_hz: float = 10, max_loop_count: Any = None,
              verbose: bool = False) -> None:
        parts.extend(entry['part'] for entry in self.parts)
        # the physical controller's pump only: the web buttons' poll blocks
        # on its queue for a timeout, which costs real time on every call
        pumps = [p for p in parts if isinstance(p, InputControllerEvents)
                 and not isinstance(p._controller, WebButtonController)]
        for pump in pumps:
            assert pump._controller.init()
        if on_start is not None:
            on_start(parts)
        for step in steps:
            step()
            for pump in pumps:
                for _ in range(4):  # one poll per channel, and one to spare
                    pump.poll()
            self.update_parts()

    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(template, 'add_drivetrain',
                                              add_drivetrain))
        stack.enter_context(mock.patch.object(dk.vehicle.Vehicle, 'start',
                                              start))
        for patch in patches:
            stack.enter_context(patch)
        template.drive(cfg=cfg)
        yield drivetrain, parts


def part_index(parts: Sequence[Any], part_type: type) -> int:
    """
    Where the first part of a type runs in the loop.
    """
    for index, part in enumerate(parts):
        if isinstance(part, part_type):
            return index
    raise AssertionError(f'no {part_type.__name__} in the vehicle')
