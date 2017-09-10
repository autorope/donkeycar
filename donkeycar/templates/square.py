# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.


Usage:
    car.py (drive) [--model=<model>]
    car.py (train) [--tub=<tub1,tub2,...tubn>] (--model=<model>)

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
    kl = dk.parts.KerasCategorical(model)
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
    
    
    
def train(tub_names, model_name):
    
    X_keys = ['cam/image_array']
    y_keys = ['user/angle', 'user/throttle']
    
    def rt(record):
        record['user/angle'] = dk.utils.linear_bin(record['user/angle'])
        return record

    def combined_gen(gens):
        import itertools
        combined_gen = itertools.chain()
        for gen in gens:
            combined_gen = itertools.chain(combined_gen, gen)
        return combined_gen
    
    kl = dk.parts.KerasCategorical()
    
    if tub_names:
        tub_paths = [os.path.join(DATA_PATH, n) for n in tub_names.split(',')]
    else:
        tub_paths = [os.path.join(DATA_PATH, n) for n in os.listdir(DATA_PATH)]
    tubs = [dk.parts.Tub(p) for p in tub_paths]

    gens = [tub.train_val_gen(X_keys, y_keys, record_transform=rt, batch_size=128) for tub in tubs]
    train_gens = [gen[0] for gen in gens]
    val_gens = [gen[1] for gen in gens]

    model_path = os.path.join(MODELS_PATH, model_name)
    kl.train(combined_gen(train_gens), combined_gen(val_gens), saved_model_path=model_path)



    
if __name__ == '__main__':
    args = docopt(__doc__)

    if args['drive']:
        drive(args['--model'])
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)
