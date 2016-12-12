

''' A simple tornado website to control the vehicle.'''


from tornado import websocket, web, ioloop
import threading
from time import sleep
import json

cl = []

class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)

    def on_close(self):
        if self in cl:
            cl.remove(self)

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        global angle
        self.finish()
        id = self.get_argument("id")
        value = self.get_argument("value")
        data = {"id": id, "value" : value}
        data = json.dumps(data)
        for c in cl:
            c.write_message(data)
        print(value)
        angle = value

    @web.asynchronous
    def post(self):
        pass

app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
])


def start_webserver():
    #global angle
    app.listen(8888)
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':

    angle=0
    speed=0

    t = threading.Thread(target=start_webserver)
    t.daemon = True #to close thread on Ctrl-c
    t.start()

    while True:
        sleep(1)
        print('angle: %s,  speed: %s' %(angle, speed))