#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it. 

Usage:
    car.py (drive) [--model=<model>]
    car.py (train) [--tub=<tub1,tub2,..tubn>] (--model=<model>)
    car.py (calibrate) 
"""


import os
from docopt import docopt
import donkeycar as dk 
from PIL import Image
import numpy as np
import cv2

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')


def drive(model_path=None):
    #Initialized car
    V = dk.vehicle.Vehicle()
    #cam = dk.parts.PiCamera()
    cam = dk.parts.ImageListCamera()
    
    V.add(cam, outputs=['cam/image_array'], threaded=True)
    
    img_fifo = dk.parts.ImgFIFO()
    V.add(img_fifo, inputs=['cam/image_array'],
        outputs=['pipeline/image_fifo'])
    
    
    ctr = dk.parts.LocalWebController()
    V.add(ctr, 
          inputs=['pipeline/image_fifo'],
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
    
    '''
    steering_controller = dk.parts.MockController()
    steering = dk.parts.PWMSteering(controller=steering_controller,
                                    left_pulse=460, right_pulse=260)
                                    
    
    throttle_controller = dk.parts.MockController()
    throttle = dk.parts.PWMThrottle(controller=throttle_controller,
                                    max_pulse=500, zero_pulse=370, min_pulse=220)
                                    
    '''
    steering = dk.parts.MockController()
    throttle = dk.parts.MockController()
    
    '''
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
    
    th = dk.parts.TubHandler(path=DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')
    '''
    
    #run the vehicle for 20 seconds
    V.start(rate_hz=20, max_loop_count=100000)
    
    print("You can now go to <your pi ip address>:8887 to drive your car.")

class TubImageStacker(dk.parts.Tub):
    '''
    A Tub to try out training against images that are saved out in the normal format, not the one created above.
    If you drive with the image fifo part, then you don't need to do any extra work on the training. Just make
    sure your inference pass also sees the same fifo image.
    '''
    
    def stack3Images(self, img_a, img_b, img_c):
        '''
        convert 3 rgb images into grayscale and put them into the 3 channels of
        a single output image
        '''
        width, height, _ = img_a.shape

        gray_a = cv2.cvtColor(img_a, cv2.COLOR_RGB2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_RGB2GRAY)
        gray_c = cv2.cvtColor(img_c, cv2.COLOR_RGB2GRAY)
        
        img_arr = np.zeros([width, height, 3], dtype=np.dtype('B'))

        img_arr[...,0] = np.reshape(gray_a, (width, height))
        img_arr[...,1] = np.reshape(gray_b, (width, height))
        img_arr[...,2] = np.reshape(gray_c, (width, height))

        return img_arr

    def get_record(self, ix):
        '''
        get the current record and two previous.
        stack the 3 images into a single image.
        '''
        data = super(TubImageStacker, self).get_record(ix)

        if ix > 1:
            data_ch1 = super(TubImageStacker, self).get_record(ix - 1)
            data_ch0 = super(TubImageStacker, self).get_record(ix - 2)

            json_data = self.get_json_record(ix)
            for key, val in json_data.items():
                typ = self.get_input_type(key)

                #load objects that were saved as separate files
                if typ == 'image':
                    val = self.stack3Images(data_ch0[key], data_ch0[key], data[key])
                    data[key] = val
                elif typ == 'image_array':
                    img = self.stack3Images(data_ch0[key], data_ch0[key], data[key])
                    val = np.array(img)

        return data


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
    tubs = [TubImageStacker(p) for p in tub_paths]

    gens = [tub.train_val_gen(X_keys, y_keys, record_transform=rt, batch_size=128) for tub in tubs]
    train_gens = [gen[0] for gen in gens]
    val_gens = [gen[1] for gen in gens]

    model_path = os.path.join(MODELS_PATH, model_name)
    kl.train(combined_gen(train_gens), combined_gen(val_gens), saved_model_path=model_path)




def calibrate():
    channel = int(input('Enter the channel your actuator uses (0-15).'))
    c = dk.parts.PCA9685(channel)
    
    for i in range(10):
        pmw = int(input('Enter a PWM setting to test(100-600)'))
        c.run(pmw)


if __name__ == '__main__':
    args = docopt(__doc__)

    if args['drive']:
        drive(model_path = args['--model'])
    elif args['calibrate']:
        calibrate()
    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(tub, model)




