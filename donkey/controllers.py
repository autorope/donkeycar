#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 24 20:10:44 2017

@author: wroscoe

remotes.py

The client and web server needed to control a car remotely. 
"""

import json

import requests

class RemoteWebServer():
    '''
    A controller that repeatedly polls a remoet webserver and expects
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

        
    def run(self, time):
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