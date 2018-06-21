#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 17:30:28 2017

@author: wroscoe
"""




import base64
import random
import numpy as np
import socketio
import eventlet
import eventlet.wsgi
from PIL import Image
from flask import Flask
from io import BytesIO
import time


class FPSTimer(object):
    def __init__(self):
        self.t = time.time()
        self.iter = 0

    def reset(self):
        self.t = time.time()
        self.iter = 0

    def on_frame(self):
        self.iter += 1
        if self.iter == 100:
            e = time.time()
            print('fps', 100.0 / (e - self.t))
            self.t = time.time()
            self.iter = 0


class SteeringServer(object):
    """
    A SocketIO based Websocket server designed to integrate with
    the Donkey Sim Unity project. Check the donkey branch of
    https://github.com/tawnkramer/sdsandbox for source of simulator.
    Prebuilt simulators available:
    Windows: https://drive.google.com/file/d/0BxSsaxmEV-5YRC1ZWHZ4Y1dZTkE/view?usp=sharing
    """
    def __init__(self, _sio, kpart, top_speed=4.0, image_part=None, steering_scale=1.0):
        self.model = None
        self.timer = FPSTimer()
        self.sio = _sio
        # TODO: convert this flask app to a tornado app to minimize dependencies.
        self.app = Flask(__name__)
        self.kpart = kpart
        self.image_part = image_part
        self.steering_scale = steering_scale
        self.top_speed = top_speed

    def throttle_control(self, last_steering, last_throttle, speed, nn_throttle):
        """
        super basic throttle control, derive from this Server and override as needed
        """
        if speed < self.top_speed:
            return 0.3

        return 0.0

    def telemetry(self, sid, data):
        """
        Callback when we get new data from Unity simulator.
        We use it to process the image, do a forward inference,
        then send controls back to client.
        Takes sid (?) and data, a dictionary of json elements.
        """
        if data:
            # The current steering angle of the car
            last_steering = float(data["steering_angle"])

            # The current throttle of the car
            last_throttle = float(data["throttle"])

            # The current speed of the car
            speed = float(data["speed"])

            # The current image from the center camera of the car
            imgString = data["image"]

            # decode string based data into bytes, then to Image
            image = Image.open(BytesIO(base64.b64decode(imgString)))

            # then as numpy array
            image_array = np.asarray(image)

            # optional change to pre-preocess image before NN sees it
            if self.image_part is not None:
                image_array = self.image_part.run(image_array)

            # forward pass - inference
            steering, throttle = self.kpart.run(image_array)

            # filter throttle here, as our NN doesn't always do a greate job
            throttle = self.throttle_control(last_steering, last_throttle, speed, throttle)

            # simulator will scale our steering based on it's angle based input.
            # but we have an opportunity for more adjustment here.
            steering *= self.steering_scale

            # send command back to Unity simulator
            self.send_control(steering, throttle)

        else:
            # NOTE: DON'T EDIT THIS.
            self.sio.emit('manual', data={}, skip_sid=True)

        self.timer.on_frame()

    def connect(self, sid, environ):
        print("connect ", sid)
        self.timer.reset()
        self.send_control(0, 0)

    def send_control(self, steering_angle, throttle):
        self.sio.emit(
            "steer",
            data={
                'steering_angle': steering_angle.__str__(),
                'throttle': throttle.__str__()
            },
            skip_sid=True)

    def go(self, address):

        # wrap Flask application with engineio's middleware
        self.app = socketio.Middleware(self.sio, self.app)

        # deploy as an eventlet WSGI server
        try:
            eventlet.wsgi.server(eventlet.listen(address), self.app)

        except KeyboardInterrupt:
            # unless some hits Ctrl+C and then we get this interrupt
            print('stopping')


class MovingSquareTelemetry:
    """
    Generator of cordinates of a bouncing moving square for simulations.
    """
    def __init__(self, max_velocity=29,
                 x_min = 10, x_max=150,
                 y_min = 10, y_max=110):

        self.velocity = random.random() * max_velocity

        self.x_min, self.x_max = x_min, x_max
        self.y_min, self.y_max = y_min, y_max

        self.x_direction = random.random() * 2 - 1
        self.y_direction = random.random() * 2 - 1

        self.x = random.random() * x_max
        self.y = random.random() * y_max

        self.tel = self.x, self.y

    def run(self):
        #move
        self.x += self.x_direction * self.velocity
        self.y += self.y_direction * self.velocity

        #make square bounce off walls
        if self.y < self.y_min or self.y > self.y_max:
            self.y_direction *= -1
        if self.x < self.x_min or self.x > self.x_max:
            self.x_direction *= -1

        return int(self.x), int(self.y)

    def update(self):
        self.tel = self.run()

    def run_threaded(self):
        return self.tel


class SquareBoxCamera:
    """
    Fake camera that returns an image with a square box.

    This can be used to test if a learning algorithm can learn.
    """

    def __init__(self, resolution=(120,160), box_size=4, color=(255, 0, 0)):
        self.resolution = resolution
        self.box_size = box_size
        self.color = color


    def run(self, x,y, box_size=None, color=None):
        """
        Create an image of a square box at a given coordinates.
        """
        radius = int((box_size or self.box_size)/2)
        color = color or self.color
        frame = np.zeros(shape=self.resolution + (3,))
        frame[y - radius: y + radius,
              x - radius: x + radius,  :] = color
        return frame


