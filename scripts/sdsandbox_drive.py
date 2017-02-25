#!/usr/bin/env python
'''
Predict Server
Create a server to accept image inputs and run them against a trained neural network.
This then sends the steering output back to the client.
Author: Tawn Kramer
Modified: Alan Steremberg
'''
import os
import argparse
import sys
import numpy as np
import h5py
import json
#import matplotlib.pyplot as plt
import time
import asyncore
import json
import socket
from PIL import Image

import struct

import donkey as dk
import cv2


class RemoteSteeringServer(asyncore.dispatcher):
    """Receives connections and establishes handlers for each client.
    """
    
    def __init__(self, address, pilot):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(address)
        self.address = self.socket.getsockname()
        print ('binding to', self.address)
        self.listen(1)
        self.pilot= pilot
        return

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        #self.logger.debug('handle_accept() -> %s', client_info[1])
        print ('got a new client', client_info[1])
        h = SteeringHandler(sock=client_info[0], chunk_size=8*1024, pilot=self.pilot)
        return
    
    def handle_close(self):
        #self.logger.debug('handle_close()')
        self.close()
        return

class SteeringHandler(asyncore.dispatcher):
    """Handles echoing messages from a single client.
    """
    IDLE = 1
    GETTING_IMG = 2
    SENDING_STEERING = 3
    
    def __init__(self, sock, chunk_size=256, pilot=None):
        self.pilot= pilot 
        self.chunk_size = chunk_size
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = []
        self.image_byes = []
        self.mode = self.IDLE
        self.start_time = time.time()

        return
    
    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        return response
    
    def handle_write(self):
        """Write as much as possible of the most recent message we have received."""
        data = self.data_to_write.pop()
        print('data:'+data)
        sent = self.send(data[:self.chunk_size].encode('utf-8'))
        print('sent:'+str(sent)+' len(data):'+str(len(data)))
        if sent < len(data):
            remaining = data[sent:].encode('utf-8')
            self.data.to_write.append(remaining)
        elif self.mode == self.SENDING_STEERING:
          self.mode = self.IDLE

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        view_image = False
        #print ('got', len(data), 'bytes')
        if len(data) == 0:
          self.handle_close()
        elif self.mode == self.IDLE:
          try:
            jsonObj = json.loads(data.decode('utf-8'))
            self.num_bytes = jsonObj['num_bytes']
            self.width = jsonObj['width']
            self.height = jsonObj['height']
            self.num_channels = jsonObj['num_channels']
            self.format = jsonObj['format']
            self.flip_y = jsonObj['flip_y']
            self.data_to_write.insert(0, "{ 'response' : 'ready_for_image' }")
            self.mode = self.GETTING_IMG
            self.image_byes = []
            self.num_read = 0
          except:
            self.mode = self.IDLE
            print ('failed to read json from: ', data)
        elif self.mode == self.GETTING_IMG:
          self.image_byes.append(data)
          self.num_read += len(data)
          if self.num_read == self.num_bytes:
            lin_arr = np.fromstring(b''.join(self.image_byes), dtype=np.uint8)
            self.mode = self.SENDING_STEERING
            if self.format == 'array_of_pixels':
              img = lin_arr.reshape(self.width, self.height, self.num_channels)
              if self.flip_y:
                img = np.flipud(img)
              img = img.transpose()
            else: #assumed to be ArrayOfChannels
              img = lin_arr.reshape(self.num_channels, self.width, self.height)
            if view_image:
              #this can be useful when validating that you have your images coming in correctly.
              vis_img = Image.fromarray(img.transpose(), 'RGB')
              vis_img.show()
              #this launches too many windows if we leave it up.
              self.handle_close()

            # hook up donkey here
            now = time.time()
            milliseconds = int( (now - self.start_time) * 1000)
            # make the image_arr the right size
            #print(img.shape)
            #vis_img = Image.fromarray(img.transpose(), 'RGB')
            #print(vis_img.shape)
            img_arr = cv2.resize(img.transpose(),(160,160))
            #print(img_arr.shape)
            #img_arr = img_arr[:, 00:120]
            img_arr = img_arr[ :120, :]
            #print(img_arr.shape)
            angle=0
            throttle=0
            angle, throttle = self.pilot.decide( img_arr,
                                                 angle,
                                                 throttle,
                                                 milliseconds)
            print('angle: %s   throttle: %s' %(angle, throttle) )


            #steering = self.model.predict(img[None, :, :, :])
            steering = angle
            reply = '{ "steering" : "%f", "throttle" : "%f" }' % (steering,throttle)
            self.data_to_write.append(reply)
        else:
            print ("wasn't prepared to recv request!")
    
    def handle_close(self):
        self.close()

def go(address,remote_url):
  #Get all autopilot signals from remote host
  mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id='mycar')
  
  s = RemoteSteeringServer(address, mypilot)
  try:
    asyncore.loop()
  except KeyboardInterrupt:
    print ('stopping')

# ***** main loop *****
if __name__ == "__main__":


  parser = argparse.ArgumentParser(description='prediction server')
  parser.add_argument('--remote', dest='remote', default='http://localhost:8887', help='remote url') 
  args = parser.parse_args()

  #
  #  Let's initialize the donkey things
  #

  address = ('0.0.0.0', 9090)
  go(address,args.remote)
