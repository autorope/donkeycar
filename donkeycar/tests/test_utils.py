#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 14:17:59 2017

@author: wroscoe
"""
import os
import unittest
import tempfile
import shutil
from donkeycar.utils import map_range, gather_tub_paths, gather_tubs
from donkeycar.parts.tub import Tub, TubWriter

class TestMapping(unittest.TestCase):
    def test_positive(self):
        min = map_range(-100, -100, 100, 0, 1000)
        half = map_range(0, -100, 100, 0, 1000)
        max = map_range(100, -100, 100, 0, 1000)
        assert min == 0
        assert half == 500
        assert max == 1000

    def test_negative(self):
        ranges = (0, 100, 0, 1000)
        min = map_range(0, *ranges)
        half = map_range(50, *ranges)
        max = map_range(100, *ranges)
        assert min == 0
        assert half == 500
        assert max == 1000


    def test_reverse(self):
        ranges = (100, 0, 0, 1000)
        min = map_range(0, *ranges)
        half = map_range(50, *ranges)
        max = map_range(100, *ranges)
        assert min == 1000
        assert half == 500
        assert max == 0

class FakeTubs(unittest.TestCase):
    
    def setUp(self):
        self.temp_folder = tempfile.mkdtemp()
        self.path = os.path.join(self.temp_folder, 'new')
        self.inputs = ['name', 'age', 'pic']
        self.types = ['str', 'float', 'str']
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)
        tub.run('will', 323, 'asdfasdf')

    def tearDown(self):        
        shutil.rmtree(self.temp_folder)    

class TestTubGatherPaths(FakeTubs):
    
    def test_tub_gather_paths(self):
        cfg = lambda: None
        cfg.DATA_PATH = '.'
        paths = gather_tub_paths(cfg, self.path)
        assert type(paths) is list
        for path in paths:
            assert type(path) is str

class TestTubGather(FakeTubs):
    
    def test_tub_gather(self):
        cfg = lambda: None
        cfg.DATA_PATH = '.'
        tubs = gather_tubs(cfg, self.path)
        assert type(tubs) is list
        for tub in tubs:
            assert type(tub) is Tub

        
