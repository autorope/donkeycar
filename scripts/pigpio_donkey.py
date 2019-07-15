'''
# pigpio_donkey.py
# author: Tawn Kramer
# date: 3/11/2018
#
# Use the pigpio python module and daemon to get hardware pwm controls from
# a raspberrypi gpio pins and no additional hardware.
#
# Install and setup:
# sudo update && sudo apt install pigpio python3-pigpio& sudo systemctl start pigpiod
'''
import os
import donkeycar as dk
from donkeycar.parts.controller import PS3JoystickController
from donkeycar.parts.actuator import PWMSteering, PWMThrottle

import pigpio

class PiGPIO_PWM():
    def __init__(self, pin, pgio, freq=75):
        self.pin = pin
        self.pgio = pgio
        self.freq = freq
        self.pgio.set_mode(self.pin, pigpio.OUTPUT)

    def __del__(self):
        self.pgio.stop()

    def set_pulse(self, pulse):
        self.pgio.hardware_PWM(self.pin, self.freq, pulse)

    def run(self, pulse):
        self.set_pulse(pulse)


cfg = dk.load_config()

p = pigpio.pi()

V = dk.Vehicle()

cfg.STEERING_CHANNEL = 12
cfg.THROTTLE_CHANNEL = 13

PULSE_MULT = 1000

cfg.STEERING_LEFT_PWM = 40 * PULSE_MULT
cfg.STEERING_RIGHT_PWM = 170 * PULSE_MULT

cfg.THROTTLE_FORWARD_PWM = 170 * PULSE_MULT
cfg.THROTTLE_STOPPED_PWM = 105 * PULSE_MULT
cfg.THROTTLE_REVERSE_PWM = 40 * PULSE_MULT

V.add(PS3JoystickController(), inputs=['camera/arr'],
            outputs=['angle', 'throttle', 'mode', 'recording'],
            threaded=True)

steering_controller = PiGPIO_PWM(cfg.STEERING_CHANNEL, p)
steering = PWMSteering(controller=steering_controller,
                            left_pulse=cfg.STEERING_LEFT_PWM, 
                            right_pulse=cfg.STEERING_RIGHT_PWM)

throttle_controller = PiGPIO_PWM(cfg.THROTTLE_CHANNEL, p)
throttle = PWMThrottle(controller=throttle_controller,
                            max_pulse=cfg.THROTTLE_FORWARD_PWM,
                            zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                            min_pulse=cfg.THROTTLE_REVERSE_PWM)

V.add(steering, inputs=['angle'])
V.add(throttle, inputs=['throttle'])

V.start()


