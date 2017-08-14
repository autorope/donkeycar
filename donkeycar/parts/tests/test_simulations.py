# -*- coding: utf-8 -*-
import unittest
from ..simulations import MovingSquareTelemetry


class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        self.tel = MovingSquareTelemetry()
        
    def test_run_types(self):
        x, y = self.tel.run()
        assert type(x) == int
        assert type(y) == int