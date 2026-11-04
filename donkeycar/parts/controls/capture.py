#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Measure which driver code each physical control on a pad reports.

    python -m donkeycar.parts.controls.capture --out pad.json

Walks through the controls a gamepad usually has, one at a time.  For each
one the person holding the pad presses Enter and then works only that
control for a few seconds; every code that moved in that window is recorded
with how far it travelled.  The result is the evidence a gamepad map in
gamepads.py is written from, saved as JSON so it can be attached to a pull
request or compared between drivers.

This exists because the same pad reports different codes through different
drivers -- an Xbox pad over USB and over Bluetooth disagree about where the
right stick and the triggers are -- and a map that has not been measured on
the driver it claims to describe passes every test and then steers with the
wrong stick.

A fumbled step can be redone: after each step's result, `r` repeats it.

Unlike `donkey createjs`, which names the controls of an unsupported pad
for one car's myconfig.py, this records raw codes and ranges for whoever is
writing or checking a map.

@author: ezward
"""

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import NamedTuple

from donkeycar.parts.controls.linux import (
    AXIS_SCALE,
    JS_EVENT_AXIS,
    JS_EVENT_INIT,
    JsDevice,
    JsDeviceInfo,
    JsEvent,
)

#: How long the person has to work each control once they press Enter.
DEFAULT_WINDOW = 4.0

#: How long to collect the driver's initial-state events after opening,
#: which is where each axis's resting value comes from.
SETTLE_TIME = 0.5

SKIP = 's'
REDO = 'r'


class Control(NamedTuple):
    """
    One step of a capture: the name a map would give the control, and what
    to tell the person to do with it.
    """

    name: str
    instruction: str


#: The controls a gamepad usually has, in the order they are asked for.  The
#: names are the convention gamepads.py uses, so a capture reads directly
#: against a map.  A pad without one of these skips it.
CONTROLS: tuple[Control, ...] = (
    Control('left_stick_horz', 'LEFT stick: full left, full right, release'),
    Control('left_stick_vert', 'LEFT stick: full up, full down, release'),
    Control('right_stick_horz', 'RIGHT stick: full left, full right, release'),
    Control('right_stick_vert', 'RIGHT stick: full up, full down, release'),
    Control('left_trigger', 'LEFT trigger: squeeze fully, release'),
    Control('right_trigger', 'RIGHT trigger: squeeze fully, release'),
    Control('dpad_horiz', 'D-pad: press LEFT, release, press RIGHT, release'),
    Control('dpad_vert', 'D-pad: press UP, release, press DOWN, release'),
    Control('a_button', 'A (or cross) button: press and release'),
    Control('b_button', 'B (or circle) button: press and release'),
    Control('x_button', 'X (or square) button: press and release'),
    Control('y_button', 'Y (or triangle) button: press and release'),
    Control('left_shoulder', 'LEFT bumper / L1: press and release'),
    Control('right_shoulder', 'RIGHT bumper / R1: press and release'),
    Control('view', 'VIEW / BACK / SELECT / SHARE (left of centre): '
                    'press and release'),
    Control('menu', 'MENU / START / OPTIONS (right of centre): '
                    'press and release'),
    Control('guide', 'XBOX / PS / logo button: press and release QUICKLY '
                     '(a long hold may turn the pad off)'),
    Control('share', 'Any remaining button, such as SHARE below the Xbox '
                     'button (skip if none)'),
    Control('left_stick_press', 'Click the LEFT stick in, release'),
    Control('right_stick_press', 'Click the RIGHT stick in, release'),
)


@dataclass
class Movement:
    """
    What one control code did during one step.
    """

    events: int
    min: float
    max: float

    @property
    def travel(self) -> float:
        return self.max - self.min


@dataclass
class Capture:
    """
    Everything a capture found, in the shape it is saved as.
    """

    device: str
    axis_codes: list[str]
    button_codes: list[str]
    axis_rest: dict[str, float] = field(default_factory=dict)
    #: Per control, either 'skipped' or each code that moved, keyed
    #: 'axis 0x2' / 'button 0x130' and largest travel first.
    controls: dict[str, dict[str, Movement] | str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _code_key(info: JsDeviceInfo, event: JsEvent) -> tuple[str, float] | None:
    """
    The 'axis 0x2' / 'button 0x130' key for an event, and its value scaled
    the way a controller scales it.  None for an index the driver did not
    declare.
    """
    if event.type & JS_EVENT_AXIS:
        codes, kind, value = info.axis_codes, 'axis', event.value / AXIS_SCALE
    else:
        codes, kind, value = info.button_codes, 'button', float(event.value)
    if event.number >= len(codes):
        return None
    return f'{kind} {codes[event.number]:#x}', value


def read_rest(
    device: JsDevice,
    info: JsDeviceInfo,
    clock: Callable[[], float],
    settle_time: float = SETTLE_TIME,
) -> dict[str, float]:
    """
    Each axis's resting value, from the initial-state events the driver
    replays on open.  A trigger rests at one end of its travel rather than
    in the middle, which is worth knowing before binding one.
    """
    rest: dict[str, float] = {}
    end = clock() + settle_time
    while clock() < end:
        event = device.read_event()
        if event is None or not event.type & JS_EVENT_INIT:
            continue
        if event.type & JS_EVENT_AXIS:
            found = _code_key(info, event)
            if found is not None:
                key, value = found
                rest[key.removeprefix('axis ')] = value
    return rest


def capture_step(
    device: JsDevice,
    info: JsDeviceInfo,
    clock: Callable[[], float],
    window: float = DEFAULT_WINDOW,
) -> dict[str, Movement]:
    """
    Every code that moved during one window, largest travel first.

    Working one stick nudges its neighbouring axis -- measured, a full
    sweep of one axis moved the other on the same stick by up to 0.7 -- so
    a step usually reports more than one code.  The one that travelled
    furthest is the control asked for.
    """
    while device.read_event() is not None:
        pass  # anything queued while the person was reading the prompt

    seen: dict[str, Movement] = {}
    end = clock() + window
    while clock() < end:
        event = device.read_event()
        if event is None or event.type & JS_EVENT_INIT:
            continue
        found = _code_key(info, event)
        if found is None:
            continue
        key, value = found
        movement = seen.get(key)
        if movement is None:
            seen[key] = Movement(events=1, min=value, max=value)
        else:
            movement.events += 1
            movement.min = min(movement.min, value)
            movement.max = max(movement.max, value)

    return dict(sorted(seen.items(), key=lambda kv: -kv[1].travel))


def format_step(movements: dict[str, Movement]) -> str:
    if not movements:
        return '    nothing reported'
    return '\n'.join(
        f'    {key:<14} events={m.events:<4} min={m.min:+.3f} max={m.max:+.3f}'
        for key, m in movements.items()
    )


def run_capture(
    device: JsDevice,
    ask: Callable[[str], str],
    say: Callable[[str], None],
    clock: Callable[[], float] = time.monotonic,
    controls: Sequence[Control] = CONTROLS,
    window: float = DEFAULT_WINDOW,
) -> Capture:
    """
    Walk the person through each control and record what moved.

    ask is input() and say is print(), passed in so a test can script the
    person.
    """
    info = device.open()
    say(f'Device : {info.name}')
    say(f'axes   : {", ".join(f"{c:#x}" for c in info.axis_codes)}')
    say(f'buttons: {", ".join(f"{c:#x}" for c in info.button_codes)}')

    result = Capture(
        device=info.name,
        axis_codes=[f'{c:#x}' for c in info.axis_codes],
        button_codes=[f'{c:#x}' for c in info.button_codes],
        axis_rest=read_rest(device, info, clock),
    )

    for control in controls:
        say('')
        while True:
            answer = ask(f'[{control.name}] {control.instruction}\n'
                         f'    Enter to start, {SKIP} to skip: ')
            if answer.strip().lower() == SKIP:
                result.controls[control.name] = 'skipped'
                break

            say('    GO')
            movements = capture_step(device, info, clock, window)
            say(format_step(movements))

            answer = ask(f'    Enter to keep, {REDO} to redo this step: ')
            if answer.strip().lower() != REDO:
                result.controls[control.name] = movements
                break
            say('')

    return result


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    from donkeycar.parts.controls.linux import LinuxJsDevice

    parser = argparse.ArgumentParser(
        prog='donkeycar.parts.controls.capture',
        description='Measure which driver code each control on a pad reports.')
    parser.add_argument('--dev', default='/dev/input/js0',
                        help='device file (default: /dev/input/js0)')
    parser.add_argument('--out', default='pad_capture.json',
                        help='where to save the result (default: pad_capture.json)')
    parser.add_argument('--window', type=float, default=DEFAULT_WINDOW,
                        help='seconds to work each control '
                             f'(default: {DEFAULT_WINDOW:g})')
    args = parser.parse_args(argv)

    device = LinuxJsDevice(args.dev)
    try:
        result = run_capture(device, ask=input, say=print, window=args.window)
    except FileNotFoundError:
        # a Bluetooth pad that has gone to sleep takes its device node with it
        raise SystemExit(f'No {args.dev}.  Is the pad connected and awake?')
    finally:
        device.close()

    with open(args.out, 'w') as f:
        f.write(result.to_json())
    print(f'\nSaved to {args.out}')


if __name__ == '__main__':
    main()
