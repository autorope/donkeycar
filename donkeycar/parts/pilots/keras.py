'''

pilots.py

Methods to create, use, save and load pilots. Pilots 
contain the highlevel logic used to determine the angle
and throttle of a vehicle. Pilots can include one or more 
models to help direct the vehicles motion. 

'''
import os
from datetime import datetime

from ... import utils




class KerasCategorical():
    def __init__(self, model_path, **kwargs):
        import keras
        self.model_path = model_path
        self.model = None #load() loads the model

    def run(self, img_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle_binned, throttle = self.model.predict(img_arr)
        angle_certainty = max(angle_binned[0])
        angle_unbinned = utils.unbin_Y(angle_binned)
        return angle_unbinned[0], throttle[0][0]


    def load(self):
        self.model = keras.models.load_model(self.model_path)
