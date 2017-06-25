#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 24 20:10:44 2017

@author: wroscoe
"""

"""
remotes.py

The client and web server needed to control a car remotely. 
"""

import json

import requests

import donkey as dk


class RemoteWebServer():
    '''
    Class used by a vehicle to send (http post requests) driving data and 
    recieve predictions from a remote webserver.
    '''
    
    def __init__(self, remote_url, connection_timeout=.25):

        self.control_url = remote_url
        self.time = 0.
        self.angle = 0.
        self.throttle = 0.
        self.mode = 'user'


        
    def update(self):
        '''
        Loop run in separate thread to request input from remote server.

        TODO: show the lag from the server to allow for safety stops, if 
        running local pilot.
        '''

        while True:
            #get latest value from server
            resp  = self.run()
            
            self.angle, self.throttle, self.mode = resp


    def run_threaded(self):
        ''' 
        Return the last state given from the remote server.
        '''
        
        #return last returned last remote response.
        return self.angle, self.throttle, self.mode

        
    def run(self, time):
        '''
        Posts current car sensor data to webserver and returns
        angle and throttle recommendations. 
        '''
        
        r = None
        while r == None:
            #Try connecting to server until connection is made.
            start = time.time()
            
            try:
                r = self.session.post(self.control_url, 
                                files={'img': dk.utils.arr_to_binary(img_arr), 
                                       'json': json.dumps(data)},
                                       timeout=0.25)
                
            except (requests.exceptions.ReadTimeout) as err:
                #Lower throttle if their is a long lag.
                print("\n Request took too long. Retrying")
                return angle, throttle * .8, None
                
            except (requests.ConnectionError) as err:
                #try to reconnect every 3 seconds
                print("\n Vehicle could not connect to server. Make sure you've " + 
                    "started your server and you're referencing the right port.")
                time.sleep(3)
            

        data = json.loads(r.text)
        angle = float(data['angle'])
        throttle = float(data['throttle'])
        drive_mode = str(data['drive_mode'])
        
        return angle, throttle, drive_mode