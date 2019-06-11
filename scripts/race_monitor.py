#!/usr/bin/env python3
"""
Scripts to help monitor rc race cars

Usage:
    race_monitor.py

"""
import os
from docopt import docopt

import donkeycar as dk
from donkeycar.parts.controller import LocalWebController, JoystickController
from donkeycar.parts.datastore import TubHandler, TubGroup

import numpy as np

def go(cfg):
    '''
    '''

    #Initialize car
    V = dk.vehicle.Vehicle()

    print("cfg.CAMERA_TYPE", cfg.CAMERA_TYPE)
    if cfg.CAMERA_TYPE == "PICAM":
        from donkeycar.parts.camera import PiCamera
        cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H)
    elif cfg.CAMERA_TYPE == "WEBCAM":
        from donkeycar.parts.camera import Webcam
        cam = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H)
    elif cfg.CAMERA_TYPE == "CVCAM":
        from donkeycar.parts.cv import CvCam
        cam = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H)
        
    V.add(cam, outputs=['cam/image_array'], threaded=True)
        
    if cfg.CAMERA_TYPE == "CVCAM":
        from donkeycar.parts.cv import CvImageView
        mon = CvImageView()
        V.add(mon, inputs=['cam/image_array'])

    ctr = None
    '''
    ctr = LocalWebController()
    
    V.add(ctr, 
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)
        '''

    inputs=['cam/image_array']
    types=['image_array']
   
    '''
    th = TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, outputs=["tub/num_records"])

    if type(ctr) is LocalWebController:
        print("You can now go to <your pi ip address>:8887 to drive your car.")
    elif type(ctr) is JoystickController:
        print("You can now move your joystick to drive your car.")
        #tell the controller about the tub        
        ctr.set_tub(tub)
        '''

    #run the vehicle for 20 seconds
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    go(cfg)
    