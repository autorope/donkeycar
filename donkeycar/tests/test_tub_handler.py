# -*- coding: utf-8 -*-
import os
from donkeycar.parts.datastore import TubHandler
from .setup import tubs


def test_create_tub_handler(tubs):
    root_dir = tubs[0]
    th = TubHandler(root_dir)
    assert th is not None


def test_get_tub_list(tubs):
    root_dir = tubs[0]
    th = TubHandler(root_dir)
    assert len(th.get_tub_list()) == 5


def test_next_tub_number(tubs):
    root_dir = tubs[0]
    th = TubHandler(root_dir)
    assert th.next_tub_number() == 5


def test_new_tub_writer(tubs):
    root_dir = tubs[0]
    th = TubHandler(root_dir)
    inputs=['cam/image_array', 'angle', 'throttle']
    types=['image_array', 'float', 'float']
    tw = th.new_tub_writer(inputs, types)
    assert len(th.get_tub_list()) == 6
    print(tw.path)
    assert int(tw.path.split('_')[-2]) == 5