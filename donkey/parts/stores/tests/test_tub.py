# -*- coding: utf-8 -*-
import tempfile
import unittest
from ..tub import Tub


class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        path = tempfile.TemporaryDirectory()
        inputs = ['name', 'age', 'pic']
        types = ['str', 'float', 'image_array']
        self.tub = Tub(path, inputs=inputs, types=types)
        
    def test_tub_create(self):
        self.tub.run(['will', 323, 'asdfasdf'])