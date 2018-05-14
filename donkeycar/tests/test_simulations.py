# -*- coding: utf-8 -*-
import unittest
import numpy as np
from donkeycar.parts.simulation import MovingSquareTelemetry, SquareBoxCamera


class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        self.tel = MovingSquareTelemetry()

    def test_run_types(self):
        x, y = self.tel.run()
        assert type(x) == int
        assert type(y) == int


class TestSquareBoxCamera(unittest.TestCase):
    def setUp(self):
        self.cam = SquareBoxCamera()

    def test_run_types(self):
        arr = self.cam.run(50, 50)
        assert type(arr) == np.ndarray
