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
from simple_pid import PID

import donkeycar as dk
from donkeycar.parts.tub_v2 import TubWriter
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.line_follower import LineFollower
from donkeycar.templates.complete import add_odometry, add_camera, \
    add_user_controller, add_controller_behaviors, add_drivetrain, \
    add_simulator, add_imu, DriveMode, UserPilotCondition
from donkeycar.parts.logger import LoggerPart
from donkeycar.parts.transform import Lambda
from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.controls import AdjustPid
from donkeycar.parts.controls.behaviors import AutoRecordOnThrottle
from donkeycar.parts.controls import mapping as behaviors

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def drive(cfg, use_joystick=False, camera_type='single', meta=[]):
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
    # if we are using the simulator, set it up
    #
    add_simulator(V, cfg)

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
    V.add(UserPilotCondition(show_pilot_image=getattr(cfg, 'OVERLAY_IMAGE', False)),
          inputs=['user/mode', "cam/image_array", "cv/image_array"],
          outputs=['run_user', "run_pilot", "ui/image_array"])

    #
    # PID controller to be used with cv_controller
    #
    pid = PID(Kp=cfg.PID_P, Ki=cfg.PID_I, Kd=cfg.PID_D)
    #
    # Computer Vision Controller
    #
    add_cv_controller(V, cfg, pid,
                      cfg.CV_CONTROLLER_MODULE,
                      cfg.CV_CONTROLLER_CLASS,
                      cfg.CV_CONTROLLER_INPUTS,
                      cfg.CV_CONTROLLER_OUTPUTS,
                      cfg.CV_CONTROLLER_CONDITION)

    #
    # Recording follows the throttle, or a button toggles it -- never both,
    # since both write 'recording' and whichever ran later would win.
    # add_controller_behaviors adds the button when auto-record is off.
    #
    if cfg.AUTO_RECORD_ON_THROTTLE:
        V.add(AutoRecordOnThrottle(
                  dead_zone=cfg.JOYSTICK_DEADZONE,
                  record_in_autopilot=getattr(cfg, 'RECORD_DURING_AI', False)),
              inputs=['user/throttle', 'user/mode'],
              outputs=['recording'])


    #
    # Tuning the PID while driving.  Each is bound to a behavior rather
    # than to a button, so a gamepad button and a web button reach it the
    # same way -- which is why this is no longer written twice per binding,
    # once for each route in.  Which control drives each one is
    # CONTROLLER_BEHAVIOR_MAP in myconfig.py.
    #
    if cfg.PID_P_DELTA:
        V.add(AdjustPid(pid, 'Kp', +cfg.PID_P_DELTA),
              run_condition=behaviors.INCREASE_PID_P)
        V.add(AdjustPid(pid, 'Kp', -cfg.PID_P_DELTA),
              run_condition=behaviors.DECREASE_PID_P)
    if cfg.PID_D_DELTA:
        V.add(AdjustPid(pid, 'Kd', +cfg.PID_D_DELTA),
              run_condition=behaviors.INCREASE_PID_D)
        V.add(AdjustPid(pid, 'Kd', -cfg.PID_D_DELTA),
              run_condition=behaviors.DECREASE_PID_D)

    #
    # Decide what inputs should change the car's steering and throttle
    # based on the choice of user or autopilot drive mode
    #
    V.add(DriveMode(cfg.AI_THROTTLE_MULT),
          inputs=['user/mode', 'user/steering', 'user/throttle',
                  'pilot/steering', 'pilot/throttle'],
          outputs=['steering', 'throttle'])


    #
    # Setup drivetrain
    #
    add_drivetrain(V, cfg)


    #
    # OLED display setup
    #
    if cfg.USE_SSD1306_128_32:
        from donkeycar.parts.oled import OLEDPart
        auto_record_on_throttle = cfg.USE_JOYSTICK_AS_DEFAULT and cfg.AUTO_RECORD_ON_THROTTLE
        oled_part = OLEDPart(cfg.SSD1306_128_32_I2C_ROTATION, cfg.SSD1306_RESOLUTION, auto_record_on_throttle)
        V.add(oled_part, inputs=['recording', 'tub/num_records', 'user/mode'], outputs=[], threaded=True)


    #
    # add tub to save data
    #
    inputs=['cam/image_array',
            'steering', 'throttle']

    types=['image_array',
           'float', 'float']

    #
    # Create data storage part
    #
    tub_path = TubHandler(path=cfg.DATA_PATH).create_tub_path() if \
        cfg.AUTO_CREATE_NEW_TUB else cfg.DATA_PATH
    meta += getattr(cfg, 'METADATA', [])
    tub_writer = TubWriter(tub_path, inputs=inputs, types=types, metadata=meta)
    V.add(tub_writer, inputs=inputs, outputs=["tub/num_records"], run_condition='recording')

    if cfg.DONKEY_GYM:
        print("You can now go to http://localhost:%d to drive your car." % cfg.WEB_CONTROL_PORT)
    else:
        print("You can now go to <your hostname.local>:%d to drive your car." % cfg.WEB_CONTROL_PORT)
    if has_input_controller:
        print("You can now move your controller to drive your car.")

    #
    # The parts a controller drives, bound to behaviors rather than to
    # buttons.  Added last because some of them need the tub.
    #
    add_controller_behaviors(V, cfg, tub=tub_writer.tub)

    #
    # run the vehicle
    #
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)


#
# Computer Vision Controller
#
def add_cv_controller(
        V, cfg, pid,
        module_name="donkeycar.parts.line_follower",
        class_name="LineFollower",
        inputs=['cam/image_array'],
        outputs=['pilot/steering', 'pilot/throttle', 'cv/image_array'],
        run_condition="run_pilot"):

        # __import__ the module
        module = __import__(module_name)

        # walk module path to get to module with class
        for attr in module_name.split('.')[1:]:
            module = getattr(module, attr)

        my_class = getattr(module, class_name)

        # add instance of class to vehicle
        V.add(my_class(pid, cfg),
              inputs=inputs,
              outputs=outputs,
              run_condition=run_condition)


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
