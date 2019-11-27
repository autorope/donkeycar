from .setup import on_pi

from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
import pytest


@pytest.mark.skipif(on_pi() == False, reason='Not on RPi')
def test_PCA9685():
    c = PCA9685(0)

@pytest.mark.skipif(on_pi() == False, reason='Not on RPi')
def test_PWMSteering():
    c = PCA9685(0)
    s = PWMSteering(c)
