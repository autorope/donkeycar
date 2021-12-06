#!/usr/bin/env python3
"""
Scripts to record a path by driving a donkey car 
and using an autopilot to drive the recoded path.
Works with wheel encoders and/or Intel T265

Usage:
    manage.py (drive) [--js] [--log=INFO] [--camera=(single|stereo)]
 

Options:
    -h --help          Show this screen.
    --js               Use physical joystick.
    -f --file=<file>   A text file containing paths to tub files, one per line. Option may be used more than once.
    --meta=<key:value> Key/Value strings describing describing a piece of meta data about this drive. Option may be used more than once.
"""
import os
import sys
import time
import logging
import json
from subprocess import Popen
import shlex

#
# import cv2 early to avoid issue with importing after tensorflow
# see https://github.com/opencv/opencv/issues/14884#issuecomment-599852128
#
try:
    import cv2
except:
    pass


from docopt import docopt
import numpy as np

import donkeycar as dk
from donkeycar.parts.controller import WebFpv, get_js_controller, LocalWebController, JoystickController
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.path import Path, PathPlot, CTE, PID_Pilot, PlotCircle, PImage, OriginOffset
from donkeycar.parts.transform import PIDController
from donkeycar.parts.kinematics import TwoWheelSteeringThrottle
from donkeycar.templates.complete import add_odometry, add_camera, add_user_controller, add_drivetrain


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

    if cfg.HAVE_SOMBRERO:
        from donkeycar.utils import Sombrero
        s = Sombrero()
   
    is_differential_drive = cfg.DRIVE_TRAIN_TYPE.startswith("DC_TWO_WHEEL")

    if cfg.HAVE_ODOM:
        #
        # setup encoders, odometry and pose estimation
        #
        add_odometry(V, cfg)
    else:
        # we give the T265 no calib to indicated we don't have odom
        cfg.WHEEL_ODOM_CALIB = None

        #This dummy part to satisfy input needs of RS_T265 part.
        class NoOdom():
            def run(self):
                return 0.0

        V.add(NoOdom(), outputs=['enc/vel_m_s'])
   
    #
    # TODO: once we have Unicycle kinematics to provide pose, make T265 optional.
    #

    if cfg.CAMERA_TYPE == "T265":
        from donkeycar.parts.realsense2 import RS_T265
        if cfg.HAVE_ODOM and not os.path.exists(cfg.WHEEL_ODOM_CALIB):
            print("You must supply a json file when using odom with T265. There is a sample file in templates.")
            print("cp donkeycar/donkeycar/templates/calibration_odometry.json .")
            exit(1)

        rs = RS_T265(image_output=False, calib_filename=cfg.WHEEL_ODOM_CALIB)
        V.add(rs, inputs=['enc/vel_m_s'], outputs=['rs/pos', 'rs/vel', 'rs/acc', 'rs/camera/left/img_array'], threaded=True)

        # Pull out the realsense T265 position stream, output 2d coordinates we can use to map.
        class PosStream:
            def run(self, pos):
                #y is up, x is right, z is backwards/forwards (negative going forwards)
                return -pos.z, -pos.x

        V.add(PosStream(), inputs=['rs/pos'], outputs=['pos/x', 'pos/y'])
    else:
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
    ctr = add_user_controller(V, cfg, use_joystick)

    #
    # This part will reset the car back to the origin. You must put the car in the known origin
    # and push the cfg.RESET_ORIGIN_BTN on your controller. This will allow you to induce an offset
    # in the mapping.
    #
    origin_reset = OriginOffset()
    V.add(origin_reset, inputs=['pos/x', 'pos/y'], outputs=['pos/x', 'pos/y'] )


    class UserCondition:
        def run(self, mode):
            if mode == 'user':
                return True
            else:
                return False

    V.add(UserCondition(), inputs=['user/mode'], outputs=['run_user'])

    #See if we should even run the pilot module. 
    #This is only needed because the part run_condition only accepts boolean
    class PilotCondition:
        def run(self, mode):
            if mode == 'user':
                return False
            else:
                return True

    V.add(PilotCondition(), inputs=['user/mode'], outputs=['run_pilot'])



    # This is the path object. It will record a path when distance changes and it travels
    # at least cfg.PATH_MIN_DIST meters. Except when we are in follow mode, see below...
    path = Path(min_dist=cfg.PATH_MIN_DIST)
    V.add(path, inputs=['pos/x', 'pos/y'], outputs=['path'], run_condition='run_user')

    # When a path is loaded, we will be in follow mode. We will not record.
    path_loaded = False
    if os.path.exists(cfg.PATH_FILENAME):
        path.load(cfg.PATH_FILENAME)
        path_loaded = True

    def save_path():
        path.save(cfg.PATH_FILENAME)
        print("saved path:", cfg.PATH_FILENAME)

    def erase_path():
        global mode, path_loaded
        if os.path.exists(cfg.PATH_FILENAME):
            os.remove(cfg.PATH_FILENAME)
            mode = 'user'
            path_loaded = False
            print("erased path", cfg.PATH_FILENAME)
        else:
            print("no path found to erase")
    
    def reset_origin():
        print("Resetting origin")
        origin_reset.init_to_last


    # Here's an image we can map to.
    img = PImage(clear_each_frame=True)
    V.add(img, outputs=['map/image'])

    # This PathPlot will draw path on the image

    plot = PathPlot(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET)
    V.add(plot, inputs=['map/image', 'path'], outputs=['map/image'])

    # This will use path and current position to output cross track error
    cte = CTE()
    V.add(cte, inputs=['path', 'pos/x', 'pos/y'], outputs=['cte/error'], run_condition='run_pilot')

    # This will use the cross track error and PID constants to try to steer back towards the path.
    pid = PIDController(p=cfg.PID_P, i=cfg.PID_I, d=cfg.PID_D)
    pilot = PID_Pilot(pid, cfg.PID_THROTTLE)
    V.add(pilot, inputs=['cte/error'], outputs=['pilot/angle', 'pilot/throttle'], run_condition="run_pilot")

    def dec_pid_d():
        pid.Kd -= 0.5
        logging.info("pid: d- %f" % pid.Kd)

    def inc_pid_d():
        pid.Kd += 0.5
        logging.info("pid: d+ %f" % pid.Kd)

    #
    # add controller buttons for saving path and modifying PID
    #
    if ctr is not None and isinstance(ctr, JoystickController):
        # Here's a trigger to save the path. Complete one circuit of your course, when you
        # have exactly looped, or just shy of the loop, then save the path and shutdown
        # this process. Restart and the path will be loaded.
        ctr.set_button_down_trigger(cfg.SAVE_PATH_BTN, save_path)

        # Here's a trigger to erase a previously saved path. 
        ctr.set_button_down_trigger(cfg.ERASE_PATH_BTN, erase_path)

        # Here's a trigger to reset the origin. 
        ctr.set_button_down_trigger(cfg.RESET_ORIGIN_BTN, reset_origin)

        # Buttons to tune PID constants
        ctr.set_button_down_trigger("L2", dec_pid_d)
        ctr.set_button_down_trigger("R2", inc_pid_d)
    

    #Choose what inputs should change the car.
    class DriveMode:
        def run(self, mode, 
                    user_angle, user_throttle,
                    pilot_angle, pilot_throttle):
            if mode == 'user':
                #print(user_angle, user_throttle)
                return user_angle, user_throttle
            
            elif mode == 'local_angle':
                return pilot_angle, user_throttle
            
            else: 
                return pilot_angle, pilot_throttle
        
    V.add(DriveMode(), 
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'], 
          outputs=['angle', 'throttle'])
    

    #
    # To make differential drive steer, 
    # divide throttle between motors based on the steering value
    #
    if is_differential_drive:
        V.add(TwoWheelSteeringThrottle(),
            inputs=['throttle', 'angle'],
            outputs=['left/throttle', 'right/throttle'])

    #
    # Setup drivetrain
    #
    add_drivetrain(V, cfg)

    # Print Joystick controls
    if ctr is not None and isinstance(ctr, JoystickController):
        ctr.print_controls()

    if path_loaded:
        print("###############################################################################")
        print("Loaded path:", cfg.PATH_FILENAME)
        print("Make sure your car is sitting at the origin of the path.")
        print("View web page and refresh. You should see your path.")
        print("Hit 'select' twice to change to ai drive mode.")
        print("You can press the X button (e-stop) to stop the car at any time.")
        print("Delete file", cfg.PATH_FILENAME, "and re-start")
        print("to record a new path.")
        print("###############################################################################")
        carcolor = "blue"
        loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = carcolor)
        V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'])

    else:
        print("###############################################################################")
        print("You are now in record mode. Open the web page to your car")
        print("and as you drive you should see a path.")
        print("Complete one circuit of your course.")
        print("When you have exactly looped, or just shy of the ")
        print("loop, then save the path (press %s)." % cfg.SAVE_PATH_BTN)
        print("You can also erase a path with the Triangle button.")
        print("When you're done, close this process with Ctrl+C.")
        print("Place car exactly at the start. ")
        print("Then restart the car with 'python manage drive'.")
        print("It will reload the path and you will be ready to  ")
        print("follow the path using  'select' to change to ai drive mode.")
        print("You can also press the Square button to reset the origin")
        print("###############################################################################")
        carcolor = 'green'
        loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = carcolor)
        V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'])

    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
        max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    log_level = args['--log'] or "INFO"
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)

    
    if args['drive']:
        drive(cfg, use_joystick=args['--js'], camera_type=args['--camera'])

