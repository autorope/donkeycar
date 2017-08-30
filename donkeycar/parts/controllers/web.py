#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 24 20:10:44 2017

@author: wroscoe

remotes.py

The client and web server needed to control a car remotely. 
"""


import os
import json
import time

import requests

import tornado.ioloop
import tornado.web
import tornado.gen

from ... import utils


class RemoteWebServer():
    '''
    A controller that repeatedly polls a remote webserver and expects
    the response to be angle, throttle and drive mode. 
    '''
    
    def __init__(self, remote_url, connection_timeout=.25):

        self.control_url = remote_url
        self.time = 0.
        self.angle = 0.
        self.throttle = 0.
        self.mode = 'user'
        self.recording = False
        #use one session for all requests
        self.session = requests.Session()


        
    def update(self):
        '''
        Loop to run in separate thread the updates angle, throttle and 
        drive mode. 
        '''

        while True:
            #get latest value from server
            self.angle, self.throttle, self.mode, self.recording = self.run()


    def run_threaded(self):
        ''' 
        Return the last state given from the remote server.
        '''
        
        #return last returned last remote response.
        return self.angle, self.throttle, self.mode, self.recording

        
    def run(self):
        '''
        Posts current car sensor data to webserver and returns
        angle and throttle recommendations. 
        '''
        
        data = {}
        response = None
        while response == None:
            try:
                response = self.session.post(self.control_url, 
                                             files={'json': json.dumps(data)},
                                             timeout=0.25)
                
            except (requests.exceptions.ReadTimeout) as err:
                print("\n Request took too long. Retrying")
                #Lower throttle to prevent runaways.
                return self.angle, self.throttle * .8, None
                
            except (requests.ConnectionError) as err:
                #try to reconnect every 3 seconds
                print("\n Vehicle could not connect to server. Make sure you've " + 
                    "started your server and you're referencing the right port.")
                time.sleep(3)
            


        data = json.loads(response.text)
        angle = float(data['angle'])
        throttle = float(data['throttle'])
        drive_mode = str(data['drive_mode'])
        recording = bool(data['recording'])
        
        return angle, throttle, drive_mode, recording
    
    
class LocalWebController(tornado.web.Application):

    def __init__(self):
        ''' 
        Create and publish variables needed on many of 
        the web handlers.
        '''

        print('Starting Donkey Server...')

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')
        
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False

        handlers = [
            (r"/", tornado.web.RedirectHandler, dict(url="/drive")),
            (r"/drive", DriveAPI),
            (r"/video",VideoAPI),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": self.static_file_path}),
            ]

        settings = {'debug': True}

        super().__init__(handlers, **settings)

    def update(self, port=8887):
        ''' Start the tornado webserver. '''
        print(port)
        self.port = int(port)
        self.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()


    def run_threaded(self, img_arr=None):
        self.img_arr = img_arr
        return self.angle, self.throttle, self.mode, self.recording
        
    def run(self, img_arr=None):
        self.img_arr = img_arr
        return self.angle, self.throttle, self.mode, self.recording


class DriveAPI(tornado.web.RequestHandler):

    def get(self):
        data = {}
        self.render("templates/vehicle.html", **data)
    
    
    def post(self):
        '''
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        '''
        data = tornado.escape.json_decode(self.request.body)
        self.application.angle = data['angle']
        self.application.throttle = data['throttle']
        self.application.mode = data['drive_mode']
        self.application.recording = data['recording']


class VideoAPI(tornado.web.RequestHandler):
    '''
    Serves a MJPEG of the images posted from the vehicle. 
    '''
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):

        ioloop = tornado.ioloop.IOLoop.current()
        self.set_header("Content-type", "multipart/x-mixed-replace;boundary=--boundarydonotcross")

        self.served_image_timestamp = time.time()
        my_boundary = "--boundarydonotcross"
        while True:
            
            interval = .1
            if self.served_image_timestamp + interval < time.time():


                img = utils.arr_to_binary(self.application.img_arr)

                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img)) 
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)