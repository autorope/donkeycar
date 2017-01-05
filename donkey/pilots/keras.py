'''

Methods to create, use, save and load predictors. These
are used to control the vehicle autonomously.

'''
import os
import numpy as np

import random

from ..utils import file_utils
from ..utils import bin_utils

from keras.models import Sequential, load_model
from keras.layers import Convolution2D, MaxPooling2D, Convolution1D, MaxPooling1D
from keras.layers import Activation, Dropout, Flatten, Dense

from .base import BasePilot

class BaseKerasPilot(BasePilot): 
    def save(self, path):
        self.model.save(path)

    def load(self, path):
        self.model = load_model(path)



class CNN(BaseKerasPilot):
    def __init__(self):

        model = Sequential()
        model.add(Convolution2D(8, 3, 3, input_shape=(3, 120, 160)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(12, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(16, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(32, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Flatten())  # this converts our 3D feature maps to 1D feature vectors
        model.add(Dense(256))
        model.add(Activation('relu'))

        model.add(Dropout(.2))
        model.add(Dense(2))

        model.compile(loss='mse', optimizer='adam')

        self.model = model


    def train(self, X, Y):

        #convert array to keras format (channels, width, height)
        X_keras = []
        for arr in X:
            karr=arr.transpose(2, 0, 1)
            X_keras.append(karr)
        X = np.array(X_keras)


        self.model.fit(X, Y,
                        nb_epoch=50,
                        batch_size=1000,
                        shuffle=True,
                        validation_data=(X[:10], Y[:10]))


    def predict(self, x):

        x=x.transpose(2, 0, 1) #convert to keras array format
        x = np.array([x])
        angle, throttle = self.model.predict(x)[0]

        #return angle, throttle
        return angle, 275



class CNNAnglePredictor(BaseKerasPilot):
    def __init__(self):
        pass


    def predict(self, x):

        x=x.transpose(2, 0, 1) #convert to keras array format
        x = np.array([x])
        angle = self.model.predict(x)[0][0]

        #return angle, throttle
        return angle, 275


class CarputerPredictor(BaseKerasPilot):
    """ 
    This is an attept to replicate the NN used by the Carputer.
    https://github.com/otaviogood/carputer

    Differences include:
    * Carputer adds in a velocity value when the network is flatted.
    * Carputer maps throttle 0-15, this maps throttle 0-7

    Note: When trained on a limited dataset, this model will only output fixed
    values.

    TODO: Try this model on a bigger dataset.

    """

    def __init__(self):
        pass

    def create(self, model_name):
        self.model_path = os.path.join(settings.MODELS_DIR, model_name)
        
        model = Sequential()
        model.add(Convolution2D(8, 3, 3, input_shape=(3, 120, 160)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(12, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(16, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Convolution2D(32, 3, 3))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Flatten())  # this converts our 3D feature maps to 1D feature vectors
        model.add(Dense(256))
        model.add(Activation('relu'))

        model.add(Dropout(.2))
        model.add(Dense(22))

        model.compile(loss='categorical_crossentropy', optimizer='adam')

        self.model = model



    def predict(self, x):

        y = self.model.predict(x)

        #convert binned output to real numbers
        angle, throttle = bin_utils.unbin_telemetry(y[0])
        return angle, throttle
