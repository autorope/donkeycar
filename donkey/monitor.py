import time


import tornado.ioloop
import tornado.web
from tornado import gen

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")



class ControllerHandler(tornado.web.RequestHandler):
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



class CameraMJPEGHandler(tornado.web.RequestHandler):
    def initialize(self, camera):
         self.camera = camera


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
                img = self.camera.capture_binary()
                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)




