"""
Script to drive a TF model as fast as possible

Usage:
    profile.py (--model=<model>)
    
Options:
    -h --help        Show this screen.
"""
import os
from docopt import docopt
import keras
import numpy as np
import time

class FPSTimer(object):
    def __init__(self):
        self.t = time.time()
        self.iter = 0

    def reset(self):
        self.t = time.time()
        self.iter = 0

    def on_frame(self):
        self.iter += 1
        if self.iter == 100:
            e = time.time()
            print('fps', 100.0 / (e - self.t))
            self.t = time.time()
            self.iter = 0

def profile(model_path):

    #load keras model
    model = keras.models.load_model(model_path)

    #query the input to see what it likes
    count, w, h, ch = model.inputs[0].get_shape()

    #generate random array in the right shape
    img = np.random.rand(int(w), int(h), int(ch))

    #make a timer obj
    timer = FPSTimer()

    try:
        while True:

            '''
            run forward pass on model
            '''
            model.predict(img[None, :, :, :])

            '''
            keep track of iterations and give feed back on iter/sec
            '''
            timer.on_frame()

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    args = docopt(__doc__)
    profile(model_path = args['--model'])
