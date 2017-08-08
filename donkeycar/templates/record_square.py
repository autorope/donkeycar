# -*- coding: utf-8 -*-
"""
Record a moving square example.

Usage:
    car.py (drive)
    car.py (train) (--tub=<tub>) (--model=<model>)

This example simulates a square that bounces around a frame
and records the frames and coordinates to disk.

"""
from docopt import docopt
import donkeycar as dk 
import os

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')

def drive():
    #make the membory 
    V = dk.Vehicle()
    
    #telemetry simulator to make box bounce off walls
    tel = dk.parts.MovingSquareTelemetry(max_velocity=5)
    V.add(tel, 
          outputs=['square/x', 'square/y'])
    
    #fake camera that shows a square at specific coordinates
    cam = dk.parts.SquareBoxCamera(resolution=(120,160), 
                                     box_size=10, 
                                     color=[33,200,2])
    V.add(cam, 
          inputs=['square/x', 'square/y'], 
          outputs=['square/image_array'])
    
    #Add a datastore to record the images.
    inputs = ['square/x', 'square/y', 'square/image_array']
    types = ['float', 'float', 'image_array']
    #add tub to save data
    th = dk.parts.TubHandler(path=DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs)
    
    
    #Run vehicel for 10 loops
    V.start(max_loop_count=100, rate_hz=1000)


def train(tub_name, model_name):
    
    km = dk.parts.KerasModels()
    model = km.default_linear()
    kl = dk.parts.KerasLinear(model)
    
    tub_path = os.path.join(DATA_PATH, tub_name)
    tub = dk.parts.Tub(tub_path)
    batch_gen = tub.batch_gen()
    
    X_keys = ['square/image_array']
    Y_keys = ['square/x', 'square/y']
    
    def train_gen(gen, X_keys, y_keys):
        while True:
            batch = next(gen)
            X = [batch[k] for k in X_keys]
            y = [batch[k] for k in y_keys]
            yield X, y
            
    keras_gen = train_gen(batch_gen, X_keys, Y_keys)
    
    model_path = os.path.join(MODELS_PATH, model_name)
    kl.train(keras_gen, None, saved_model_path=model_path, epochs=10)
    
    
if __name__ == '__main__':
    args = docopt(__doc__)

    if args['drive']:
        drive()
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)