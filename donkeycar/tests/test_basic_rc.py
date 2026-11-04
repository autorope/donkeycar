#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
basic.py's RC receiver path, through a real drive loop.
"""

import types
import unittest

import pytest

import donkeycar as dk
from donkeycar.parts.controls.events import format_axis_event

# basic.py imports the training augmentations at module level
pytest.importorskip('albumentations')
from donkeycar.templates.basic import add_rc_behaviors  # noqa: E402


def car_with(**settings) -> dk.vehicle.Vehicle:
    cfg = types.SimpleNamespace(JOYSTICK_STEERING_SCALE=0.8,
                                JOYSTICK_MAX_THROTTLE=0.5,
                                JOYSTICK_THROTTLE_DIR=-1.0,
                                JOYSTICK_DEADZONE=0.01, **settings)
    car = dk.vehicle.Vehicle()
    add_rc_behaviors(car, cfg)
    return car


def one_pass(car, steering, throttle) -> tuple[float, float]:
    car.mem[format_axis_event('steering')] = steering
    car.mem[format_axis_event('throttle')] = throttle
    car.update_parts()
    return car.mem['user/angle'], car.mem['user/throttle']


class TestRCReceiverIsPassedThrough(unittest.TestCase):
    """
    The receiver already reads positive for forward and is limited by the
    transmitter, so the gamepad settings must not flip or scale it.
    """

    def test_forward_is_forward_at_full_value(self):
        assert one_pass(car_with(), 0.5, 0.5) == (0.5, 0.5)

    def test_reverse_is_reverse(self):
        assert one_pass(car_with(), -0.5, -0.5) == (-0.5, -0.5)


if __name__ == '__main__':
    unittest.main()
