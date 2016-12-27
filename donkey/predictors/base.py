'''

Methods to create, use, save and load predictors. These
are used to control the vehicle autonomously.

'''
import os
import settings
import numpy as np

import random

from utils import file as file_utils

class BasePredictor():
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
        self.model_path = os.path.join(settings.MODELS_DIR, self.model_name)
        print('loading model from %' %self.model_path)
        self.model = open(self.model_path)


    def predict(self, arr):
        angle = 0
        speed = 0

        #Do prediction magic

        return angle, speed


class RandomPredictor(BasePredictor):
    '''
    Example predictor to demontrate the format.
    '''

    def predict(self, img):
        angle = random.randrange(-90, 91)
        speed = random.randrange(-100,101)
        return angle, speed


    def fit(self, x, y):
        model = "some model to save"
        return model

    def load(self, model): 
        print('This model doesnt need to Load')
