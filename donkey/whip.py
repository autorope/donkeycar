import time
import json
import io
import os

import numpy as np

import requests
import tornado.ioloop
import tornado.web

from PIL import Image


from utils import image as image_utils


class WhipClient():
    '''
    Class used by vehicle to send driving data and recieve predictions.
    '''
       
    
    def __init__(self, remote_url, session, model):

        self.record_url = remote_url + '/mycar/drive/'

        
        
    def post(self, img, angle, speed, milliseconds):
        '''
        Accepts: image and control attributes and saves 
        them to learn how to drive.'''

        #load features
        data = {
                'angle': angle,
                'speed': speed,
                'milliseconds': milliseconds
                }

        r = requests.post(self.record_url, 
                            files={'img': image_utils.img_to_binary(img), 
                                    'json': json.dumps(data)}) #hack to put json in file
        
        data = json.loads(r.text)
        angle = int(float(data['angle']))
        speed = int(float(data['speed']))
        print('drive client: %s' %r.text)

        return angle, speed





class WhipServer():
    '''
    Class used to create server that accepts driving data, records it, 
    runs a predictor and returns the predictions.
    '''
    
    def __init__(self, recorder, predictor):

        self.port = int(os.environ.get("PORT", 8886))
        self.recorder = recorder
        self.predictor = predictor

        vehicle_data = {'c_angle': 0, 'c_speed': 0, 'milliseconds': 0, 
                        'drive_mode':'manual'}
        self.vehicles = {'mycar':vehicle_data}

        pass
        
        
    def start(self):
        '''
        Start the webserver.
        '''

        #load features
        app = tornado.web.Application([
            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", VehicleHandler),

            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/control/",
                ControllerHandler,
                dict(vehicles = self.vehicles)
            ),
            #Here we pass in self so the webserve can update angle and speed asynch
            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/mjpeg/?(?P<file>[^/]*)?",
                CameraMJPEGHandler,
                dict(vehicles = self.vehicles)
            ),
            (r"/?(?P<vehicle_id>[A-Za-z0-9-]+)?/drive/", 
                DriveHandler, 
                dict(predictor=self.predictor, recorder=self.recorder, vehicles=self.vehicles)
            )       
            ])

        app.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

        return True



class VehicleHandler(tornado.web.RequestHandler):
    def get(self, vehicle_id):
        self.render("monitor.html")


class ControllerHandler(tornado.web.RequestHandler):
    def initialize(self, vehicles):
        #the parrent controller
         self.vehicles = vehicles

    def post(self, vehicle_id):
        '''
        Receive post requests as user changes the angle
        and speed of the vehicle on a the index webpage
        '''
        data = tornado.escape.json_decode(self.request.body)

        angle = data['angle']
        speed = data['speed']
        drive_mode = data['drive_mode']

        V = self.vehicles[vehicle_id]

        V['drive_mode'] = drive_mode

        if angle is not "":
            V['c_angle'] = int(data['angle'])
        else:
            V['c_angle'] = 0

        if speed is not "":
            V['c_speed'] = int(data['speed'])
        else:
            V['c_speed'] = 0    

        print(V)


class DriveHandler(tornado.web.RequestHandler):
    def initialize(self, recorder, predictor, vehicles):
        #the parrent controller
         self.predictor = predictor
         self.recorder = recorder
         self.vehicles = vehicles

    def post(self, vehicle_id):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and speed the car should be goin. 
        '''    
        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))

        #Hack to take json from a file
        #data = json.loads(self.request.files['json'][0]['body'].decode("utf-8") )

        arr = np.array(img)
        p_angle, p_speed = self.predictor.predict(arr)


        V = self.vehicles[vehicle_id]
        V['img'] = img
        V['p_angle'] = p_angle
        V['p_speed'] = p_speed

        self.recorder.record(img, 
                            V['c_angle'],
                            V['c_speed'], 
                            V['milliseconds'])



        if V['drive_mode'] == 'manual':
            angle, speed  = V['c_angle'], V['c_speed']
        else:
            angle, speed  = V['p_angle'], V['p_speed']

        print('%s: A: %s   S:%s' %(V['drive_mode'], angle, speed))

        self.write(json.dumps({'angle': str(angle), 'speed': str(speed)}))

    def get(self):
        print('DriveHandler get function')


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

