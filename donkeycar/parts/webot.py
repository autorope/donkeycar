import json
import logging
import socket
import time
from threading import Thread
from typing import Any, Dict

from io import BytesIO
import base64

import numpy as np
from PIL import Image

import tornado.ioloop
import tornado.websocket
from tornado import gen

logger = logging.getLogger(__name__)

class DonkeyWebotEnv(object):

    def __init__(self, host="127.0.0.1", port=9091, headless=0, world_name="donkey-generated-track-v0", sync="asynchronous", conf={}):

        self.host=host
        self.port=port
        self.running = True
        self.aborted = False
        self.do_process_msgs = False
        self.connection = None
        self.io_loop = tornado.ioloop.IOLoop.current()
        self.io_loop.add_callback(self.start)
        self.ws = None

        self.frame=None

    def start(self):
        self.connect_and_read()

    def stop(self):
        self.io_loop.stop()

    @gen.coroutine
    def connect_and_read(self):
        url=f"ws://{self.host}:{self.port}/websocket/"
        print(f"Connect to {url}")
        try:
            self.ws = yield tornado.websocket.websocket_connect(
                url=url,
                callback=self.maybe_retry_connection,
                on_message_callback=self.on_message,
                ping_interval=10,
                ping_timeout=30,
            )
        except Exception:
            print ("connection error")
        else:
            print ("connected")

    def send_driving(self, throttle, steering):
        payload={'type':'driving', 'data':{'throttle':throttle, 'steering':steering}}
        if self.ws:
            msg = json.dumps(payload)
            try:
                self.ws.write_message(msg)
            except tornado.websocket.StreamClosedError:
                print ("Sending aborted")

    def maybe_retry_connection(self, future) -> None:
        try:
            self.connection = future.result()
        except:
            print("Could not reconnect, retrying in 3 seconds...")
            self.io_loop.call_later(3, self.connect_and_read)

    def on_message(self, message):
        if message is None:
            print("Disconnected, reconnecting...")
            self.connect_and_read()
        else:
            json_msg = json.loads(message)
            if 'sensor' in json_msg:
                if json_msg['sensor'] == 'cam':
                    self.frame = np.asarray(Image.open(BytesIO(base64.b64decode(json_msg['data']))))

    def update(self):
        while self.running:
            self.io_loop.start()

    def run_threaded(self, steering, throttle, brake=None):

        if steering is None or throttle is None:
            steering = 0.0
            throttle = 0.0
        if brake is None:
            brake = 0.0

        self.steering = steering
        self.throttle = throttle
        self.send_driving (self.throttle, self.steering)
        return self.frame

    def shutdown(self):
        self.running = False
        time.sleep(0.2)
        self.stop()
