#!/usr/bin/env python3
"""

Scripts to drive on autopilot using computer vision

Usage:
    manage.py (drive) [--js] [--log=INFO] [--camera=(single|stereo)] [--myconfig=<filename>]


Options:
    -h --help          Show this screen.
    --js               Use physical joystick.
    --myconfig=filename     Specify myconfig file to use.
                            [default: myconfig.py]
"""
import logging

from docopt import docopt

import donkeycar as dk
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.line_follower import LineFollower
from donkeycar.templates.complete import add_odometry, add_camera, \
    add_user_controller, add_drivetrain, add_simulator, add_imu
from donkeycar.parts.logger import LoggerPart
from donkeycar.parts.transform import Lambda
from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.controller import JoystickController


def drive(cfg, use_joystick=False, camera_type='single'):
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
    # setup primary camera
    #
    add_camera(V, cfg, camera_type)

    #
    # add the user input controller(s)
    # - this will add the web controller
    # - it will optionally add any configured 'joystick' controller
    #
    has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
    ctr = add_user_controller(V, cfg, use_joystick, input_image = 'ui/image_array')

    #
    # explode the web buttons into their own key/values in memory
    #
    V.add(ExplodeDict(V.mem, "web/"), inputs=['web/buttons'])

    #
    # track user vs autopilot condition
    #
    class UserPilotCondition:
        def run(self, mode, user_image, pilot_image):
            if mode == 'user':
                return True, False, user_image
            else:
                return False, True, pilot_image
    V.add(UserPilotCondition(),
          inputs=['user/mode', "cam/image_array", "cv/image_array"],
          outputs=['run_user', "run_pilot", "ui/image_array"])



    #
    # Computer Vision Controller
    #
    V.add(LineFollower(cfg.OVERLAY_IMAGE, False),
          inputs=['cam/image_array'],
          outputs=['pilot/steering', 'pilot/throttle', 'recording', 'cv/image_array'],
          run_condition="run_pilot")

    #
    # Choose what inputs should change the car.
    #
    # TODO: when we merge pose estimate branch, update 'angle' to 'steering'
    class DriveMode:
        def run(self, mode,
                    user_angle, user_throttle,
                    pilot_angle, pilot_throttle):
            if mode == 'user':
                return user_angle, user_throttle

            elif mode == 'local_angle':
                return pilot_angle if pilot_angle else 0.0, user_throttle

            else:
                return pilot_angle if pilot_angle else 0.0, \
                       pilot_throttle * cfg.AI_THROTTLE_MULT \
                           if pilot_throttle else 0.0

    V.add(DriveMode(),
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/steering', 'pilot/throttle'],
          outputs=['angle', 'throttle'])


    #
    # Setup drivetrain
    #
    add_drivetrain(V, cfg)

    # Print Joystick controls
    if ctr is not None and isinstance(ctr, JoystickController):
        ctr.print_controls()


    #
    # add tub to save data
    #
    inputs=['cam/image_array',
            'angle', 'throttle']

    types=['image_array',
           'float', 'float']

    th = TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, outputs=["tub/num_records"], run_condition="recording")

    #
    # run the vehicle
    #
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config(myconfig=args['--myconfig'])

    log_level = args['--log'] or "INFO"
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)

    if args['drive']:
        drive(cfg, use_joystick=args['--js'], camera_type=args['--camera'])
