"""
Classes used to communicate between vehicle and server. 
"""

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


import donkey as dk


class RemoteClient():
    '''
    Class used by vehicle to send driving data and recieve predictions.
    '''
    
    def __init__(self, remote_url, vehicle_id='mycar'):

        self.record_url = remote_url + '/vehicle/' + vehicle_id + '/'
        
        
    def decide(self, img_arr, angle, throttle, milliseconds):
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
                            files={'img': dk.utils.arr_to_binary(img_arr), 
                                   'json': json.dumps(data)}) #hack to put json in file
        
        data = json.loads(r.text)
        angle = int(float(data['angle']))
        throttle = int(float(data['throttle']))
        print('remote client: %s' %r.text)

        return angle, throttle




class DonkeyPilotApplication(tornado.web.Application):

    def __init__(self, data_path='~/donkey_data/'):

        self.vehicles = {}

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')

        self.data_path = os.path.expanduser(data_path)
        self.sessions_path = os.path.join(self.data_path, 'sessions')
        self.models_path = os.path.join(self.data_path, 'models')


        handlers = [

            #temporary redirect until vehicles is not a singleton
            (r"/", HomeHandler),

            (r"/drive/", ChooseVehicleHandler),

            (r"/drive/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", DriveHandler),

            (r"/drive/?(?P<vehicle_id>[A-Za-z0-9-]+)?/mjpeg/?(?P<file>[^/]*)?",
                CameraMJPEGHandler
            ),

            (r"/vehicle/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", VehicleHandler),

            (r"/sessions/", SessionListHandler),

            (r"/sessions/?(?P<session_id>[^/]+)?/", SessionViewHandler),

            (r"/session_image/?(?P<session_id>[^/]+)?/?(?P<img_name>[^/]+)?", 
                SessionImageHandler
            ),


            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": self.static_file_path}),

            ]

        settings = {'debug': True}

        super().__init__(handlers, **settings)

    def start(self, port=8887):
        print(port)
        self.port = int(port)
        self.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()


    def get_vehicle(self, vehicle_id):
        if vehicle_id not in self.vehicles:
            sh = dk.sessions.SessionHandler(self.sessions_path)
            self.vehicles[vehicle_id] = dict({
                        'user_angle': 0, 
                        'user_throttle': 0,  
                        'drive_mode':'user', 
                        'milliseconds': 0,
                        'recording': False,
                        'pilot': dk.pilots.BasePilot(),
                        'session': sh.new()})

        return self.vehicles[vehicle_id]


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        '''
        Serves home page.
        ''' 
        self.render("templates/home.html")


class ChooseVehicleHandler(tornado.web.RequestHandler):
    def get(self):
        '''
        Serves home page.
        ''' 
        data = {'vehicles':self.application.vehicles}

        self.render("templates/choose_vehicle.html", **data)


class SessionImageHandler(tornado.web.RequestHandler):
    def get(self, session_id, img_name):

        print('SessionImageHandler')

        sessions_path = self.application.sessions_path
        path = os.path.join(sessions_path, session_id, img_name)
        f = Image.open(path)
        o = io.BytesIO()
        f.save(o, format="JPEG")
        s = o.getvalue()
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))   

        print('writing image')
        self.write(s)   



class SessionListHandler(tornado.web.RequestHandler):

    def get(self):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    

        session_dirs = [f for f in os.scandir(self.application.sessions_path) if f.is_dir() ]
        data = {'session_dirs': session_dirs}
        self.render("templates/session_list.html", **data)



class SessionViewHandler(tornado.web.RequestHandler):

    def get(self, session_id):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    
        from operator import itemgetter

        
        sessions_path = self.application.sessions_path
        path = os.path.join(sessions_path, session_id)
        imgs = [dk.utils.merge_two_dicts({'name':f.name}, dk.sessions.parse_img_filepath(f.path)) for f in os.scandir(path) if f.is_file() ]

        sorted_imgs = sorted(imgs, key=itemgetter('name')) 
        session = {'name':session_id, 'imgs': sorted_imgs[:100]}
        data = {'session': session}
        self.render("templates/session_view.html", **data)

    def post(self, session_id):
        data = tornado.escape.json_decode(self.request.body)

        if data['action'] == 'delete_images':
            sessions_path = self.application.sessions_path
            path = os.path.join(sessions_path, session_id)

            for i in data['imgs']:
                os.remove(os.path.join(path, i))
                print('%s removed' %i)



class DriveHandler(tornado.web.RequestHandler):
    def get(self, vehicle_id):
        '''
        Serves page for users to control the vehicle.
        ''' 
        V = self.application.get_vehicle(vehicle_id)
        self.render("templates/monitor.html")


    def post(self, vehicle_id):
        '''
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        '''
        data = tornado.escape.json_decode(self.request.body)

        angle = data['angle']
        throttle = data['throttle']

        V = self.application.get_vehicle(vehicle_id)

        #Set recording mode
        if data['recording'] == 'true':
            V['recording'] = True
        else:
            V['recording'] = False


        #update vehicle angel based on drive mode
        V['drive_mode'] = data['drive_mode']

        if angle is not "":
            V['user_angle'] = int(angle)
        else:
            V['user_angle'] = 0

        if throttle is not "":
            V['user_throttle'] = int(throttle)
        else:
            V['user_throttle'] = 0    

        print(V)



class VehicleHandler(tornado.web.RequestHandler):

    def post(self, vehicle_id):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    
        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))
        img_arr = dk.utils.img_to_arr(img)

        #Hack to take json from a file
        #data = json.loads(self.request.files['json'][0]['body'].decode("utf-8") )
        
        V = self.application.vehicles[vehicle_id]

        #Get angle/throttle from pilot loaded by the server.
        pilot_angle, pilot_throttle = V['pilot'].decide(img)
        
        V['img'] = img
        V['pilot_angle'] = pilot_angle
        V['pilot_throttle'] = pilot_throttle


        if V['recording'] == True:
            #save image with encoded angle/throttle values
            V['session'].put(img, 
                             angle=V['user_angle'],
                             throttle=V['user_throttle'], 
                             milliseconds=V['milliseconds'])

        #depending on the drive mode, return user or pilot values
        if V['drive_mode'] == 'user':
            angle, throttle  = V['user_angle'], V['user_throttle']
        elif V['drive_mode'] == 'auto_angle':
            angle, throttle  = V['pilot_angle'], V['user_throttle']
        else:
            angle, throttle  = V['pilot_angle'], V['pilot_throttle']

        print('%s: A: %s   T:%s' %(V['drive_mode'], angle, throttle))

        #retun angel/throttle values to vehicle with json response
        self.write(json.dumps({'angle': str(angle), 'throttle': str(throttle)}))



class CameraMJPEGHandler(tornado.web.RequestHandler):

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


                img = self.application.vehicles[vehicle_id]['img']
                img = dk.utils.img_to_binary(img)

                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)

