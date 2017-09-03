#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it. 

Usage:
    manage.py drive [--model=<model>] [--web=<True/False>] [--throttle=<Throttle 0.0-1.0>]
    manage.py train (--tub=<tub>) (--model=<model>)
    manage.py calibrate
"""


import os
from docopt import docopt
import donkeycar as dk

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')


def drive(model_path=None, web_control=False, max_throttle=0.40):
    #Initialized car
    V = dk.vehicle.Vehicle()

    # Setup camera
    cam = dk.parts.PiCamera()
    V.add(cam, outputs=['cam/image_array'], threaded=True)

    # Select if only use bluetooth PS3 controller
    # Or web controller
    # Also set the max throttle
    if web_control:
        ctr = dk.parts.LocalWebController()
    else:
        ctr = dk.parts.JoystickPilot(max_throttle=max_throttle)
    V.add(ctr,
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)
    
    # See if we should even run the pilot module.
    # This is only needed because the part run_contion only accepts boolean
    def pilot_condition(mode):
        if mode == 'user':
            return False
        else:
            return True
        
    pilot_condition_part = dk.parts.Lambda(pilot_condition)
    V.add(pilot_condition_part, inputs=['user/mode'], outputs=['run_pilot'])
    
    # Run the pilot if the mode is not user
    kl = dk.parts.KerasCategorical()                                            # There is also KereasLinear()
    if model_path:
        print(model_path)
        kl.load(model_path)
    
    V.add(kl, inputs=['cam/image_array'], 
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot')

    # Choose what inputs should change the car.
    def drive_mode(mode, 
                   user_angle, user_throttle,
                   pilot_angle, pilot_throttle):
        if mode == 'user':
            return user_angle, user_throttle
        
        elif mode == 'local_angle':
            return pilot_angle, user_throttle
        
        else: 
            return pilot_angle, pilot_throttle
        
    drive_mode_part = dk.parts.Lambda(drive_mode)
    V.add(drive_mode_part, 
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'], 
          outputs=['angle', 'throttle'])

    # Configure the throttle and angle control hardware
    # Calibrate min/max for steering angle
    # Calibrate min/max/zero for throttle
    steering_controller = dk.parts.PCA9685(1)
    steering = dk.parts.PWMSteering(controller=steering_controller,
                                    left_pulse=460, right_pulse=260)
    
    throttle_controller = dk.parts.PCA9685(0)
    throttle = dk.parts.PWMThrottle(controller=throttle_controller,
                                    max_pulse=500, zero_pulse=370, min_pulse=220)
    
    V.add(steering, inputs=['angle'])
    V.add(throttle, inputs=['throttle'])
    
    # Add tub to save data
    inputs = ['cam/image_array',
              'user/angle', 'user/throttle',
              'pilot/angle', 'pilot/throttle',
              'user/mode']
    types = ['image_array',
             'float', 'float',
             'float', 'float',
             'str']
    
    th = dk.parts.TubHandler(path=DATA_PATH)
    tub_writer = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub_writer, inputs=inputs, run_condition='recording')
    
    # Run the vehicle for 20 seconds
    V.start(rate_hz=20, max_loop_count=100000)
    
    print("You can now go to <your pi ip address>:8887 to drive your car.")



def train(tub_name, model_name):
    
    kl = dk.parts.KerasCategorical()
    
    tub_path = os.path.join(DATA_PATH, tub_name)
    tub = dk.parts.Tub(tub_path)
    
    X_keys = ['cam/image_array']
    y_keys = ['user/angle', 'user/throttle']
    
    def rt(record):
        record['user/angle'] = dk.utils.linear_bin(record['user/angle'])
        #record['user/throttle'] = dk.utils.linear_bin(record['user/throttle'])      # !!! Possible where to fix throttle
        return record
    
    train_gen, val_gen = tub.train_val_gen(X_keys, y_keys, 
                                           record_transform=rt, batch_size=128)
    
    model_path = os.path.join(MODELS_PATH, model_name)
    kl.train(train_gen, None, saved_model_path=model_path)




def calibrate():
    channel = int(input('Enter the channel your actuator uses (0-15).'))
    c = dk.parts.PCA9685(channel)
    
    for i in range(10):
        pmw = int(input('Enter a PWM setting to test(100-600)'))
        c.run(pmw)


if __name__ == '__main__':
    args = docopt(__doc__)

    if args['drive']:
        model = args['--model']
        web = args['--web']
        throttle = args['--throttle']
        drive(model_path=model, web_control=web, max_throttle=throttle)
    elif args['calibrate']:
        calibrate()
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)




