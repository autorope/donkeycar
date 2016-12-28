import settings

import numpy as np


import time
import threading 
from utils import image as image_utils

from donkey.monitor import (ControllerHandler, 
                            IndexHandler,
                            CameraMJPEGHandler)


import tornado


class Car:
    def __init__(self, 
                vehicle_id='mycar',
                remote_url=None,
                fake_camera_img_dir=None):

        self.remote_url = remote_url
        self.vehicle_id = vehicle_id
        
        if fake_camera_img_dir is None:
            self.camera = settings.camera(resolution=settings.CAMERA_RESOLUTION)
        else:
            self.camera = settings.camera(img_dir=fake_camera_img_dir)

        self.controller = settings.controller()
        self.vehicle = settings.vehicle()
        

        self.drive_client = settings.drive_client(self.remote_url, 
                                              self.session,
                                              self.model)


        if model is not None:
            self.predictor = settings.predictor()
            self.predictor.load(self.model)
        else:
            self.predictor = None
            print("No model specified. Autodrive will not work.")



        print('Starting webserver at <ip_address>:%s' %self.monitor_port)
        t = threading.Thread(target=self.start_web_monitor)
        t.daemon = True #to close thread on Ctrl-c
        t.start()



    def drive_loop(self):

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






            #print current car state
            print('A/P: >(%s, %s)  speed(%s/%s)  drive_mode: %s' %(self.controller.angle, 
                                    p_angle, 
                                    self.controller.speed,
                                    p_speed,
                                    self.controller.drive_mode))

            
            time.sleep(settings.DRIVE_LOOP_DELAY)
