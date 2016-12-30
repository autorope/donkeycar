'''

Methods to create, use, save and load predictors. These
are used to control the vehicle autonomously.

'''
import os
import numpy as np

import random

from ..utils import file_utils

class BasePilot():
    '''
    Base class to define common functions.
    When creating a class, only override the funtions you'd like to replace.
    '''
    
    def __init__(self):
        self.model = None

    def create(self, model=None): pass

    def save(self):
        pass

    def load(self, model):
        pass


    def decide(self, arr):
        angle = 0
        speed = 0

        #Do prediction magic

        return angle, speed


class RandomPilot(BasePilot):
    '''
    Example predictor to demontrate the format.
    '''

    def decide(self, img):
        angle = random.randrange(-90, 91)
        speed = random.randrange(-100,101)
        return angle, speed