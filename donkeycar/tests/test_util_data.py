#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 14:17:59 2017

@author: wroscoe
"""
import unittest
import pytest


from donkeycar.util.data import linear_bin
from donkeycar.util.data import linear_unbin
from donkeycar.util.data import bin_Y
from donkeycar.util.data import unbin_Y
from donkeycar.util.data import map_range
from donkeycar.util.data import merge_two_dicts
from donkeycar.util.data import param_gen


def create_lbin(marker_index):
    """ Create a linear binary array with value set """
    l = [0] * 15
    l[marker_index] = 1
    return l


class TestLinearBin(unittest.TestCase):

    def test_zero(self):
        res = linear_bin(0)
        assert res[7] == 1
        assert sum(res[:7]) == 0
        assert sum(res[8:]) == 0

    def test_positive(self):
        res = linear_bin(1)
        assert res[14] == 1
        assert sum(res[:14]) == 0

    def test_negative(self):
        res = linear_bin(-1)
        assert res[0] == 1
        assert sum(res[1:]) == 0

    def test_illegal_pos(self):
        with pytest.raises(IndexError):
            linear_bin(2)

    def test_illegal_type(self):
        with pytest.raises(TypeError):
            linear_bin('0')


class TestLinearUnbin(unittest.TestCase):

    def test_zero(self):
        l = create_lbin(7)
        res = linear_unbin(l)
        assert res == 0.0

    def test_positive(self):
        l = create_lbin(14)
        res = linear_unbin(l)
        assert res == 1.0

    def test_negative(self):
        l = create_lbin(0)
        res = linear_unbin(l)
        assert res == -1.0

    def test_empty_list(self):
        res = linear_unbin( [0] * 15 )
        assert res == -1.0

    def test_illegal_list(self):
        with pytest.raises(ValueError):
            linear_unbin( [0] * 10 )


class TestBinY(unittest.TestCase):

    def test_normal_list(self):
        l = [ -1, 0, 1 ]
        res = bin_Y(l)

        # negative
        assert res[0][0] == 1
        assert sum(res[0][1:]) == 0

        # zero
        assert res[1][7] == 1
        assert sum(res[1][:7]) == 0
        assert sum(res[1][8:]) == 0

        # positive
        assert res[2][14] == 1
        assert sum(res[2][:14]) == 0

class TestUnbinY(unittest.TestCase):

    def test_normal_list(self):
        l = [ create_lbin(0), create_lbin(7), create_lbin(14) ]
        res = unbin_Y(l)

        # negative
        assert res[0] == -1.0

        # zero
        assert res[1] == 0.0

        # positive
        assert res[2] == 1.0


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


class TestMergeDicts(unittest.TestCase):

    def test_merge_two_dicts(self):
        d1 = { 'a' : 1, 'b' : 2, 'c' : 3 }
        d2 = { 10 : 'hi', 'bob' : 20 }
        res = merge_two_dicts(d1, d2)

        assert res == { 'a' : 1, 'b' : 2, 'c' : 3, 10 : 'hi', 'bob' : 20 }

class TestParamGen(unittest.TestCase):

    def test_param_gen(self):
        g = param_gen({ 'a' : [ 'opt1', 'opt2' ], 'b' : [ 'opt3', 'opt4' ] })
        l = [ x for x in g ]
        expected = [
                {'a': 'opt1', 'b': 'opt3'},
                {'a': 'opt1', 'b': 'opt4'},
                {'a': 'opt2', 'b': 'opt3'},
                {'a': 'opt2', 'b': 'opt4'}
            ]
        self.assertCountEqual(expected, l)