"""
Classes needed to run a webserver so that the donkey can
be controlled remotely by the user or an auto pilot. 
"""

import time
import json
import io
import os
import copy
import math

import numpy as np

import requests
import tornado.ioloop
import tornado.web

from PIL import Image


import donkey as dk


class RemoteClient():
    '''
    Class used by a vehicle to send driving data and 
    recieve predictions from a remote webserver.
    '''
    
    def __init__(self, remote_url, vehicle_id='mycar'):

        self.control_url = remote_url + '/api/vehicles/control/' + vehicle_id + '/'
        self.last_milliseconds = 0
        
        
    def decide(self, img_arr, angle, throttle, milliseconds):
        '''
        Posts current car sensor data to webserver and returns
        angle and throttle recommendations. 
        '''

        #load features
        data = {
                'angle': angle,
                'throttle': throttle,
                'milliseconds': milliseconds
                }


        r = None

        while r == None:
            #Try connecting to server until connection is made.
            
            try:
                start = time.time()
                r = requests.post(self.control_url, 
                                files={'img': dk.utils.arr_to_binary(img_arr), 
                                       'json': json.dumps(data)}) #hack to put json in file 
                end = time.time()
                lag = end-start
            except (requests.ConnectionError) as err:
                print("Vehicle could not connect to server. Make sure you've " + 
                    "started your server and you're referencing the right port.")
                time.sleep(3)

        print(r.text)
        
        data = json.loads(r.text)
        
        angle = float(data['angle'])
        throttle = float(data['throttle'])
        
        print('vehicle <> server: request lag: %s' %lag)


        return angle, throttle




class DonkeyPilotApplication(tornado.web.Application):

    def __init__(self, data_path='~/donkey_data/'):
        ''' 
        Create and publish variables needed on many of 
        the web handlers.
        '''

        #create necessary directors if they don't exist
        dk.utils.create_donkey_data(data_path)

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

            (r"/sessions/?(?P<session_id>[^/]+)?/?(?P<page>[^/]+)?", 
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
        ''' Start the tornado webserver. '''
        print(port)
        self.port = int(port)
        self.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()


    def get_vehicle(self, vehicle_id):
        ''' Returns vehicle if it exists or creates a new one '''

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
        self.render("templates/home.html")


class VehicleListView(tornado.web.RequestHandler):
    def get(self):
        '''
        Serves a list of the vehicles posting requests to the server.
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
        self.render("templates/vehicle.html", **data)


class VehicleAPI(tornado.web.RequestHandler):


    def post(self, vehicle_id):
        '''
        Currently this only changes the pilot. 
        '''

        V = self.application.get_vehicle(vehicle_id)

        data = tornado.escape.json_decode(self.request.body)
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

        

        #set if vehicle is recording
        V['recording'] = data['recording']


        #update vehicle angel based on drive mode
        V['drive_mode'] = data['drive_mode']

        if angle is not "":
            V['user_angle'] = angle
        else:
            V['user_angle'] = 0

        if throttle is not "":
            V['user_throttle'] = throttle
        else:
            V['user_throttle'] = 0    

        print('Drive: %s: A: %s   T:%s' %(V['drive_mode'], angle, throttle))

class ControlAPI(tornado.web.RequestHandler):

    def post(self, vehicle_id):
        '''
        Receive post requests from a vehicle and returns 
        the angle and throttle the car should use. Depending on 
        the drive mode the values can come from the user or
        an autopilot.
        '''    

        V = self.application.get_vehicle(vehicle_id)

        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))
        img_arr = dk.utils.img_to_arr(img)


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

        print('Control: %s: A: %s   T:%s' %(V['drive_mode'], angle, throttle))
        

        #retun angel/throttle values to vehicle with json response
        self.write(json.dumps({'angle': str(angle), 'throttle': str(throttle)}))



class VideoAPI(tornado.web.RequestHandler):
    '''
    Serves a MJPEG of the images posted from the vehicle. 
    '''
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, vehicle_id):

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
        ''' Returns jpg images from a session folder '''

        sessions_path = self.application.sessions_path
        path = os.path.join(sessions_path, session_id, img_name)
        f = Image.open(path)
        o = io.BytesIO()
        f.save(o, format="JPEG")
        s = o.getvalue()

        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))   
        
        self.write(s)   



class SessionListView(tornado.web.RequestHandler):

    def get(self):
        '''  
        Serves a page showing a list of all the session folders.  
        TODO: Move this list creation to the session handler. 
        '''    

        session_dirs = [f for f in os.scandir(self.application.sessions_path) if f.is_dir() ]
        data = {'session_dirs': session_dirs}
        self.render("templates/session_list.html", **data)



class SessionView(tornado.web.RequestHandler):

    def get(self, session_id, page):
        '''
        Shows all the images saved in the session. 
        TODO: Add pagination.
        '''    
        from operator import itemgetter

        sessions_path = self.application.sessions_path
        path = os.path.join(sessions_path, session_id)
        imgs = [dk.utils.merge_two_dicts({'name':f.name}, dk.sessions.parse_img_filepath(f.path)) for f in os.scandir(path) if f.is_file() ]
        img_count = len(imgs)

        perpage = 1000
        pages = math.ceil(img_count/perpage)
        if page is None: 
            page = 1
        else:
            page = int(page)
        end = page * perpage
        start = end - perpage
        end = min(end, img_count)


        sorted_imgs = sorted(imgs, key=itemgetter('name')) 
        page_list = [p+1 for p in range(pages)]
        session = {'name':session_id, 'imgs': sorted_imgs[start:end]}
        data = {'session': session, 'page_list': page_list, 'this_page':page}
        self.render("templates/session.html", **data)

    def post(self, session_id, page):
        ''' 
        Deletes selected images 
        TODO: move this to an api cal. Page is not needed.
        '''
        
        data = tornado.escape.json_decode(self.request.body)

        if data['action'] == 'delete_images':
            sessions_path = self.application.sessions_path
            path = os.path.join(sessions_path, session_id)

            for i in data['imgs']:
                os.remove(os.path.join(path, i))
                print('%s removed' %i)







