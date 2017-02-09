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

        self.record_url = remote_url + '/api/vehicles/control/' + vehicle_id + '/'
        
        
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


        r = None

        while r == None:

            try:
                r = requests.post(self.record_url, 
                                files={'img': dk.utils.arr_to_binary(img_arr), 
                                       'json': json.dumps(data)}) #hack to put json in file 
            except (requests.ConnectionError) as err:
                print("Vehicle could not connect to server. Make sure you've " + 
                    "started your server and you're referencing the right port.")
                time.sleep(3)


        
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

        ph = dk.pilots.PilotHandler(self.models_path)
        self.pilots = ph.default_pilots()


        handlers = [

            #temporary redirect until vehicles is not a singleton
            (r"/", HomeView),

            (r"/vehicles/", VehicleListView),

            (r"/vehicles/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", 
                VehicleView),


            (r"/api/vehicles/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", 
                VehicleAPI),


            (r"/api/vehicles/drive/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", 
                DriveAPI),

            (r"/api/vehicles/video/?(?P<vehicle_id>[A-Za-z0-9-]+)?",
                VideoAPI
            ),

            (r"/api/vehicles/control/?(?P<vehicle_id>[A-Za-z0-9-]+)?/", 
                ControlAPI),


            (r"/sessions/", SessionListView),

            (r"/sessions/?(?P<session_id>[^/]+)?/", 
                SessionView),

            (r"/session_image/?(?P<session_id>[^/]+)?/?(?P<img_name>[^/]+)?", 
                SessionImageView
            ),


            (r"/pilots/", PilotListView),



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
            print('new vehicle')
            sh = dk.sessions.SessionHandler(self.sessions_path)
            self.vehicles[vehicle_id] = dict({
                        'id': vehicle_id, 
                        'user_angle': 0, 
                        'user_throttle': 0,  
                        'drive_mode':'user', 
                        'milliseconds': 0,
                        'recording': False,
                        'pilot': dk.pilots.BasePilot(),
                        'session': sh.new()})

        #eprint(self.vehicles)
        return self.vehicles[vehicle_id]


#####################
#                   #
#      vehicles     #
#                   #
#####################


class HomeView(tornado.web.RequestHandler):
    def get(self):
        '''
        Serves home page.
        ''' 
        self.render("templates/home.html")


class VehicleListView(tornado.web.RequestHandler):
    def get(self):
        '''
        Serves home page.
        ''' 
        data = {'vehicles':self.application.vehicles}

        self.render("templates/vehicle_list.html", **data)


class VehicleView(tornado.web.RequestHandler):
    def get(self, vehicle_id):
        '''
        Serves page for users to control the vehicle.
        ''' 


        V = self.application.get_vehicle(vehicle_id)
        pilots = self.application.pilots
        data = {'vehicle': V, 'pilots': pilots}
        print(data)
        self.render("templates/vehicle.html", **data)


class VehicleAPI(tornado.web.RequestHandler):

    def post(self, vehicle_id):
        '''
        Currently this only changes the pilot. 
        '''

        V = self.application.get_vehicle(vehicle_id)

        data = tornado.escape.json_decode(self.request.body)
        print(data)
        pilot = next(filter(lambda p: p.name == data['pilot'], self.application.pilots))
        V['pilot'] = pilot.load()



class DriveAPI(tornado.web.RequestHandler):

    def post(self, vehicle_id):
        '''
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        '''

        V = self.application.get_vehicle(vehicle_id)

        data = tornado.escape.json_decode(self.request.body)

        angle = data['angle']
        throttle = data['throttle']

        

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


class ControlAPI(tornado.web.RequestHandler):

    def post(self, vehicle_id):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    

        V = self.application.get_vehicle(vehicle_id)

        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))
        img_arr = dk.utils.img_to_arr(img)

        #Hack to take json from a file
        #data = json.loads(self.request.files['json'][0]['body'].decode("utf-8") )
        

        #Get angle/throttle from pilot loaded by the server.
        pilot_angle, pilot_throttle = V['pilot'].decide(img_arr)
        
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



class VideoAPI(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, vehicle_id):
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


#####################
#                   #
#      pilots       #
#                   #
#####################


class PilotListView(tornado.web.RequestHandler):
    def get(self):
        '''
        Render a list of pilots.
        '''
        ph = dk.pilots.PilotHandler(self.application.models_path)
        pilots = ph.default_pilots()
        data = {'pilots': pilots}
        self.render("templates/pilots_list.html", **data)




#####################
#                   #
#     sessions      #
#                   #
#####################



class SessionImageView(tornado.web.RequestHandler):
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



class SessionListView(tornado.web.RequestHandler):

    def get(self):
        '''
        Receive post requests from vehicle with camera image. 
        Return the angle and throttle the car should be goin. 
        '''    

        session_dirs = [f for f in os.scandir(self.application.sessions_path) if f.is_dir() ]
        data = {'session_dirs': session_dirs}
        self.render("templates/session_list.html", **data)



class SessionView(tornado.web.RequestHandler):

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







