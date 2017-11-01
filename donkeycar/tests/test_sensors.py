import unittest

import pytest
from .setup import on_pi
from donkeycar.parts.camera import BaseCamera


def test_base_camera():
    cam = BaseCamera()


@pytest.mark.skipif(on_pi() == False, reason='only works on RPi')
def test_picamera():
    from donkeycar.parts.camera import PiCamera
    cam = PiCamera()
    cam.update()
    frame = cam.run_threaded()
    assert frame.shape == cam.camera.resolution



