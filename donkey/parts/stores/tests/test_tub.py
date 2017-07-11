# -*- coding: utf-8 -*-
import tempfile
import unittest
from ..tub import TubWriter
import os 


class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        tempfolder = tempfile.TemporaryDirectory()
        path = os.path.join(tempfolder.name, 'new')
        inputs = ['name', 'age', 'pic']
        types = ['str', 'float', 'str']
        self.tub = TubWriter(path, inputs=inputs, types=types)
        
    def test_tub_create(self):
        self.tub.run('will', 323, 'asdfasdf')