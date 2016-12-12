import tornado.ioloop
import tornado.web
import time
import os
from tornado import gen
from io import BytesIO
from PIL import Image


''' 
CONFIG
'''
from camera import FakeCamera as Cam
#from camera import Camera as Cam


cam = Cam()

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class VelocityHandler(tornado.web.RequestHandler):
    def post(self):
        global angle
        global speed
        print(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        angle = data['angle']
        speed = data['speed']

class MJPEGHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, file):
        ioloop = tornado.ioloop.IOLoop.current()
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")

        self.served_image_timestamp = time.time()
        my_boundary = "--boundarydonotcross"
        while True:
            
            interval = .1
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



app = tornado.web.Application([
    (r"/", IndexHandler),
    (r"/velocity", VelocityHandler),
    (r"/mjpeg/([^/]*)", MJPEGHandler)
])


if __name__ == "__main__":
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()