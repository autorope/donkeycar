#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it. 

Usage:
    manage.py (drive) [--model=<model>]
    manage.py (train) [--tub=<tub1,tub2,..tubn>] (--model=<model>)
    manage.py (calibrate)
"""


import os
from docopt import docopt
import donkeycar as dk 


def drive(cfg, model_path=None):
    #Initialized car
    V = dk.vehicle.Vehicle()
    cam = dk.parts.PiCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam, outputs=['cam/image_array'], threaded=True)
    
    ctr = dk.parts.LocalWebController()

    '''
    #Joystick pilot below is an alternative controller.
    #Comment out the above ctr= and enable the below ctr= to switch.
    #modify max_throttle closer to 1.0 to have more power
    #modify steering_scale lower than 1.0 to have less responsive steering
    ctr = dk.parts.JoystickPilot(max_throttle=cfg.JOYSTICK_MAX_THROTTLE,
                                 steering_scale=cfg.JOYSTICK_STEERING_SCALE)
    '''
    
    V.add(ctr, 
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
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
    kl = dk.parts.KerasCategorical()
    if model_path:
        kl.load(model_path)
    
    V.add(kl, inputs=['cam/image_array'], 
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot')
    
    
    #Choose what inputs should change the car.
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
    
    
    steering_controller = dk.parts.PCA9685(cfg.STEERING_CHANNEL)
    steering = dk.parts.PWMSteering(controller=steering_controller,
                                    left_pulse=cfg.STEERING_LEFT_PWM, 
                                    right_pulse=cfg.STEERING_RIGHT_PWM)
    
    throttle_controller = dk.parts.PCA9685(cfg.THROTTLE_CHANNEL)
    throttle = dk.parts.PWMThrottle(controller=throttle_controller,
                                    max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                    zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                                    min_pulse=cfg.THROTTLE_REVERSE_PWM)
    
    V.add(steering, inputs=['angle'])
    V.add(throttle, inputs=['throttle'])
    
    #add tub to save data
    inputs=['cam/image_array',
            'user/angle', 'user/throttle', 
            #'pilot/angle', 'pilot/throttle', 
            'user/mode']
    types=['image_array',
           'float', 'float',  
           #'float', 'float', 
           'str']
    
    th = dk.parts.TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)
    
    print("You can now go to <your pi ip address>:8887 to drive your car.")



def train(cfg, tub_names, model_name):
    
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
        tub_paths = [os.path.join(cfg.DATA_PATH, n) for n in tub_names.split(',')]
    else:
        tub_paths = [os.path.join(cfg.DATA_PATH, n) for n in os.listdir(cfg.DATA_PATH)]
    tubs = [dk.parts.Tub(p) for p in tub_paths]

    gens = [tub.train_val_gen(X_keys, y_keys, record_transform=rt, batch_size=128) for tub in tubs]
    train_gens = [gen[0] for gen in gens]
    val_gens = [gen[1] for gen in gens]

    model_path = os.path.join(cfg.MODELS_PATH, model_name)
    kl.train(combined_gen(train_gens), combined_gen(val_gens), saved_model_path=model_path)




def calibrate():
    channel = int(input('Enter the channel your actuator uses (0-15).'))
    c = dk.parts.PCA9685(channel)
    
    for i in range(10):
        pmw = int(input('Enter a PWM setting to test(100-600)'))
        c.run(pmw)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    
    if args['drive']:
        drive(cfg, model_path = args['--model'])
    
    elif args['calibrate']:
        calibrate()
    
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(cfg, tub, model)




