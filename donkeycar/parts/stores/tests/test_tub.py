# -*- coding: utf-8 -*-
import tempfile
import unittest
from ..tub import TubWriter
import os 


class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        tempfolder = tempfile.TemporaryDirectory()
        self.path = os.path.join(tempfolder.name, 'new')
        self.inputs = ['name', 'age', 'pic']
        self.types = ['str', 'float', 'str']
        
    def test_tub_create(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)
        
    def test_tub_path(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)
        tub.run('will', 323, 'asdfasdf')