#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car

Usage:
    manage.py (drive)


Options:
    -h --help          Show this screen.    
"""
import os
import time

from docopt import docopt
import numpy as np

import donkeycar as dk
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.camera import PiCamera


class MyCVController:
    '''
    CV based controller
    '''

    def run(self, cam_img):

        #do image processing here. output variables steering and throttle to control vehicle.

        steering = 0.0 # from zero to one
        throttle = 0.2 # from -1 to 1
        recording = False # Set to true if desired to save camera frames

        return steering, throttle, recording



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

    #Camera
    cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
    V.add(cam, outputs=['cam/image_array'], threaded=True)
        
    #Controller
    V.add(MyCVController(), 
          inputs=['cam/image_array'],
          outputs=['steering', 'throttle', 'recording'])

       
    #Sombrero
    if cfg.HAVE_SOMBRERO:
        from donkeycar.parts.sombrero import Sombrero
        s = Sombrero()

        
    #Drive train setup

    from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle

    steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
    steering = PWMSteering(controller=steering_controller,
                                    left_pulse=cfg.STEERING_LEFT_PWM, 
                                    right_pulse=cfg.STEERING_RIGHT_PWM)
    
    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
    throttle = PWMThrottle(controller=throttle_controller,
                                    max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                    zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                                    min_pulse=cfg.THROTTLE_REVERSE_PWM)

    V.add(steering, inputs=['steering'])
    V.add(throttle, inputs=['throttle'])
    
    #add tub to save data

    inputs=['cam/image_array',
            'steering', 'throttle']

    types=['image_array',
           'float', 'float']

    th = TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, outputs=["tub/num_records"], run_condition='recording')

    #run the vehicle
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    
    if args['drive']:
        drive(cfg)
    
