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


    def save(self):
        pass

    def load(self, model):
        self.model_path = os.path.join(settings.MODELS_DIR, self.model_name)
        print('loading model from %' %self.model_path)
        self.model = open(self.model_path)


    def predict(self):
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

from keras.models import Sequential, load_model
from keras.layers import Convolution2D, MaxPooling2D, Convolution1D, MaxPooling1D
from keras.layers import Activation, Dropout, Flatten, Dense

class ConvolutionPredictor(BasePredictor):
    def __init__(self):
        pass

    def create(self, model_name):
        self.model_path = os.path.join(settings.MODELS_DIR, model_name)
        
        model = Sequential()
        model.add(Convolution1D(32, 3, input_shape=(128, 128)))
        model.add(Activation('relu'))
        model.add(MaxPooling1D(2))

        model.add(Convolution1D(32, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling1D(2))

        model.add(Convolution1D(64, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling1D(2))


        model.add(Flatten())  # this converts our 3D feature maps to 1D feature vectors
        model.add(Dense(64))
        model.add(Activation('relu'))
        model.add(Dropout(0.5))
        model.add(Dense(2))

        model.compile(loss='mse',
                      optimizer='rmsprop')

        self.model = model


    def fit(self, X, Y):
        self.model.fit(X, Y,
                        nb_epoch=100,
                        batch_size=1000,
                        shuffle=True,
                        validation_data=(X[:10], Y[:10]))


    def save(self):
        self.model.save(self.model_path)

    def load(self, model_name):
        self.model_path = os.path.join(settings.MODELS_DIR, model_name)
        self.model = load_model(self.model_path)


    def predict(self, x):
        x = np.array([x])
        y = self.model.predict(x)
        return y[0]
