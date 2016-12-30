import numpy as np
import time
import threading 
from .utils import image_utils
from .actuators import BaseSteeringActuator, BaseThrottleActuator


import tornado


class BaseVehicle:
    def __init__(self):

        self.drive_loop_delay = .2

        self.camera = None
        self.steering_actuator = None
        self.throttle_actuator = None
        self.pilot = None


    def start(self):

        start_time = time.time()
        angle = 0
        throttle = 0

        #drive loop
        while True:
            now = time.time()
            milliseconds = int( (now - start_time) * 1000)

            #get PIL image from camera
            img = self.camera.capture_img()

            angle, throttle = self.pilot.decide( img,
                                                 angle, 
                                                 throttle,
                                                 milliseconds)

            self.steering_actuator.update(angle)
            self.throttle_actuator.update(throttle)

            #print current car state
            print('angle: %s   throttle: %s' %(angle, throttle) )           
            time.sleep(self.drive_loop_delay)
