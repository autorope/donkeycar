#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
`donkey createjs` -- name the controls on a controller Donkeycar has no
built-in map for.

The wizard used to generate a Python file holding a controller class and a
map from its buttons to behaviors.  It no longer needs to: naming a control
is a dictionary in myconfig.py, and what each control *does* is
CONTROLLER_BEHAVIOR_MAP.  So this asks only what each control is called and
prints the two dictionaries to paste in.

@author: ezward
"""

import argparse
import sys
import time
from typing import Any

from donkeycar.parts.controls.device import NO_CHANGE
from donkeycar.parts.controls.linux import LinuxGameController, LinuxJsDevice

#: How long to wait for a control to move before giving up on it.
CONTROL_TIMEOUT = 20.0

#: A control must move at least this far to count as deliberate, so that a
#: resting stick's jitter is not mistaken for the user answering.
AXIS_THRESHOLD = 0.5


class CreateJoystick:
    """
    Walks a user through naming the controls on their controller.
    """

    def __init__(self) -> None:
        self.controller: LinuxGameController | None = None
        self.button_names: dict[int, str] = {}
        self.axis_names: dict[int, str] = {}

    # -- the command interface ------------------------------------------

    def parse_args(self, args: list[str]) -> Any:
        parser = argparse.ArgumentParser(prog='createjs', usage='%(prog)s [options]')
        parser.add_argument(
            '--dev', default='/dev/input/js0',
            help='device file for the controller')
        parser.add_argument(
            '--config', default=None,
            help='write the names to this file as well as printing them')
        return parser.parse_args(args)

    def run(self, args: list[str], parser: Any = None) -> None:
        parsed = self.parse_args(args)
        if not self.connect(parsed.dev):
            return

        print()
        print('Press each control you want to name, one at a time.')
        print('Press Enter without pressing anything to move on.')
        print()

        self.name_controls()
        self.report(parsed.config)

    # -- the wizard -----------------------------------------------------

    def connect(self, dev_fn: str) -> bool:
        controller = LinuxGameController(device=LinuxJsDevice(dev_fn))
        if not controller.init():
            print(f'Could not open {dev_fn}.')
            print('Is the controller connected and paired?')
            return False

        self.controller = controller
        print(f'Found: {controller.name}')
        print(f'  {len(controller.axis_map)} axes, '
              f'{len(controller.button_map)} buttons')
        return True

    def name_controls(self) -> None:
        """
        Ask for a name, wait for a control, repeat.
        """
        while True:
            try:
                name = input('Name for the next control (Enter to finish): ')
            except (EOFError, KeyboardInterrupt):
                print()
                return

            name = name.strip()
            if not name:
                return

            print(f'  Now press or move the control you want to call '
                  f'{name!r}...')
            control = self.wait_for_control()
            if control is None:
                print('  Nothing happened; skipping.')
                continue

            kind, code, was_called = control
            if kind == 'button':
                self.button_names[code] = name
            else:
                self.axis_names[code] = name
            print(f'  {was_called} (0x{code:02x}) is now {name!r}')

    def wait_for_control(self) -> tuple[str, int, str] | None:
        """
        The next control the user moves, as its kind, its driver code and
        the name it currently reports under.

        An axis has to move a good way to count.  A resting stick trickles
        small changes continuously -- measured up to 0.1 on a real pad --
        and taking the first of those would name whichever stick happened
        to be twitching rather than the control the user pressed.
        """
        assert self.controller is not None

        deadline = time.monotonic() + CONTROL_TIMEOUT
        while time.monotonic() < deadline:
            change = self.controller.poll()
            if change == NO_CHANGE:
                continue

            if change.button is not None and change.button_state:
                code = self.code_for(change.button, self.controller.button_map)
                if code is not None:
                    self.drain()
                    return 'button', code, change.button

            if change.axis is not None and change.axis_value is not None:
                if abs(change.axis_value) < AXIS_THRESHOLD:
                    continue
                code = self.code_for(change.axis, self.controller.axis_map)
                if code is not None:
                    self.drain()
                    return 'axis', code, change.axis

        return None

    def drain(self) -> None:
        """
        Swallow whatever else the control sent, so that releasing a button
        or letting a stick spring back is not read as the next answer.
        """
        assert self.controller is not None
        settle = time.monotonic() + 0.5
        while time.monotonic() < settle:
            self.controller.poll()

    @staticmethod
    def code_for(name: str, control_map: tuple[str, ...]) -> int | None:
        """
        The driver's code for a control, read back out of its default name.

        A control with no built-in name reports as 'button(0x133)' or
        'axis(0x03)', which is where the code comes from.  A control that
        already has a real name is one this controller knows about, and
        does not need naming again.
        """
        if '(0x' not in name:
            print(f'  {name!r} already has a name; nothing to do.')
            return None
        try:
            return int(name.split('(0x')[1].rstrip(')'), 16)
        except (IndexError, ValueError):
            return None

    # -- the result -----------------------------------------------------

    def report(self, path: str | None = None) -> None:
        if not self.button_names and not self.axis_names:
            print('\nNothing was named.')
            return

        lines = [
            '',
            '# Paste this into myconfig.py.  Set CONTROLLER_TYPE to',
            "# 'custom' if this controller has no built-in map; if it has",
            '# one, these names are layered over it and only the controls',
            '# listed here change.',
            '',
            self.format_dict('JOYSTICK_BUTTON_NAMES', self.button_names),
            '',
            self.format_dict('JOYSTICK_AXIS_NAMES', self.axis_names),
            '',
            '# What each control does is CONTROLLER_BEHAVIOR_MAP, which',
            '# takes the names above.  See cfg_complete.py.',
        ]
        text = '\n'.join(lines)
        print(text)

        if path:
            with open(path, 'wt') as out:
                out.write(text + '\n')
            print(f'\nAlso written to {path}')

    @staticmethod
    def format_dict(name: str, names: dict[int, str]) -> str:
        if not names:
            return f'{name} = None'

        lines = [f'{name} = {{']
        for code in sorted(names):
            lines.append(f"    0x{code:02x}: '{names[code]}',")
        lines.append('}')
        return '\n'.join(lines)


if __name__ == '__main__':
    CreateJoystick().run(sys.argv[1:])
