# -*- coding: utf-8 -*-
import tempfile
from tempfile import gettempdir
import unittest
from donkeycar.parts.datastore import TubWriter, Tub
from donkeycar.parts.datastore import TubHandler
from donkeycar.templates import donkey2
import donkeycar as dk
import os

import pytest

#fixtures
from .setup import tub, tub_path, on_pi, default_template, d2_path

def test_config():
    path = default_template(d2_path(gettempdir()))
    cfg = dk.load_config(os.path.join(path, 'config.py'))
    assert(cfg != None)

def test_drive():
    path = default_template(d2_path(gettempdir()))
    myconfig = open(os.path.join(path, 'myconfig.py'), "wt")
    myconfig.write("CAMERA_TYPE = 'MOCK'\n")
    myconfig.write("DRIVE_TRAIN_TYPE = 'None'")
    myconfig.close()
    cfg = dk.load_config(os.path.join(path, 'config.py'))
    cfg.MAX_LOOPS = 10
    donkey2.drive(cfg=cfg)

