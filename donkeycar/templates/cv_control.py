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
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.line_follower import LineFollower
from donkeycar.templates.complete import add_odometry, add_camera, \
    add_user_controller, add_drivetrain, add_simulator, add_imu
from donkeycar.templates.path_follow import ToggleRecording
from donkeycar.parts.logger import LoggerPart
from donkeycar.parts.transform import Lambda
from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.controller import JoystickController

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
    pid = PID(Kp=cfg.PID_P, Ki=cfg.PID_I, Kd=cfg.PID_D)
    V.add(LineFollower(pid, cfg),
          inputs=['cam/image_array'],
          outputs=['pilot/steering', 'pilot/throttle', 'recording', 'cv/image_array'],
          run_condition="run_pilot")

    def dec_pid_d():
        pid.Kd -= cfg.PID_D_DELTA
        logging.info("pid: d- %f" % pid.Kd)

    def inc_pid_d():
        pid.Kd += cfg.PID_D_DELTA
        logging.info("pid: d+ %f" % pid.Kd)

    def dec_pid_p():
        pid.Kp -= cfg.PID_P_DELTA
        logging.info("pid: p- %f" % pid.Kp)

    def inc_pid_p():
        pid.Kp += cfg.PID_P_DELTA
        logging.info("pid: p+ %f" % pid.Kp)


    recording_control = ToggleRecording(cfg.AUTO_RECORD_ON_THROTTLE)
    V.add(recording_control, inputs=['user/mode', "recording"], outputs=["recording"])


    #
    # Add buttons for handling various user actions
    # The button names are in configuration.
    # They may refer to game controller (joystick) buttons OR web ui buttons
    #
    # There are 5 programmable webui buttons, "web/w1" to "web/w5"
    # adding a button handler for a webui button
    # is just adding a part with a run_condition set to
    # the button's name, so it runs when button is pressed.
    #
    have_joystick = ctr is not None and isinstance(ctr, JoystickController)

    # button to toggle recording
    if cfg.TOGGLE_RECORDING_BTN:
        print(f"Toggle recording button is {cfg.TOGGLE_RECORDING_BTN}")
        if cfg.TOGGLE_RECORDING_BTN.startswith("web/w"):
            V.add(Lambda(lambda: recording_control.toggle_recording()), run_condition=cfg.TOGGLE_RECORDING_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.TOGGLE_RECORDING_BTN, recording_control.toggle_recording)

    # Buttons to tune PID constants
    if cfg.DEC_PID_P_BTN and cfg.PID_P_DELTA:
        print(f"Decrement PID P button is {cfg.DEC_PID_P_BTN}")
        if cfg.DEC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(lambda: dec_pid_p()), run_condition=cfg.DEC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_P_BTN, dec_pid_p)
    if cfg.INC_PID_P_BTN and cfg.PID_P_DELTA:
        print(f"Increment PID P button is {cfg.INC_PID_P_BTN}")
        if cfg.INC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(lambda: inc_pid_p()), run_condition=cfg.INC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_P_BTN, inc_pid_p)
    if cfg.DEC_PID_D_BTN and cfg.PID_D_DELTA:
        print(f"Decrement PID D button is {cfg.DEC_PID_D_BTN}")
        if cfg.DEC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(lambda: dec_pid_d()), run_condition=cfg.DEC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_D_BTN, dec_pid_d)
    if cfg.INC_PID_D_BTN and cfg.PID_D_DELTA:
        print(f"Increment PID D button is {cfg.INC_PID_D_BTN}")
        if cfg.INC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(lambda: inc_pid_d()), run_condition=cfg.INC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_D_BTN, inc_pid_d)

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
