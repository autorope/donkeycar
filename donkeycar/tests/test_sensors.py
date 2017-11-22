import unittest

import pytest
from .setup import on_pi
from donkeycar.parts.camera import BaseCamera


def test_base_camera():
    cam = BaseCamera()


@pytest.mark.skipif(on_pi() == False, reason='only works on RPi')
def test_picamera():
    from donkeycar.parts.camera import PiCamera
    resolution = (120,160)
    cam = PiCamera(resolution=resolution)
    frame = cam.run()
    #assert shape is as expected. img_array shape shows (width, height, channels)
    assert frame.shape[:2] == resolution[:]

