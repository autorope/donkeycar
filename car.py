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
                session=None, 
                model=None, 
                remote_url=None,
                fake_camera_img_dir=None):
        
        self.monitor_port = 8887

        self.session=session
        self.model=model
        self.remote_url = remote_url
        
        if fake_camera_img_dir is None:
            self.camera = settings.camera(resolution=settings.CAMERA_RESOLUTION)
        else:
            self.camera = settings.camera(img_dir=fake_camera_img_dir)

        self.controller = settings.controller()
        self.vehicle = settings.vehicle()

        self.recorder = settings.recorder(self.session)
        


        if remote_url is not None:
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

        while True:
            now = time.time()
            milliseconds = int( (now - start_time) * 1000)

            #get PIL image from camera
            img = self.camera.capture_img()

            #read values from controller
            c_angle = self.controller.angle
            c_speed = self.controller.speed
            drive_mode = self.controller.drive_mode


            if self.remote_url is None:
                #when no remote, use two functions to record and predict
                self.recorder.record(img, 
                                    c_angle,
                                    c_speed, 
                                    milliseconds)

                if self.predictor is not None:
                    #send image and data to predictor to get estimates
                    #arr = image_utils.img_to_greyarr(img)
                    arr = np.array(img)
                    p_angle, p_speed = self.predictor.predict(arr)
                
                else: 
                    p_angle, p_speed = 0, 0


            else:
                #when using a remote connection combine the record adn predic functions 
                #into one call. 
                angle, speed = self.drive_client.post( img,
                                                            c_angle, 
                                                            c_speed,
                                                            milliseconds)



            self.vehicle.update(angle, speed)


            #print current car state
            print('>: %s   S: %s' %(angle, speed) )           
            time.sleep(settings.DRIVE_LOOP_DELAY)



    def start_web_monitor(self):

        app = tornado.web.Application([
            (r"/", IndexHandler),
            #Here we pass in self so the webserve can update angle and speed asynch
            (r"/velocity", ControllerHandler, dict(controller = self.controller)),
            (r"/mjpeg/([^/]*)", CameraMJPEGHandler, dict(camera = self.camera))
        ])

        app.listen(self.monitor_port)
        tornado.ioloop.IOLoop.instance().start()
