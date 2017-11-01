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
from donkeycar.utils import map_range

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


