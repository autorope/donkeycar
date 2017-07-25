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

import donkey as dk


if hasattr(os, 'scandir'):
    from os import scandir
else:
    from scandir import scandir

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

        #use one session for all requests
        self.session = requests.Session()

    def update(self):
        '''
        Loop to run in separate thread the updates angle, throttle and
        drive mode.
        '''

        while True:
            #get latest value from server
            self.angle, self.throttle, self.mode = self.run()

    def run_threaded(self):
        '''
        Return the last state given from the remote server.
        '''
        #return last returned last remote response.
        return self.angle, self.throttle, self.mode

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

        return angle, throttle, drive_mode


class LocalWebController(tornado.web.Application):

    def __init__(self, mydonkey_path='~/mydonkey/'):
        '''
        Create and publish variables needed on many of
        the web handlers.
        '''

        print('Starting Donkey Server...')

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')

        self.mydonkey_path = os.path.expanduser(mydonkey_path)
        self.sessions_path = os.path.join(self.mydonkey_path, 'sessions')
        self.models_path = os.path.join(self.mydonkey_path, 'models')

        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False

        handlers = [
            (r"/drive", DriveAPI),
            (r"/video",VideoAPI),
            (r"/sessions/", SessionListView),
            (r"/sessions/?(?P<session_id>[^/]+)?/?(?P<page>[^/]+)?",
                SessionView),
            (r"/session_image/?(?P<session_id>[^/]+)?/?(?P<img_name>[^/]+)?",
                SessionImageView),
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

    def run_threaded(self, img_arr = None, rcin_angle = 0.0, rcin_throttle = 0.0):
        self.img_arr = img_arr

        if self.mode == 'user':
            self.angle = rcin_angle
            self.throttle = rcin_throttle

        print(self.angle)
        return self.angle, self.throttle, self.mode, self.recording

    def shutdown(self):
        # indicate that the thread should be stopped
        print('stopping LocalWebController')


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
                img = dk.utils.arr_to_binary(self.application.img_arr)

                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img))
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)

####################
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

        session_dirs = [f for f in scandir(self.application.sessions_path) if f.is_dir() ]
        data = {'session_dirs': sorted(session_dirs, key = lambda d: d.name, reverse = True)}
        self.render("templates/session_list.html", **data)



class SessionView(tornado.web.RequestHandler):

    def get(self, session_id, page):
        '''
        Shows all the images saved in the session.
        '''
        from operator import itemgetter

        sessions_path = self.application.sessions_path
        path = os.path.join(sessions_path, session_id)
        imgs = [dk.utils.merge_two_dicts({'name':f.name}, dk.sessions.parse_img_filepath(f.path)) for f in scandir(path) if f.is_file() and f.name[-3:] =='jpg' ]
        img_count = len(imgs)

        perpage = 500
        pages = math.ceil(img_count/perpage)
        if page is None:
            page = 1
        else:
            page = int(page)

        if page == 0:
            page = 1

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
                f = i.split('_')
                f = '_'.join(f[0:2]) + ".json"
                os.remove(os.path.join(path, f))
                print('%s removed' % f)

