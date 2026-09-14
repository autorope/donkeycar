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
from donkeycar.parts.controls import (
    BehaviorEventMapper,
    InputControllerEvents,
    TogglePilotMode,
    UserSteering,
    UserThrottle,
    get_behavior_map,
    get_input_controller,
)
from donkeycar.parts.controls import mapping as behaviors


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

    #
    # The controller reports which of its controls moved; the parts below
    # decide what that means, so which button does what is
    # CONTROLLER_BEHAVIOR_MAP in myconfig.py rather than an edit here.
    #
    V.add(InputControllerEvents(V.mem, get_input_controller(cfg)),
          threaded=True)

    mapper = BehaviorEventMapper(V.mem, get_behavior_map(cfg))
    mapper.show_map()
    V.add(mapper)

    #
    # This template calls its steering 'user/angle', and has no camera, tub
    # or pilot, so it binds only what it can actually use.
    #
    V.add(UserSteering(scale=cfg.JOYSTICK_STEERING_SCALE,
                       dead_zone=cfg.JOYSTICK_DEADZONE),
          inputs=[behaviors.STEERING], outputs=['user/angle'],
          run_condition=behaviors.STEERING)
    V.add(UserThrottle(direction=cfg.JOYSTICK_THROTTLE_DIR,
                       scale=cfg.JOYSTICK_MAX_THROTTLE,
                       dead_zone=cfg.JOYSTICK_DEADZONE),
          inputs=[behaviors.THROTTLE], outputs=['user/throttle'],
          run_condition=behaviors.THROTTLE)
    V.add(TogglePilotMode(), inputs=['user/mode'], outputs=['user/mode'],
          run_condition=behaviors.TOGGLE_PILOT_MODE)

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
