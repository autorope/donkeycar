import settings #call this first to set global vars

import tornado.ioloop
import tornado.web
import time
import os
from tornado import gen
from io import BytesIO
from PIL import Image
import threading
from time import sleep

''' 
CONFIG
'''

cam = settings.cam

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")



class VelocityHandler(tornado.web.RequestHandler):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        print(data)
        angle = data['angle']
        speed = data['speed']


        if angle is not "":
            settings.angle = int(data['angle'])
        else:
            settings.angle = 0

        if speed is not "":
            settings.speed = int(data['speed'])
        else:
            settings.speed = 0            



class MJPEGHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, file):
        ioloop = tornado.ioloop.IOLoop.current()
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")

        self.served_image_timestamp = time.time()
        my_boundary = "--boundarydonotcross"
        while True:
            
            interval = .2
            if self.served_image_timestamp + interval < time.time():
                img = cam.capture()
                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)


def start_webserver():
    #global angle
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


app = tornado.web.Application([
    (r"/", IndexHandler),
    (r"/velocity", VelocityHandler),
    (r"/mjpeg/([^/]*)", MJPEGHandler)
])


if __name__ == '__main__':

    angle=0
    speed=0

    t = threading.Thread(target=start_webserver)
    t.daemon = True #to close thread on Ctrl-c
    t.start()

    while True:
        sleep(1)
        print('angle: %s,  speed: %s' %(angle, speed))