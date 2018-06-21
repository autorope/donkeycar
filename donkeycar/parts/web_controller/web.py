#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 24 20:10:44 2017

@author: wroscoe

remotes.py

The client and web server needed to control a car remotely.
"""

import random


import os
import time

import tornado
import tornado.ioloop
import tornado.web
import tornado.gen

from donkeycar import util


class LocalWebController(tornado.web.Application):
    port = 8887
    def __init__(self, use_chaos=False):
        """
        Create and publish variables needed on many of
        the web handlers.
        """
        print('Starting Donkey Server...')

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.static_file_path = os.path.join(this_dir, 'templates', 'static')

        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False
        self.ip_address = util.web.get_ip_address()
        self.access_url = 'http://{}:{}'.format(self.ip_address, self.port)

        self.chaos_on = False
        self.chaos_counter = 0
        self.chaos_frequency = 1000 #frames
        self.chaos_duration = 10

        if use_chaos:
            self.run_threaded = self.run_chaos
        else:
            self.run_threaded = self._run_threaded

        handlers = [
            (r"/", tornado.web.RedirectHandler, dict(url="/drive")),
            (r"/drive", DriveAPI),
            (r"/video", VideoAPI),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": self.static_file_path}),
        ]

        settings = {'debug': True}
        super().__init__(handlers, **settings)

    def run_chaos(self, img_arr=None):
        """
        Run function where steering is made random to add corrective
        """
        self.img_arr = img_arr
        if self.chaos_counter == self.chaos_frequency:
            self.chaos_on = True
            random_steering = random.random()
        elif self.chaos_counter == self.chaos_duration:
            self.chaos_on = False

        if self.chaos_on:
            return random_steering, self.throttle, self.mode, False
        else:
            return self.angle, self.throttle, self.mode, self.recording

    def say_hello(self):
        """
        Print friendly message to user
        """
        print("You can now go to {} to drive your car.".format(self.access_url))

    def update(self):
        """ Start the tornado web server. """
        self.port = int(self.port)
        self.listen(self.port)
        instance = tornado.ioloop.IOLoop.instance()
        instance.add_callback(self.say_hello)
        instance.start()

    def _run_threaded(self, img_arr=None):
        self.img_arr = img_arr
        return self.angle, self.throttle, self.mode, self.recording

    def run(self, img_arr=None):
        return self.run_threaded(img_arr)


class DriveAPI(tornado.web.RequestHandler):
    def get(self):
        data = {}
        self.render("templates/vehicle.html", **data)

    def post(self):
        """
        Receive post requests as user changes the angle
        and throttle of the vehicle on a the index webpage
        """
        data = tornado.escape.json_decode(self.request.body)
        self.application.angle = data['angle']
        self.application.throttle = data['throttle']
        self.application.mode = data['drive_mode']
        self.application.recording = data['recording']


class VideoAPI(tornado.web.RequestHandler):
    """
    Serves a MJPEG of the images posted from the vehicle.
    """

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

                img = util.img.arr_to_binary(self.application.img_arr)

                self.write(my_boundary)
                self.write("Content-type: image/jpeg\r\n")
                self.write("Content-length: %s\r\n\r\n" % len(img))
                self.write(img)
                self.served_image_timestamp = time.time()
                yield tornado.gen.Task(self.flush)
            else:
                yield tornado.gen.Task(ioloop.add_timeout, ioloop.time() + interval)
