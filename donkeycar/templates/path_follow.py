#!/usr/bin/env python3
"""
Scripts to drive a donkey car using Intel T265

Usage:
    manage.py (drive) [--log=INFO]
 

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

from docopt import docopt
import numpy as np
import pigpio

import donkeycar as dk
from donkeycar.parts.controller import WebFpv, get_js_controller, LocalWebController
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.path import Path, PathPlot, CTE, PID_Pilot, PlotCircle, PImage, OriginOffset
from donkeycar.parts.transform import PIDController
from donkeycar.parts.pigpio_enc import PiPGIOEncoder, OdomDist
from donkeycar.parts.realsense2 import RS_T265
        

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

    if cfg.HAVE_SOMBRERO:
        from donkeycar.utils import Sombrero
        s = Sombrero()
   
    ctr = get_js_controller(cfg)

    V.add(ctr,
            inputs=['cam/image_array'],
            outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
            threaded=True)

    if cfg.HAVE_ODOM:
        pi = pigpio.pi()
        enc = PiPGIOEncoder(cfg.ODOM_PIN, pi)
        V.add(enc, outputs=['enc/ticks'])

        odom = OdomDist(mm_per_tick=cfg.MM_PER_TICK, debug=cfg.ODOM_DEBUG)
        V.add(odom, inputs=['enc/ticks', 'user/throttle'], outputs=['enc/dist_m', 'enc/vel_m_s', 'enc/delta_vel_m_s'])

        if not os.path.exists(cfg.WHEEL_ODOM_CALIB):
            print("You must supply a json file when using odom with T265. There is a sample file in templates.")
            print("cp donkeycar/donkeycar/templates/calibration_odometry.json .")
            exit(1)

    else:
        # we give the T265 no calib to indicated we don't have odom
        cfg.WHEEL_ODOM_CALIB = None

        #This dummy part to satisfy input needs of RS_T265 part.
        class NoOdom():
            def run(self):
                return 0.0

        V.add(NoOdom(), outputs=['enc/vel_m_s'])
   
    # This requires use of the Intel Realsense T265
    rs = RS_T265(image_output=False, calib_filename=cfg.WHEEL_ODOM_CALIB)
    V.add(rs, inputs=['enc/vel_m_s'], outputs=['rs/pos', 'rs/vel', 'rs/acc', 'rs/camera/left/img_array'], threaded=True)

    # Pull out the realsense T265 position stream, output 2d coordinates we can use to map.
    class PosStream:
        def run(self, pos):
            #y is up, x is right, z is backwards/forwards
            return pos.x, pos.z

    V.add(PosStream(), inputs=['rs/pos'], outputs=['pos/x', 'pos/y'])

    # This part will reset the car back to the origin. You must put the car in the known origin
    # and push the cfg.RESET_ORIGIN_BTN on your controller. This will allow you to induce an offset
    # in the mapping.


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


    
    # Here's a trigger to save the path. Complete one circuit of your course, when you
    # have exactly looped, or just shy of the loop, then save the path and shutdown
    # this process. Restart and the path will be loaded.
    ctr.set_button_down_trigger(cfg.SAVE_PATH_BTN, save_path)

    # Here's a trigger to erase a previously saved path. 

    ctr.set_button_down_trigger(cfg.ERASE_PATH_BTN, erase_path)

    # Here's a trigger to reset the origin. 

    ctr.set_button_down_trigger(cfg.RESET_ORIGIN_BTN, reset_origin)

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

    # Buttons to tune PID constants
    ctr.set_button_down_trigger("L2", dec_pid_d)
    ctr.set_button_down_trigger("R2", inc_pid_d)

    # #This web controller will create a web server. We aren't using any controls, just for visualization.

    web_ctr = LocalWebController(port=cfg.WEB_CONTROL_PORT,
                                 mode=cfg.WEB_INIT_MODE)

    V.add(web_ctr,
        inputs=['map/image'],
        outputs=['web/angle', 'web/throttle', 'web/mode', 'web/recording'],
        threaded=True)
    

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
    

    if not cfg.DONKEY_GYM:
        steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
        steering = PWMSteering(controller=steering_controller,
                                        left_pulse=cfg.STEERING_LEFT_PWM, 
                                        right_pulse=cfg.STEERING_RIGHT_PWM)
        
        throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
        throttle = PWMThrottle(controller=throttle_controller,
                                        max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                        zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                                        min_pulse=cfg.THROTTLE_REVERSE_PWM)

        V.add(steering, inputs=['angle'])
        V.add(throttle, inputs=['throttle'])

    # Print Joystick controls
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
        drive(cfg)