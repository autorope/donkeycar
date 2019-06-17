# -*- coding: utf-8 -*-
import tempfile
from tempfile import gettempdir
import unittest
from donkeycar.parts.datastore import TubWriter, Tub
from donkeycar.parts.datastore import TubHandler
from donkeycar.templates import complete
import donkeycar as dk
import os

import pytest

#fixtures
from .setup import tub, tub_path, on_pi, default_template, d2_path, custom_template

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
    complete.drive(cfg=cfg)


def test_custom_templates():
    template_names = ["complete", "basic_web", "square"]
    for template in template_names:
        path = custom_template(d2_path(gettempdir()), template=template)
        cfg = dk.load_config(os.path.join(path, 'config.py'))
        assert(cfg != None)
        mcfg = dk.load_config(os.path.join(path, 'myconfig.py'))
        assert(mcfg != None)
