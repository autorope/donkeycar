import settings
import time
import threading 
from utils import image as image_utils

from donkey.monitor import (ControllerHandler, 
                            IndexHandler,
                            CameraMJPEGHandler)


import tornado


class Car:
    def __init__(self, session=None, model=None, remote_url=None):
        
        self.monitor_port = 8887

        self.session=session
        self.model=model
        self.remote_url = remote_url

        self.camera = settings.camera()
        self.controller = settings.controller()
        self.vehicle = settings.vehicle()
        self.recorder = settings.recorder(self.session)
        self.predictor = settings.predictor()
        if model is not None:
            self.predictor.load(self.model)
        else:
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
                #record and predict locally
                self.recorder.record(img, 
                                    c_angle,
                                    c_speed, 
                                    milliseconds)

                #send image and data to predictor to get estimates
                arr = image_utils.img_to_greyarr(img)
                p_angle, p_speed = self.predictor.predict(arr)

            else:
                p_angle, p_speed = self.remote_driver(remote_url,
                                                     img,
                                                     c_angle, 
                                                     c_speed,
                                                     milliseconds)



            if self.controller.drive_mode == 'manual':
                #update vehicle with given velocity vars (not working)
                self.vehicle.update(c_angle, c_speed)
            else:
                self.vehicle.update(p_angle, p_speed)



            #print current car state
            print('A/P: >(%s, %s)  speed(%s/%s)  drive_mode: %s' %(self.controller.angle, 
                                    p_angle, 
                                    self.controller.speed,
                                    p_speed,
                                    self.controller.drive_mode))

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