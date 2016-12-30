import time
import json
import io
import os
import copy

import numpy as np

import requests
import tornado.ioloop
import tornado.web

from PIL import Image


from .utils import image_utils


class RemoteClient():
    '''
    Class used by vehicle to send driving data and recieve predictions.
    '''
    
    def __init__(self, remote_url, vehicle_id='mycar'):

        self.record_url = remote_url + '/' + vehicle_id + '/drive/'
        
        
    def decide(self, img, angle, throttle, milliseconds):
        '''
        Accepts: image and control attributes and saves 
        them to learn how to drive.'''

        #load features
        data = {
                'angle': angle,
                'throttle': throttle,
                'milliseconds': milliseconds
                }

        r = requests.post(self.record_url, 
                            files={'img': image_utils.img_to_binary(img), 
                                   'json': json.dumps(data)}) #hack to put json in file
        
        data = json.loads(r.text)
        angle = int(float(data['angle']))
        throttle = int(float(data['throttle']))
        print('remote client: %s' %r.text)

        return angle, throttle





class RemoteServer():
    '''
    Class used to create server that accepts driving data, records it, 
    runs a predictor and returns the predictions.
    '''
    
    def __init__(self, recorder, pilot):

        self.port = int(os.environ.get("PORT", 8887))
        self.recorder = recorder
        self.pilot = pilot

        vehicle_data = {'user_angle': 0, 
                        'user_throttle': 0,  
                        'drive_mode':'user', 
                        'milliseconds': 0,}


        self.vehicles = {'mycar':vehicle_data}

        
    def start(self):
        '''
        Start the webserver.
        '''

        #load features
        app = tornado.web.Application([

            #temporary redirect until vehicles is not a singleton
            (r"/", tornado.web.RedirectHandler,
                dict(url="/mycar/")),

            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", VehicleHandler),

            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/control/",
                ControllerHandler,
                dict(vehicles = self.vehicles)
            ),
            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/mjpeg/?(?P<file>[^/]*)?",
                CameraMJPEGHandler,
                dict(vehicles = self.vehicles)
            ),
            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/drive/", 
                DriveHandler, 
                dict(pilot=self.pilot, recorder=self.recorder, vehicles=self.vehicles)
            )       
            ])

        app.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

        return True



class VehicleHandler(tornado.web.RequestHandler):
    def get(self, vehicle_id):
        self.render("templates/monitor.html")


class ControllerHandler(tornado.web.RequestHandler):

    def initialize(self, vehicles):
         self.vehicles = vehicles

    def post(self, vehicle_id):
        '''
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        '''
        data = tornado.escape.json_decode(self.request.body)

        angle = data['angle']
        throttle = data['throttle']
        drive_mode = data['drive_mode']

        V = self.vehicles[vehicle_id]

        V['drive_mode'] = drive_mode

        if angle is not "":
            V['user_angle'] = int(angle)
        else:
            V['user_angle'] = 0

        if throttle is not "":
            V['user_throttle'] = int(throttle)
        else:
            V['user_throttle'] = 0    

        print(V)


class DriveHandler(tornado.web.RequestHandler):
    def initialize(self, recorder, pilot, vehicles):
        #the parrent controller
         self.pilot = pilot
         self.recorder = recorder
         self.vehicles = vehicles

    def post(self, vehicle_id):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    
        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))

        #Hack to take json from a file
        #data = json.loads(self.request.files['json'][0]['body'].decode("utf-8") )

        arr = np.array(img)
        pilot_angle, pilot_throttle = self.pilot.decide(arr)


        V = self.vehicles[vehicle_id]
        V['img'] = img
        V['pilot_angle'] = pilot_angle
        V['pilot_throttle'] = pilot_throttle

        self.recorder.record(img, 
                            V['user_angle'],
                            V['user_throttle'], 
                            V['milliseconds'])

        if V['drive_mode'] == 'user':
            angle, throttle  = V['user_angle'], V['user_throttle']
        else:
            angle, throttle  = V['pilot_angle'], V['pilot_throttle']

        print('%s: A: %s   T:%s' %(V['drive_mode'], angle, throttle))
        self.write(json.dumps({'angle': str(angle), 'throttle': str(throttle)}))



class CameraMJPEGHandler(tornado.web.RequestHandler):
    def initialize(self, vehicles):
         self.vehicles = vehicles

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, vehicle_id, file):
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


                img = self.vehicles[vehicle_id]['img']
                img = image_utils.img_to_binary(img)

                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)

