#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
basic.py's gamepad toggles, through its real drive().

Item 3 of a review posted on PR #1249: basic.py's joystick branch added a
web controller after the mode and recording toggles and gave it only the
camera image, so it wrote its own mode and recording over theirs in the
same pass.  Pressing the buttons did nothing.
"""

import logging
import os
import tempfile
import unittest
from unittest import mock

import pytest

import donkeycar as dk
from donkeycar.parts.controls.device import ControlChange
from donkeycar.parts.controls.events import InputControllerEvents
from donkeycar.parts.controls.web import WebButtonController
from donkeycar.tests.fake_js import FakeInputController
from donkeycar.tests.setup import custom_template

# basic.py imports the training augmentations at module level
pytest.importorskip('albumentations')
from donkeycar.templates import basic  # noqa: E402


class TestTheGamepadToggles(unittest.TestCase):
    """
    On the xbox map, A toggles the pilot mode and B toggles recording.
    """

    def setUp(self) -> None:
        logging.disable(logging.WARNING)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.pad = FakeInputController()

    def press(self, button: str):
        return lambda: self.pad.changes.extend([
            ControlChange(button, 1, None, None),
            ControlChange(button, 0, None, None)])

    def drive(self, *steps) -> list[tuple[str, bool]]:
        """
        The mode and recording state after each pass, one pass per step.
        """
        seen: list[tuple[str, bool]] = []

        def start(vehicle, rate_hz=10, max_loop_count=None, verbose=False):
            pumps = [e['part'] for e in vehicle.parts
                     if isinstance(e['part'], InputControllerEvents)
                     and not isinstance(e['part']._controller,
                                        WebButtonController)]
            for pump in pumps:
                assert pump._controller.init()
            for step in steps:
                step()
                for pump in pumps:
                    for _ in range(4):
                        pump.poll()
                vehicle.update_parts()
                seen.append((vehicle.mem['user/mode'],
                             vehicle.mem['recording']))

        with tempfile.TemporaryDirectory() as car_dir:
            custom_template(car_dir, template='basic')
            with open(os.path.join(car_dir, 'myconfig.py'), 'w') as f:
                f.write("CAMERA_TYPE = 'MOCK'\n"
                        "DRIVE_TRAIN_TYPE = 'MOCK'\n"
                        "USE_JOYSTICK_AS_DEFAULT = True\n"
                        "CONTROLLER_TYPE = 'xbox'\n"
                        "AUTO_RECORD_ON_THROTTLE = False\n")
            cfg = dk.load_config(os.path.join(car_dir, 'config.py'))
            with mock.patch.object(basic, 'get_input_controller',
                                   return_value=self.pad), \
                 mock.patch.object(dk.vehicle.Vehicle, 'start', start):
                basic.drive(cfg)
        return seen

    @staticmethod
    def idle() -> None:
        pass

    def test_the_mode_toggle_sticks(self):
        seen = self.drive(self.idle, self.press('a_button'), self.idle,
                          self.press('a_button'), self.idle)

        assert [mode for mode, _ in seen] == [
            'user', 'local_angle', 'local_angle', 'local', 'local']

    def test_the_recording_toggle_sticks(self):
        seen = self.drive(self.idle, self.press('b_button'), self.idle,
                          self.press('b_button'), self.idle)

        assert [recording for _, recording in seen] == [
            False, True, True, False, False]


if __name__ == '__main__':
    unittest.main()
