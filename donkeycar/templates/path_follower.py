#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car

Usage:
    path_follower.py (drive) [--log=INFO]
 

Options:
    -h --help          Show this screen.
    --js               Use physical joystick.
    -f --file=<file>   A text file containing paths to tub files, one per line. Option may be used more than once.
    --meta=<key:value> Key/Value strings describing describing a piece of meta data about this drive. Option may be used more than once.
"""
import os
import time
import logging

from docopt import docopt
import numpy as np

import donkeycar as dk
from donkeycar.parts.controller import LocalWebController, JoystickController
from donkeycar.parts.controller import PS3JoystickController, PS4JoystickController, NimbusController, XboxOneJoystickController
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.path import Path, PathPlot, CTE, PID_Pilot, PlotCircle, PImage, OriginOffset
from donkeycar.parts.transform import PIDController


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
    
    cont_class = PS3JoystickController

    if cfg.CONTROLLER_TYPE == "nimbus":
        cont_class = NimbusController
    
    ctr = cont_class(throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
                                steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
    
    ctr.set_deadzone(cfg.JOYSTICK_DEADZONE)

    V.add(ctr, 
          inputs=['null'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)

    if cfg.DONKEY_GYM:
        from donkeycar.parts.dgym import DonkeyGymEnv 
        gym_env = DonkeyGymEnv(cfg.DONKEY_SIM_PATH, env_name=cfg.DONKEY_GYM_ENV_NAME)
        threaded = True
        inputs = ['angle', 'throttle']
        V.add(gym_env, inputs=inputs, outputs=['cam/image_array', 'rs/pos'], threaded=threaded)

        class PosStream:
            def run(self, pos):
                #y is up, x is right, z is backwards/forwards
                logging.debug("pos %s" % str(pos))
                return pos[0], pos[2]

    else:
        from donkeycar.parts.realsense import RS_T265
        rs = RS_T265()
        V.add(rs, outputs=['rs/pos', 'rs/vel', 'rs/acc'], threaded=True)

        class PosStream:
            def run(self, pos):
                #y is up, x is right, z is backwards/forwards
                return pos.x, pos.z

    V.add(PosStream(), inputs=['rs/pos'], outputs=['pos/x', 'pos/y'])

    origin_reset = OriginOffset()
    V.add(origin_reset, inputs=['pos/x', 'pos/y'], outputs=['pos/x', 'pos/y'] )

    ctr.set_button_down_trigger(cfg.RESET_ORIGIN_BTN, origin_reset.init_to_last)

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




    path = Path(min_dist=cfg.PATH_MIN_DIST)
    V.add(path, inputs=['pos/x', 'pos/y'], outputs=['path'], run_condition='run_user')

    if os.path.exists(cfg.PATH_FILENAME):
        path.load(cfg.PATH_FILENAME)
        print("loaded path:", cfg.PATH_FILENAME)

    def save_path():
        path.save(cfg.PATH_FILENAME)
        print("saved path:", cfg.PATH_FILENAME)

    ctr.set_button_down_trigger(cfg.SAVE_PATH_BTN, save_path)

    img = PImage(clear_each_frame=True)
    V.add(img, outputs=['map/image'])

    plot = PathPlot(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET)
    V.add(plot, inputs=['map/image', 'path'], outputs=['map/image'])

    cte = CTE()
    V.add(cte, inputs=['path', 'pos/x', 'pos/y'], outputs=['cte/error'], run_condition='run_pilot')

    pid = PIDController(p=cfg.PID_P, i=cfg.PID_I, d=cfg.PID_D)
    pilot = PID_Pilot(pid, cfg.PID_THROTTLE)
    V.add(pilot, inputs=['cte/error'], outputs=['pilot/angle', 'pilot/throttle'], run_condition="run_pilot")

    loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET)
    V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'])


    #This web controller will create a web server
    web_ctr = LocalWebController()
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
