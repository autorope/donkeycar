import json
import logging
import socket
import struct
import time
from threading import Thread
from typing import Any, Dict

from io import BytesIO
import base64

import numpy as np
from PIL import Image


mylogger = logging.getLogger(__name__)

class MessageProtocol:
    HEADER_FORMAT = '!I'  # 4-byte unsigned integer in network byte order
    
    @staticmethod
    def receive_message(client_socket):
        # Read the message header
        header_data = b''
        while len(header_data) < struct.calcsize(MessageProtocol.HEADER_FORMAT):
            header_chunk = client_socket.recv(struct.calcsize(MessageProtocol.HEADER_FORMAT) - len(header_data))
            if not header_chunk:
                raise EOFError('unexpected end of message header')
            header_data += header_chunk
        message_length = struct.unpack(MessageProtocol.HEADER_FORMAT, header_data)[0]
        
        # Read the message payload
        message_data = b''
        while len(message_data) < message_length:
            message_chunk = client_socket.recv(message_length - len(message_data))
            if not message_chunk:
                raise EOFError('unexpected end of message')
            message_data += message_chunk
        
        return message_data
    
    @staticmethod
    def send_message(client_socket, message):
        # Encode the message as bytes
        message_data = message.encode('utf-8')
        
        # Construct the message header
        header_data = struct.pack(MessageProtocol.HEADER_FORMAT, len(message_data))
        
        # Send the message header and payload
        client_socket.sendall(header_data)
        return client_socket.sendall(message_data)

class DonkeyWebotEnv(object):

    RECONNECT_DELAY=3

    def __init__(self, host="127.0.0.1", port=9091, headless=0, world_name="donkey-generated-track-v0", sync="asynchronous", conf={}):

        self.host=host
        self.port=port
        self.running = True
        self.flowOpen = False
        self.frame=None
        self.connect()

    def is_alive(self):
        socket_status = self.client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
        return socket_status
    
    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mylogger.info(f"Connect to Webot {self.host}:{self.port}")

        try:
            self.client_socket.connect((self.host, self.port))
        except ConnectionRefusedError:
            self.handle_disconnect('connect')
        self.flowOpen = True

    def handle_disconnect (self, origin='unspecified'):
        mylogger.info(f"Webot connection closed by server ({origin})")
        self.flowOpen = False
        self.client_socket.close()
        time.sleep(DonkeyWebotEnv.RECONNECT_DELAY)
        self.connect()

    def handle_incoming_packets(self):
        while True:
            try:
                message = MessageProtocol.receive_message(self.client_socket)
                self.on_message(message)
            except (OSError, EOFError, ConnectionResetError) as error:
                self.handle_disconnect('recv')

    def send_driving(self, throttle, steering):
        if self.flowOpen:
            payload={'type':'driving', 'data':{'throttle':throttle, 'steering':steering}}
            if self.client_socket:
                msg = json.dumps(payload)
                try:
                    if MessageProtocol.send_message(self.client_socket, msg)==0:
                        self.handle_disconnect('send null')
                except:
                    self.handle_disconnect('send')

    def on_message(self, message):
        json_msg = json.loads(message)
        if 'sensor' in json_msg:
            if json_msg['sensor'] == 'cam':
                self.frame = np.asarray(Image.open(BytesIO(base64.b64decode(json_msg['data']))))

    def update(self):
        while self.running:
            self.handle_incoming_packets()

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
