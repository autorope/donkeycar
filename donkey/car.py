import settings

import numpy as np
import time
import threading 
from utils import image as image_utils

from donkey.vehicles import BaseVehicle


import tornado


class Car:
    def __init__(self, 
                vehicle_id='mycar',
                remote_url=None,
                fake_camera_img_dir=None):

        self.remote_url = remote_url
        self.vehicle_id = vehicle_id
        
        self.drive_loop_delay = settings.DRIVE_LOOP_DELAY

        if fake_camera_img_dir is None:
            self.camera = settings.camera(resolution=settings.CAMERA_RESOLUTION)
        else:
            self.camera = settings.camera(img_dir=fake_camera_img_dir)

        self.vehicle = BaseVehicle()
        

        self.drive_client = settings.drive_client(self.remote_url,
                                                  self.vehicle_id)



    def start(self):

        start_time = time.time()
        angle = 0
        speed = 0

        while True:
            now = time.time()
            milliseconds = int( (now - start_time) * 1000)

            #get PIL image from camera
            img = self.camera.capture_img()

            angle, speed = self.drive_client.post( img,
                                                    angle, 
                                                    speed,
                                                    milliseconds)

            self.vehicle.update(angle, speed)

            #print current car state
            print('>: %s   S: %s' %(angle, speed) )           
            time.sleep(self.drive_loop_delay)
