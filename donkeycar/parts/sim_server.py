'''
A SocketIO based Websocket server designed to integrate with 
the Donkey Sim Unity project. Check the donkey branch of
https://github.com/tawnkramer/sdsandbox for source of simulator.
Prebuilt simulators available:
Windows: https://drive.google.com/file/d/0BxSsaxmEV-5YRC1ZWHZ4Y1dZTkE/view?usp=sharing
'''
import shutil
import base64

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
    def __init__(self, _sio, kpart, top_speed=4.0, image_part=None, steering_scale=1.0):
        self.model = None
        self.timer = FPSTimer()
        self.sio = _sio
        self.app = Flask(__name__)
        self.kpart = kpart
        self.image_part = image_part
        self.steering_scale = steering_scale
        self.top_speed = top_speed

    def throttle_control(self, last_steering, last_throttle, speed, nn_throttle):
        '''
        super basic throttle control, derive from this Server and override as needed
        '''
        if speed < self.top_speed:
            return 0.3
        
        return 0.0

    def telemetry(self, sid, data):
        '''
        Callback when we get new data from Unity simulator.
        We use it to process the image, do a forward inference,
        then send controls back to client.
        Takes sid (?) and data, a dictionary of json elements.
        '''
        if data:
            # The current steering angle of the car
            last_steering = float(data["steering_angle"])

            # The current throttle of the car
            last_throttle = float(data["throttle"])

            # The current speed of the car
            speed = float(data["speed"])

            # The current image from the center camera of the car
            imgString = data["image"]

            #decode string based data into bytes, then to Image
            image = Image.open(BytesIO(base64.b64decode(imgString)))

            #then as numpy array
            image_array = np.asarray(image)

            #optional change to pre-preocess image before NN sees it
            if self.image_part is not None:
                image_array = self.image_part.run(image_array)

            #forward pass - inference
            steering, throttle = self.kpart.run(image_array)

            #filter throttle here, as our NN doesn't always do a greate job
            throttle = self.throttle_control(last_steering, last_throttle, speed, throttle)

            #simulator will scale our steering based on it's angle based input.
            #but we have an opportunity for more adjustment here.
            steering *= self.steering_scale

            #send command back to Unity simulator
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
            #unless some hits Ctrl+C and then we get this interrupt
            print('stopping')
