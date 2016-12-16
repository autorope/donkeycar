import time
import os
import threading
from time import sleep
from io import BytesIO

import tornado.ioloop
import tornado.web
from tornado import gen

from PIL import Image


''' 
A Tornado Webserver that serves a simple web page that allows
a user to monitor and control the vehicle. 

This runs localy on the Raspberry Pi of the vehicle.
'''



class LocalWebController():
    ''' Wrapper to create common interface for angle and driving controls'''
    port = 8887
    angle=0
    speed=0
    drive_mode = 'manual'

    def __init__(self):
        
        print('Starting webserver at <ip_address>:%s' %self.port)
        t = threading.Thread(target=self.start)
        t.daemon = True #to close thread on Ctrl-c
        t.start()


    def start(self):

        app = tornado.web.Application([
            (r"/", IndexHandler),
            #Here we pass in self so the webserve can update angle and speed asynch
            (r"/velocity", VelocityHandler, dict(controller = self)),
            #(r"/mjpeg/([^/]*)", MJPEGHandler)
        ])

        app.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

   



class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")



class VelocityHandler(tornado.web.RequestHandler):
    def initialize(self, controller):
        #the parrent controller
         self.controller = controller

    def post(self):
        '''
        Receive post requests as user changes the angle
        and speed of the vehicle on a the controller webpage
        '''
        data = tornado.escape.json_decode(self.request.body)
        print(data)
        angle = data['angle']
        speed = data['speed']
        drive_mode = data['drive_mode']


        self.controller.drive_mode = drive_mode

        if angle is not "":
            self.controller.angle = int(data['angle'])
        else:
            self.controller.angle = 0

        if speed is not "":
            self.controller.speed = int(data['speed'])
        else:
            self.controller.speed = 0            


'''
REMOVING UNTIL THIS GOES INTO A BROADER CAR OBJECT
It doesn't make sense to call camera from the controller
'''
"""
class MJPEGHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, file):
        '''
        Show a video of the pictures captured by the vehicle.
        '''
        ioloop = tornado.ioloop.IOLoop.current()
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")

        self.served_image_timestamp = time.time()
        my_boundary = "--boundarydonotcross"
        while True:
            
            interval = .2
            if self.served_image_timestamp + interval < time.time():
                img = GLB.camera.capture_binary()
                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)

"""


