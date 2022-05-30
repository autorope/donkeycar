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

Starts in user mode.
- The user flow to 'train' a path.   
  - start "python manage.py drive" 
  - This starts in user mode; so user is in manual drive mode 
    driving records path waypoints.
  - drive to record a path; make the start and end close to each other.
  - if you don't like path, select the reset button and it will
    reset the origin _AND_ erase the path from memory.  MOve the
    vehicle back to where the physical origin is and start driving
    again to record a new path.
  - if you like the path, select the save button to save it. 
- The user flow for autopilot:  
  - record or load a path (select load button) 
  - select auto-pilot mode using joystick or web ui.  The
    vehicle will start trying to follow the recorded path.
  - switch back user model to stop autopilot.
  - to restart using the saved path; 
    - select reset button; this will erase path and reset origin 
    - select load button to load path
    - put the car back at the physical origin.


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
from donkeycar.parts.controller import JoystickController
from donkeycar.parts.path import CsvPath, RosPath, PathPlot, CTE, PID_Pilot, PlotCircle, PImage, OriginOffset
from donkeycar.parts.transform import PIDController
from donkeycar.parts.kinematics import TwoWheelSteeringThrottle
from donkeycar.templates.complete import add_odometry, add_camera, add_user_controller, add_drivetrain, add_simulator
from donkeycar.parts.logger import LoggerPart
from donkeycar.parts.pipe import Pipe

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

    is_differential_drive = cfg.DRIVE_TRAIN_TYPE.startswith("DC_TWO_WHEEL")

    #Initialize car
    V = dk.vehicle.Vehicle()

    if cfg.HAVE_SOMBRERO:
        from donkeycar.utils import Sombrero
        s = Sombrero()
   
    #Initialize logging before anything else to allow console logging
    if cfg.HAVE_CONSOLE_LOGGING:
        logger.setLevel(logging.getLevelName(cfg.LOGGING_LEVEL))
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(cfg.LOGGING_FORMAT))
        logger.addHandler(ch)

    if cfg.HAVE_MQTT_TELEMETRY:
        from donkeycar.parts.telemetry import MqttTelemetry
        tel = MqttTelemetry(cfg)

    #
    # if we are using the simulator, set it up
    #
    add_simulator(V, cfg)

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

    if cfg.HAVE_T265:
        from donkeycar.parts.realsense2 import RS_T265
        if cfg.HAVE_ODOM and not os.path.exists(cfg.WHEEL_ODOM_CALIB):
            print("You must supply a json file when using odom with T265. There is a sample file in templates.")
            print("cp donkeycar/donkeycar/templates/calibration_odometry.json .")
            exit(1)

        #
        # NOTE: image output on the T265 is broken in the python API and
        #       will never get fixed, so not image output from T265
        #
        rs = RS_T265(image_output=False, calib_filename=cfg.WHEEL_ODOM_CALIB, device_id=cfg.REALSENSE_T265_ID)
        V.add(rs, inputs=['enc/vel_m_s'], outputs=['rs/pos', 'rs/vel', 'rs/acc'], threaded=True)

        #
        # Pull out the realsense T265 position stream, output 2d coordinates we can use to map.
        # Transform the T265 augmented reality coordinate system into a traditional
        # top-down POSE coordinate system where east is positive-x and north is positive-y.
        #
        class PosStream:
            def run(self, pos):
                #y is up, x is right, z is backwards/forwards (negative going forwards)
                return -pos.z, -pos.x

        V.add(PosStream(), inputs=['rs/pos'], outputs=['pos/x', 'pos/y'])

    #
    # gps outputs ['pos/x', 'pos/y']
    #
    add_gps(V, cfg)

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
    ctr = add_user_controller(V, cfg, use_joystick, input_image = 'map/image')

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
    path = CsvPath(min_dist=cfg.PATH_MIN_DIST)
    V.add(path, inputs=['pos/x', 'pos/y'], outputs=['path'], run_condition='run_user')

    if cfg.DONKEY_GYM:
        lpos = LoggerPart(inputs=['dist/left', 'dist/right', 'dist', 'pos/pos_x', 'pos/pos_y', 'yaw'], level="INFO", logger="simulator")
        V.add(lpos, inputs=lpos.inputs)
    if cfg.HAVE_ODOM:
        if cfg.HAVE_ODOM_2:
            lpos = LoggerPart(inputs=['enc/left/distance', 'enc/right/distance', 'enc/left/timestamp', 'enc/right/timestamp'], level="INFO", logger="odometer")
            V.add(lpos, inputs=lpos.inputs)
        lpos = LoggerPart(inputs=['enc/distance', 'enc/timestamp'], level="INFO", logger="odometer")
        V.add(lpos, inputs=lpos.inputs)
        lpos = LoggerPart(inputs=['pos/x', 'pos/y', 'pos/angle'], level="INFO", logger="kinematics")
        V.add(lpos, inputs=lpos.inputs)

    # When a path is loaded, we will be in follow mode. We will not record.
    path_loaded = False
    if os.path.exists(cfg.PATH_FILENAME):
        path.load(cfg.PATH_FILENAME)
        path_loaded = True

    def save_path():
        if path.length() > 0:
            if path.save(cfg.PATH_FILENAME):
                print("That path was saved to ", cfg.PATH_FILENAME)
            else:
                print("The path could NOT be saved; check the PATH_FILENAME in myconfig.py to make sure it is a legal path")
        else:
            print("There is no path to save; try recording the path.")

    def load_path():
       if path.load(cfg.PATH_FILENAME):
           path_loaded = True
           mode = 'user'
           print("The path was loaded was loaded from ", cfg.PATH_FILENAME)
       else:
           print("path _not_ loaded; make sure you have saved a path.")

    def erase_path():
        global mode, path_loaded
        origin_reset.init_to_last
        if path.reset():
            mode = 'user'
            path_loaded = False
            print("The origin and the path were reset; you are ready to record a new path.")
        else:
            print("The origin was reset; you are ready to record a new path.")

    def reset_origin():
        """
        Reset effective pose to (0, 0)
        """
        origin_reset.init_to_last
        print("The origin was reset to the current position.")

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

        # allow controller to (re)load the path
        ctr.set_button_down_trigger(cfg.LOAD_PATH_BTN, load_path)

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

    #
    # draw a map image as the vehicle moves
    #
    loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = "blue")
    V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'], run_condition='run_pilot')

    loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = "green")
    V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'], run_condition='run_user')

    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
        max_loop_count=cfg.MAX_LOOPS)


def add_gps(V, cfg):
    if cfg.HAVE_GPS:
        from donkeycar.parts.gps import GpsPosition
        from donkeycar.parts.pipe import Pipe
        gps = GpsPosition(cfg.GPS_SERIAL, cfg.GPS_BAUDRATE)
        V.add(gps, outputs=['gps/timestamp', 'gps/utm/longitude', 'gps/utm/latitude'])
        V.add(Pipe(), inputs=['gps/utm/longitude', 'gps/utm/latitude'], outputs=['pos/x', 'pos/y'])



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

