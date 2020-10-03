# -*- coding: utf-8 -*-

from tempfile import gettempdir
from donkeycar.templates import complete
import donkeycar as dk
import os

from .setup import default_template, d2_path, custom_template


def test_config():
    path = default_template(d2_path(gettempdir()))
    cfg = dk.load_config(os.path.join(path, 'config.py'))
    assert (cfg is not None)


def test_drive():
    path = default_template(d2_path(gettempdir()))
    myconfig = open(os.path.join(path, 'myconfig.py'), "wt")
    myconfig.write("CAMERA_TYPE = 'MOCK'\n")
    myconfig.write("USE_SSD1306_128_32 = False \n")
    myconfig.write("DRIVE_TRAIN_TYPE = 'None'")
    myconfig.close()
    cfg = dk.load_config(os.path.join(path, 'config.py'))
    cfg.MAX_LOOPS = 10
    complete.drive(cfg=cfg)


def test_custom_templates():
    template_names = ["complete", "basic", "square"]
    for template in template_names:
        path = custom_template(d2_path(gettempdir()), template=template)
        cfg = dk.load_config(os.path.join(path, 'config.py'))
        assert (cfg is not None)
        mcfg = dk.load_config(os.path.join(path, 'myconfig.py'))
        assert (mcfg is not None)
