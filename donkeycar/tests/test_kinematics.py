import math
import time
import unittest

from donkeycar.parts.kinematics import differential_steering


class TestTwoWheelSteeringThrottle(unittest.TestCase):
    def test_differential_steering(self):
        # Straight within steering_zero tolerance
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.0, 0.0))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.05, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.10, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, -0.05, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, -0.10, 0.10))

        # left
        self.assertEqual((0.9, 1.0), differential_steering(1.0, -0.10, 0.0))
        self.assertEqual((0.8, 1.0), differential_steering(1.0, -0.20, 0.0))
        self.assertEqual((0.45, 0.5), differential_steering(0.5, -0.10, 0.0))
        self.assertEqual((0.40, 0.5), differential_steering(0.5, -0.20, 0.0))

        # right
        self.assertEqual((1.0, 0.9), differential_steering(1.0, 0.10, 0.0))
        self.assertEqual((1.0, 0.8), differential_steering(1.0, 0.20, 0.0))
        self.assertEqual((0.5, 0.45), differential_steering(0.5, 0.10, 0.0))
        self.assertEqual((0.5, 0.40), differential_steering(0.5, 0.20, 0.0))
