from .setup import on_pi

from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.actuator import L298N_HBridge_2pin
import pytest


@pytest.mark.skipif(on_pi() == False, reason='Not on RPi')
def test_PCA9685():
    c = PCA9685(0)

@pytest.mark.skipif(on_pi() == False, reason='Not on RPi')
def test_PWMSteering():
    c = PCA9685(0)
    s = PWMSteering(c, 300, 440)


class _DutyPin:
    def __init__(self):
        self.duty = None

    def start(self, duty=0):
        self.duty = duty

    def duty_cycle(self, duty):
        self.duty = duty

    def stop(self):
        pass


def test_L298N_HBridge_2pin_zero_max_duty():
    forward, backward = _DutyPin(), _DutyPin()
    motor = L298N_HBridge_2pin(forward, backward, max_duty=0)
    for throttle in (-1, 0, 1):
        motor.run(throttle)
        assert forward.duty == 0
        assert backward.duty == 0
