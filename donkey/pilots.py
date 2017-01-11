'''

Methods to create, use, save and load pilots. Pilots 
contain the highlevel logic used to determine the angle
and throttle of a vehicle. Pilots can include one or more 
models to help direct the vehicles motion. 

'''
import os
import numpy as np

import random

from donkey import utils

class BasePilot():
    '''
    Base class to define common functions.
    When creating a class, only override the funtions you'd like to replace.
    '''
    
    def decide(self, img_arr):
        angle = 0
        speed = 0

        #Do prediction magic

        return angle, speed


class SwervePilot(BasePilot):
    '''
    Example predictor that should not be used.
    '''
    def __init__(self):
        self.angle= random.randrange(-45, 46)
        self.throttle = 20


    def decide(self, img_arr):

        new_angle = self.angle + random.randrange(-4, 5)
        self.angle = min(max(-45, new_angle), 45)

        return self, angle, self.throttle


class KerasAngle():
    def __init__(self, model, throttle):
        self.model = model
        self.throttle = throttle
        self.last_angle = 0

    def decide(self, img_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle = self.model.predict(img_arr)
        angle = angle[0][0]

        #add some smoothing
        a = .8
        angel = a * angle + (1-a) * self.last_angle
        self.last_angle = angle
        
        return angle, self.throttle

