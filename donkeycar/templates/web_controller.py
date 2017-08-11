# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.


Usage:
    car.py (drive)
    car.py (train) (--tub=<tub>) (--model=<model>)

"""


import os
from docopt import docopt
import donkeycar as dk 

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')


def drive():
    V = dk.vehicle.Vehicle()
    #initialize values
    V.mem.put(['square/x', 'square/y'], (100,100))
    
    
    #display square box given by cooridantes.
    cam = dk.parts.SquareBoxCamera(resolution=(200,200))
    V.add(cam, 
          inputs=['square/x', 'square/y'],
          outputs=['square/image_array'])
    
    #display the image and read user values from a local web controller
    ctr = dk.parts.LocalWebController()
    V.add(ctr, 
          inputs=['square/image_array'],
          outputs=['user/angle', 'user/throttle', 
                   'user/mode', 'recording'],
          threaded=True)
    
    #transform angle and throttle values to coordinate values
    f = lambda x : int(x * 100 + 100)
    l = dk.parts.Lambda(f)
    V.add(l, inputs=['user/angle'], outputs=['square/x'])
    V.add(l, inputs=['user/throttle'], outputs=['square/y'])
    
    #add tub to save data
    inputs=['user/angle', 'user/throttle', 'square/image_array']
    types=['float', 'float', 'image_array']
    
    th = dk.parts.TubHandler(path=DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=50, max_loop_count=1000)
    
    
    
    #you can now go to localhost:8887 to move a square around the image
    
def train(tub, model):
    pass
    
if __name__ == '__main__':
    args = docopt(__doc__)

    if args['drive']:
        drive()
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)