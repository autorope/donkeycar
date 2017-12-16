#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it. 

Usage:
    manage.py (drive) [--model=<model>] [--js]
    manage.py (train) [--tub=<tub1,tub2,..tubn>]  (--model=<model>) [--no_cache]
    manage.py (sim) (--model=<model>) [--top_speed=<5>]

Options:
    -h --help        Show this screen.
    --tub TUBPATHS   List of paths to tubs. Comma separated. Use quotes to use wildcards. ie "~/tubs/*"
    --js             Use physical joystick.
"""
from numpy.random import seed
seed(1)
from tensorflow import set_random_seed
set_random_seed(2)
import os
import glob
import numpy as np

from docopt import docopt

import donkeycar as dk

#import parts
from donkeycar.parts.camera import PiCamera
from donkeycar.parts.transform import Lambda
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.datastore import TubHandler, TubGroup
from donkeycar.parts.controller import LocalWebController, JoystickController
from donkeycar.parts.simulation import SteeringServer
from donkeycar.parts.keras import KerasRNN_LSTM
from donkeycar.parts.datastore import Tub

SEQ_LEN = 3

import numpy as np

class LastNImages(object):
    '''
    keep an array of the last N images
    '''

    def __init__(self, seq_len):
        self.images = []
        self.seq_len = seq_len

    def run(self, img):
        while len(self.images) < self.seq_len:
            self.images.append(img)

        self.images = self.images[1:]
        self.images.append(img)
        return self.images

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
    from donkeycar.parts.led_status import RGB_LED

    #Initialize car
    V = dk.vehicle.Vehicle()
    cam = PiCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam, outputs=['cam/image_array'], threaded=True)
    
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        #modify max_throttle closer to 1.0 to have more power
        #modify steering_scale lower than 1.0 to have less responsive steering
        ctr = JoystickController(max_throttle=cfg.JOYSTICK_MAX_THROTTLE,
                                 steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                 auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
    else:        
        #This web controller will create a web server that is capable
        #of managing steering, throttle, and modes, and more.
        ctr = LocalWebController()

    
    V.add(ctr, 
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)
    
    #See if we should even run the pilot module. 
    #This is only needed because the part run_condition only accepts boolean
    def pilot_condition(mode):
        if mode == 'user':
            return False
        else:
            return True
        
    pilot_condition_part = Lambda(pilot_condition)
    V.add(pilot_condition_part, inputs=['user/mode'], outputs=['run_pilot'])
    
    def led_cond(mode, recording, num_records):
        '''
        returns a blink rate. 0 for off. -1 for on. positive for rate.
        '''

        if num_records is not None and num_records % 10 == 0:
            print("recorded", num_records, "records")

        if recording:
            return -1 #solid on
        elif mode == 'user':
            return 1
        elif mode == 'local_angle':
            return 0.5
        elif mode == 'local':
            return 0.1
        return 0 

    led_cond_part = Lambda(led_cond)
    V.add(led_cond_part, inputs=['user/mode', 'recording', "tub/num_records"], outputs=['led/blink_rate'])

    #led = LED(8)
    led = RGB_LED(12, 10, 16)
    led.set_rgb(0, 0, 1)
    V.add(led, inputs=['led/blink_rate'])
    
    #lastNImages = LastNImages(SEQ_LEN)
    #V.add(lastNImages, inputs=['cam/image_array'], outputs=['cam/last_N'])

    #Run the pilot if the mode is not user.
    kl = KerasRNN_LSTM(seq_length=SEQ_LEN, num_outputs=2)

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
        
    drive_mode_part = Lambda(drive_mode)
    V.add(drive_mode_part, 
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'], 
          outputs=['angle', 'throttle'])
    
    
    steering_controller = PCA9685(cfg.STEERING_CHANNEL)
    steering = PWMSteering(controller=steering_controller,
                                    left_pulse=cfg.STEERING_LEFT_PWM, 
                                    right_pulse=cfg.STEERING_RIGHT_PWM)
    
    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL)
    throttle = PWMThrottle(controller=throttle_controller,
                                    max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                    zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                                    min_pulse=cfg.THROTTLE_REVERSE_PWM)
    
    V.add(steering, inputs=['angle'])
    V.add(throttle, inputs=['throttle'])
    
    #add tub to save data
    inputs=['cam/image_array', 'user/angle', 'user/throttle', 'user/mode']
    types=['image_array', 'float', 'float',  'str']
    
    th = TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, outputs=['tub/num_records'], run_condition='recording')
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)
    
    print("You can now go to <your pi ip address>:8887 to drive your car.")


'''
Tub management
'''
def expand_path_masks(paths):
    '''
    take a list of paths and expand any wildcards
    returns a new list of paths fully expanded
    '''
    import glob
    expanded_paths = []
    for path in paths:
        if '*' in path or '?' in path:
            mask_paths = glob.glob(path)
            expanded_paths += mask_paths
        else:
            expanded_paths.append(path)

    return expanded_paths


def gather_tub_paths(cfg, tub_names=None):
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub paths
    '''
    if tub_names:
        tub_paths = [os.path.expanduser(n) for n in tub_names.split(',')]
        return expand_path_masks(tub_paths)
    else:
        return [os.path.join(cfg.DATA_PATH, n) for n in os.listdir(cfg.DATA_PATH)]


def gather_tubs(cfg, tub_names):
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub objects initialized to each path
    '''    
    tub_paths = gather_tub_paths(cfg, tub_names)
    tubs = [Tub(p) for p in tub_paths]

    return tubs


def get_image_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[0])

def get_record_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[1].split('.')[0])

def make_key(sample):
    tub_path = sample['tub_path']
    index = sample['index']
    return tub_path + str(index)

def make_next_key(sample, index_offset):
    tub_path = sample['tub_path']
    index = sample['index'] + index_offset
    return tub_path + str(index)



def custom_train(cfg, tub_names, model_name):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    '''
    import sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.utils import shuffle
    from PIL import Image
    import json


    print("custom rnn training")

    tubs = gather_tubs(cfg, tub_names)

    records = []

    for tub in tubs:
        record_paths = glob.glob(os.path.join(tub.path, 'record_*.json'))
        print("Tub:", tub.path, "has", len(record_paths), 'records')

        record_paths.sort(key=get_record_index)
        records += record_paths


    print('collating records')
    gen_records = {}

    for record_path in records:

        with open(record_path, 'r') as fp:
            json_data = json.load(fp)

        basepath = os.path.dirname(record_path)
        image_filename = json_data["cam/image_array"]
        image_path = os.path.join(basepath, image_filename)
        sample = { 'record_path' : record_path, "image_path" : image_path, "json_data" : json_data }

        sample["tub_path"] = basepath
        sample["index"] = get_image_index(image_filename)

        angle = float(json_data['user/angle'])
        throttle = float(json_data["user/throttle"])

        sample['target_output'] = np.array([angle, throttle])

        sample['img_data'] = None

        key = make_key(sample)

        gen_records[key] = sample



    print('collating sequences')

    sequences = []

    for k, sample in gen_records.items():

        seq = []

        for i in range(SEQ_LEN):
            key = make_next_key(sample, i)
            if key in gen_records:
                seq.append(gen_records[key])
            else:
                continue

        if len(seq) != SEQ_LEN:
            continue

        sequences.append(seq)



    #shuffle and split the data
    train_data, val_data  = train_test_split(sequences, shuffle=True, test_size=(1 - cfg.TRAIN_TEST_SPLIT))


    def generator(data, batch_size=cfg.BATCH_SIZE):
        num_records = len(data)

        while True:
            #shuffle again for good measure
            shuffle(data)

            for offset in range(0, num_records, batch_size):
                batch_data = data[offset:offset+batch_size]

                if len(batch_data) != batch_size:
                    break

                b_inputs_img = []
                b_inputs_imu = []
                b_labels = []

                for seq in batch_data:
                    inputs_img = []
                    labels = []
                    for record in seq:
                        #get image data if we don't already have it
                        if record['img_data'] is None:
                            record['img_data'] = np.array(Image.open(record['image_path']))
                            
                        inputs_img.append(record['img_data'])
                    labels.append(seq[-1]['target_output'])

                    b_inputs_img.append(inputs_img)
                    b_labels.append(labels)

                #X = [np.array(b_inputs_img), np.array(b_inputs_imu)]
                X = [np.array(b_inputs_img)]
                y = np.array(b_labels).reshape(batch_size, 2)

                yield X, y

    train_gen = generator(train_data)
    val_gen = generator(val_data)

    kl = KerasRNN_LSTM(seq_length=SEQ_LEN, num_outputs=2)

    model_path = os.path.expanduser(model_name)

    total_records = len(sequences)
    total_train = len(train_data)
    total_val = len(val_data)

    print('train: %d, validation: %d' %(total_train, total_val))
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    print('steps_per_epoch', steps_per_epoch)

    kl.train(train_gen, 
        val_gen, 
        saved_model_path=model_path,
        steps=steps_per_epoch,
        train_split=cfg.TRAIN_TEST_SPLIT,
        use_early_stop = False)


class CSteeringServer(SteeringServer):

    def __init__(self, *args, **kwargs):
        super(CSteeringServer, self).__init__(*args, **kwargs)
        self.last_steering = 0.0
        self.alpha = 0.6

    def approach(self, old_val, new_val, alpha):
        return ((1.0 - alpha) * old_val) + (alpha * new_val)

    def steering_control(self, steering):
        new_steer = self.approach(self.last_steering, steering, self.alpha)
        self.last_steering = new_steer
        return new_steer

    #def throttle_control(self, last_steering, last_throttle, speed, nn_throttle):
    #    return nn_throttle * 2.0

def sim(cfg, model, top_speed=5.0):
    '''
    Start a websocket SocketIO server to talk to a donkey simulator
    '''
    import socketio
    import donkeycar as dk

    if cfg is None:
        print('no config')
        return

    kl = KerasRNN_LSTM(seq_length=SEQ_LEN, num_outputs=2)
    
    #can provide an optional image filter part
    img_stack = None

    #load keras model
    kl.load(model)  

    #start socket server framework
    sio = socketio.Server()

    top_speed = float(top_speed)

    #start sim server handler
    ss = CSteeringServer(sio, kpart=kl, top_speed=top_speed, image_part=img_stack)
            
    #register events and pass to server handlers

    @sio.on('telemetry')
    def telemetry(sid, data):
        ss.telemetry(sid, data)

    @sio.on('connect')
    def connect(sid, environ):
        ss.connect(sid, environ)

    ss.go(('0.0.0.0', 9090))

if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    
    if args['drive']:
        drive(cfg, model_path = args['--model'], use_joystick=args['--js'])

    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        cache = not args['--no_cache']
        custom_train(cfg, tub, model)

    elif args['sim']:
        model = args['--model']
        top_speed = args['--top_speed']
        sim(cfg, model, top_speed)



