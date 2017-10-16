#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it. 

Usage:
    manage.py (drive) [--model=<model>] [--js]
    manage.py (train) [--tub=<tub1,tub2,..tubn>] (--model=<model>) [--no_cache]
    manage.py (calibrate)
    manage.py (check) [--tub=<tub1,tub2,..tubn>] [--fix]
    manage.py (histogram) [--tub=<tub1,tub2,..tubn>] (--rec=<"user/angle">)
    manage.py (plot_predictions) [--tub=<tub1,tub2,..tubn>] (--model=<model>)

Options:
    -h --help     Show this screen.
    --js          Use physical joystick.
    --fix         Remove records which cause problems.
    --no_cache    During training, load image repeatedly on each epoch

"""
import os
from docopt import docopt
import donkeycar as dk 


def drive(cfg, model_path=None, use_joystick=False):
    '''
    Construct a working robotic vehicle from many parts.
    Each part runs as a job in the Vehicle loop, calling either
    it's run or run_threaded method depending on the constructor flag `threaded`.
    All parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely manner.
    Parts may have named outputs and inputs. The framework handles passing named outputs
    to parts requesting the same named input.
    '''

    #Initialize car
    V = dk.vehicle.Vehicle()
    cam = dk.parts.PiCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam, outputs=['cam/image_array'], threaded=True)
    
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        #modify max_throttle closer to 1.0 to have more power
        #modify steering_scale lower than 1.0 to have less responsive steering
        ctr = dk.parts.JoystickController(max_throttle=cfg.JOYSTICK_MAX_THROTTLE,
                                    steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                    auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
    else:        
        #This web controller will create a web server that is capable
        #of managing steering, throttle, and modes, and more.
        ctr = dk.parts.LocalWebController()

    
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
            'user/mode']
    types=['image_array',
           'float', 'float',  
           'str']
    
    th = dk.parts.TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)
    
    print("You can now go to <your pi ip address>:8887 to drive your car.")

def train(cfg, tub_names, model_name, cache):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    '''
    X_keys = ['cam/image_array']
    y_keys = ['user/angle', 'user/throttle']
    
    def rt(record):
        record['user/angle'] = dk.utils.linear_bin(record['user/angle'])
        return record

    kl = dk.parts.KerasCategorical()
    
    tub_paths = dk.utils.gather_tub_paths(cfg, tub_names)

    if cache:
        print('cache is ON')
    else:
        print('cache is OFF')

    tub_chain = dk.parts.TubChain(tub_paths, X_keys, y_keys, cache=cache, record_transform=rt, batch_size=cfg.BATCH_SIZE, train_split=cfg.TRAIN_TEST_SPLIT)
    train_gens, val_gens = tub_chain.train_val_gen()

    model_path = os.path.expanduser(model_name)

    total_records = tub_chain.total_records()
    total_train = int(total_records * cfg.TRAIN_TEST_SPLIT)
    total_val = total_records - total_train
    print('train: %d, validation: %d' %(total_train, total_val))
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    print('steps_per_epoch', steps_per_epoch)

    kl.train(train_gens, 
        val_gens, 
        saved_model_path=model_path,
        steps=steps_per_epoch,
        train_split=cfg.TRAIN_TEST_SPLIT)


def calibrate():
    channel = int(input('Enter the channel your actuator uses (0-15).'))
    c = dk.parts.PCA9685(channel)
    
    for i in range(10):
        pmw = int(input('Enter a PWM setting to test(100-600)'))
        c.run(pmw)

def check(cfg, tub_names, fix=False):
    '''
    Check for any problems. Looks at tubs and find problems in any records or images that won't open.
    If fix is True, then delete images and records that cause problems.
    '''
    tubs = dk.utils.gather_tubs(cfg, tub_names)

    for tub in tubs:
        tub.check(fix=fix)

def histogram(cfg, tub_names, record):
    '''
    Produce a histogram of record type frequency in the given tub
    '''
    tubs = dk.utils.gather_tubs(cfg, tub_names)

    import matplotlib.pyplot as plt
    samples = []
    for tub in tubs:
        num_records = tub.get_num_records()
        for iRec in tub.get_index(shuffled=False):
            try:
                json_data = tub.get_json_record(iRec)
                sample = json_data[record]
                samples.append(float(sample))
            except FileNotFoundError:
                pass

    fig = plt.figure()
    plt.hist(samples, 50)
    title = "Histgram of %s in %s " % (record, tub_names)
    fig.suptitle(title)
    plt.xlabel(record)
    plt.show()

def plot_predictions(cfg, tub_names, model_name):
    '''
    Plot model predictions for angle and throttle against data from tubs.

    '''
    import matplotlib.pyplot as plt
    import pandas as pd

    tubs = dk.utils.gather_tubs(cfg, tub_names)
    
    model_path = os.path.expanduser(model_name)
    model = dk.parts.KerasCategorical()
    model.load(model_path)

    user_angles = []
    user_throttles = []
    pilot_angles = []
    pilot_throttles = []

    for tub in tubs:
        num_records = tub.get_num_records()
        for iRec in tub.get_index(shuffled=False):
            record = tub.get_record(iRec)
            
            img = record["cam/image_array"]    
            user_angle = float(record["user/angle"])
            user_throttle = float(record["user/throttle"])
            pilot_angle, pilot_throttle = model.run(img)

            user_angles.append(user_angle)
            user_throttles.append(user_throttle)
            pilot_angles.append(pilot_angle)
            pilot_throttles.append(pilot_throttle)

    angles_df = pd.DataFrame({'user_angle': user_angles, 'pilot_angle': pilot_angles})
    throttles_df = pd.DataFrame({'user_throttle': user_throttles, 'pilot_throttle': pilot_throttles})

    fig = plt.figure()

    title = "Model Predictions\nTubs: " + tub_names + "\nModel: " + model_name
    fig.suptitle(title)

    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212)

    angles_df.plot(ax=ax1)
    throttles_df.plot(ax=ax2)

    ax1.legend(loc=4)
    ax2.legend(loc=4)

    plt.show()


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    
    if args['drive']:
        drive(cfg, model_path = args['--model'], use_joystick=args['--js'])
    
    elif args['calibrate']:
        calibrate()
    
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        cache = not args['--no_cache']
        train(cfg, tub, model, cache)

    elif args['check']:
        tub = args['--tub']
        fix = args['--fix']
        check(cfg, tub, fix)

    elif args['histogram']:
        tub = args['--tub']
        rec = args['--rec']
        histogram(cfg, tub, rec)

    elif args['plot_predictions']:
        tub = args['--tub']
        model = args['--model']
        plot_predictions(cfg, tub, model)




