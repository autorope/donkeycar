# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.


Usage:
    car.py (drive) [--model=<model>]
    car.py (train) (--tub=<tub>) (--model=<model>)

"""


import os
from docopt import docopt
import donkeycar as dk 

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')


def drive(model=None):
    V = dk.vehicle.Vehicle()
    #initialize values
    V.mem.put(['square/angle', 'square/throttle'], (100,100))
    
    
    #display square box given by cooridantes.
    cam = dk.parts.SquareBoxCamera(resolution=(120,160))
    V.add(cam, 
          inputs=['square/angle', 'square/throttle'],
          outputs=['cam/image_array'])
    
    #display the image and read user values from a local web controller
    ctr = dk.parts.LocalWebController()
    V.add(ctr, 
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 
                   'user/mode', 'recording'],
          threaded=True)
    
    #See if we should even run the pilot module. 
    #This is only needed because the part run_contion only accepts boolean
    def pilot_condition(mode):
        if mode == 'user':
            return False
        else:
            return True
        
    pilot_condition_part = dk.parts.Lambda(pilot_condition)
    V.add(pilot_condition_part, inputs=['user/mode'], outputs=['run_pilot'])
    
    #Run the pilot if the mode is not user.
    kl = dk.parts.KerasLinear(model)
    V.add(kl, inputs=['cam/image_array'], 
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot')
    
    
    #See if we should even run the pilot module. 
    def drive_mode(mode, 
                   user_angle, user_throttle,
                   pilot_angle, pilot_throttle):
        if mode == 'user':
            return user_angle, user_throttle
        
        elif mode == 'pilot_angle':
            return pilot_angle, user_throttle
        
        else: 
            return pilot_angle, pilot_throttle
        
    drive_mode_part = dk.parts.Lambda(drive_mode)
    V.add(drive_mode_part, 
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'], 
          outputs=['angle', 'throttle'])
    
    
    
    #transform angle and throttle values to coordinate values
    f = lambda x : int(x * 100 + 100)
    l = dk.parts.Lambda(f)
    V.add(l, inputs=['user/angle'], outputs=['square/angle'])
    V.add(l, inputs=['user/throttle'], outputs=['square/throttle'])
    
    #add tub to save data
    inputs=['cam/image_array',
            'user/angle', 'user/throttle', 
            'pilot/angle', 'pilot/throttle', 
            'square/angle', 'square/throttle',
            'user/mode']
    types=['image_array',
           'float', 'float',  
           'float', 'float', 
           'float', 'float',
           'str']
    
    th = dk.parts.TubHandler(path=DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=50, max_loop_count=100000)
    
    
    
    #you can now go to localhost:8887 to move a square around the image
def train(tub_name, model_name):
    
    km = dk.parts.KerasModels()
    model = km.default_linear()
    kl = dk.parts.KerasLinear(model)
    
    tub_path = os.path.join(DATA_PATH, tub_name)
    print(tub_path)
    tub = dk.parts.Tub(tub_path)
    batch_gen = tub.batch_gen()
    
    X_keys = ['cam/image_array']
    Y_keys = ['square/angle', 'square/throttle']
    
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
        drive(args['--model'])
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)