#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car
Shows how to use an implement the drive-loop for a car with Arduino as its
drive train. Further it shows how to control the car with a joystick for the
sake of providing a functional demo.

Usage:
    manage.py (drive)

Options:
    -h --help          Show this screen.
"""
import os
import time

from docopt import docopt

import donkeycar as dk
from donkeycar.parts.actuator import ArduinoFirmata, ArdPWMSteering, ArdPWMThrottle
from donkeycar.parts.controller import get_js_controller


def drive(cfg):
    '''
    Construct a working robotic vehicle from many parts.
    Each part runs as a job in the Vehicle loop, calling either
    it's run or run_threaded method depending on the constructor flag `threaded`.
    All parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely manner.
    Parts may have named outputs and inputs. The framework handles passing named outputs
    to parts requesting the same named input.
    '''

    #Initialize car
    V = dk.vehicle.Vehicle()
    ctr = get_js_controller(cfg)
    V.add(ctr,
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)

    #Drive train setup
    arduino_controller = ArduinoFirmata(
        servo_pin=cfg.STEERING_ARDUINO_PIN, esc_pin=cfg.THROTTLE_ARDUINO_PIN)
    steering = ArdPWMSteering(controller=arduino_controller,
                              left_pulse=cfg.STEERING_ARDUINO_LEFT_PWM,
                              right_pulse=cfg.STEERING_ARDUINO_RIGHT_PWM)

    throttle = ArdPWMThrottle(controller=arduino_controller,
                              max_pulse=cfg.THROTTLE_ARDUINO_FORWARD_PWM,
                              zero_pulse=cfg.THROTTLE_ARDUINO_STOPPED_PWM,
                              min_pulse=cfg.THROTTLE_ARDUINO_REVERSE_PWM)

    V.add(steering, inputs=['user/angle'])
    V.add(throttle, inputs=['user/throttle'])

    #run the vehicle
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ,
            max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    if args['drive']:
        drive(cfg)
