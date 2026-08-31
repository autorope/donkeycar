#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test doubles and assertions for the Linux game controllers.

This module is deliberately not named test_*.py; it holds the fixture the
per-gamepad tests share, not tests of its own.
"""

import ast
import inspect
import textwrap
from collections.abc import Iterable, Mapping
from typing import Any

from donkeycar.parts.controls.linux import (
    JS_EVENT_AXIS,
    JS_EVENT_BUTTON,
    JS_EVENT_INIT,
    JsDevice,
    JsDeviceInfo,
    JsEvent,
)


class FakeJsDevice:
    """
    A JsDevice that reports the controls it was given and replays a
    scripted list of events, so a controller and its name maps can be
    tested with no joystick attached.
    """

    def __init__(
        self,
        name: str = 'Fake Gamepad',
        axis_codes: Iterable[int] = (),
        button_codes: Iterable[int] = (),
        events: Iterable[JsEvent] = (),
        open_error: OSError | None = None,
    ) -> None:
        self.name = name
        self.axis_codes = tuple(axis_codes)
        self.button_codes = tuple(button_codes)
        self.events = list(events)
        self.open_error = open_error
        self.open_count = 0
        self.closed = False

    def open(self) -> JsDeviceInfo:
        self.open_count += 1
        if self.open_error is not None:
            raise self.open_error
        return JsDeviceInfo(self.name, self.axis_codes, self.button_codes)

    def read_event(self) -> JsEvent | None:
        if self.events:
            return self.events.pop(0)
        return None

    def close(self) -> None:
        self.closed = True


#: Fail the type check here, rather than in twelve gamepad test modules,
#: if the fake ever stops matching the real device contract.
_protocol_check: JsDevice = FakeJsDevice()


def button_event(number: int, value: int, time: int = 0) -> JsEvent:
    """
    A button press (value 1) or release (value 0) of the button the driver
    reports at the given index.
    """
    return JsEvent(time=time, value=value, type=JS_EVENT_BUTTON, number=number)


def axis_event(number: int, value: int, time: int = 0) -> JsEvent:
    """
    A movement of the axis the driver reports at the given index.  value is
    the raw driver reading, -32767 to 32767.
    """
    return JsEvent(time=time, value=value, type=JS_EVENT_AXIS, number=number)


def init_event(number: int, value: int = 0, time: int = 0) -> JsEvent:
    """
    One of the synthetic events the driver replays when the device is
    opened to announce each control's current state.
    """
    return JsEvent(
        time=time,
        value=value,
        type=JS_EVENT_BUTTON | JS_EVENT_INIT,
        number=number,
    )


def duplicate_values(names: Mapping[int, str]) -> list[str]:
    """
    Names used for more than one control, which would make two controls
    indistinguishable downstream.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names.values():
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates)


def duplicate_literal_keys(obj: Any) -> list[str]:
    """
    Keys written more than once in a dict literal in this class's source.

    A duplicate key cannot be found by inspecting the resulting dict --
    Python keeps only the last one and the earlier control silently
    disappears.  This reads the source instead.  PS4Joystick had exactly
    this defect: 0x13a was written as both 'L3' and 'share', so 'L3' was
    unreachable.
    """
    try:
        source = inspect.getsource(obj)
    except (OSError, TypeError):  # pragma: no cover - source always present
        return []

    # a nested class comes back indented, which will not parse on its own
    tree = ast.parse(textwrap.dedent(source))
    duplicates: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        seen: set[object] = set()
        for key in node.keys:
            if not isinstance(key, ast.Constant):
                continue
            if key.value in seen:
                duplicates.append(repr(key.value))
            seen.add(key.value)
    return duplicates
