#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car

Usage:
    manage.py (drive) [--model=<model>] [--js] [--type=(linear|categorical|rnn|imu|behavior|3d)] [--camera=(single|stereo)]
    manage.py (train) [--tub=<tub1,tub2,..tubn>] (--model=<model>) [--transfer=<model>] [--type=(linear|categorical|rnn|imu|behavior|3d)] [--continuous] [--aug]


Options:
    -h --help     Show this screen.
    --js          Use physical joystick.
"""
import os
from docopt import docopt

import donkeycar as dk

#import parts
from donkeycar.parts.transform import Lambda
from donkeycar.parts.keras import KerasIMU, KerasCategorical, KerasBehavioral, KerasLinear
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.datastore import TubHandler, TubGroup
from donkeycar.parts.controller import LocalWebController, JoystickController
from donkeycar.parts.imu import Mpu6050
import numpy as np
from donkeycar.parts.throttle_filter import ThrottleFilter

class BehaviorPart(object):
    '''
    Keep a list of states, and an active state. Keep track of switching.
    And return active state information.
    '''
    def __init__(self, states):
        '''
        expects a list of strings to enumerate state
        '''
        print("bvh states:", states)
        self.states = states
        self.active_state = 0
        self.one_hot_state_array = []
        for i in range(len(states)):
            self.one_hot_state_array.append(0.0)
        self.one_hot_state_array[0] = 1.0

    def increment_state(self):
        self.one_hot_state_array[self.active_state] = 0.0
        self.active_state += 1
        if self.active_state >= len(self.states):
            self.active_state = 0
        self.one_hot_state_array[self.active_state] = 1.0
        print("In State:", self.states[self.active_state])

    def decrement_state(self):
        self.one_hot_state_array[self.active_state] = 0.0
        self.active_state -= 1
        if self.active_state < 0:
            self.active_state = len(self.states) - 1
        self.one_hot_state_array[self.active_state] = 1.0
        print("In State:", self.states[self.active_state])

    def set_state(self, iState):
        self.one_hot_state_array[self.active_state] = 0.0
        self.active_state = iState
        self.one_hot_state_array[self.active_state] = 1.0
        print("In State:", self.states[self.active_state])

    def run(self):
        return self.active_state, self.states[self.active_state], self.one_hot_state_array

    def shutdown(self):
        pass

def drive(cfg, model_path=None, use_joystick=False, model_type=None, camera_type='single'):
    '''
    Construct a working robotic vehicle from many parts.
    Each part runs as a job in the Vehicle loop, calling either
    it's run or run_threaded method depending on the constructor flag `threaded`.
    All parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely manner.
    Parts may have named outputs and inputs. The framework handles passing named outputs
    to parts requesting the same named input.
    '''

    if model_type is None:
        model_type = "categorical"

    stereo_cam = camera_type == "stereo"
    
    #Initialize car
    V = dk.vehicle.Vehicle()

    if stereo_cam:
        from donkeycar.parts.camera import Webcam

        camA = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, iCam = 0)
        V.add(camA, outputs=['cam/image_array_a'], threaded=True)

        camB = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, iCam = 1)
        V.add(camB, outputs=['cam/image_array_b'], threaded=True)

        def stereo_pair(image_a, image_b):
            if image_a is not None and image_b is not None:
                width, height, _ = image_a.shape
                grey_a = dk.utils.rgb2gray(image_a)
                grey_b = dk.utils.rgb2gray(image_b)
                grey_c = grey_a - grey_b
                
                stereo_image = np.zeros([width, height, 3], dtype=np.dtype('B'))
                stereo_image[...,0] = np.reshape(grey_a, (width, height))
                stereo_image[...,1] = np.reshape(grey_b, (width, height))
                stereo_image[...,2] = np.reshape(grey_c, (width, height))
            else:
                stereo_image = []

            return np.array(stereo_image)

        image_sterero_pair_part = Lambda(stereo_pair)
        V.add(image_sterero_pair_part, inputs=['cam/image_array_a', 'cam/image_array_b'], 
            outputs=['cam/image_array'])

    else:
        
        print("cfg.CAMERA_TYPE", cfg.CAMERA_TYPE)
        if cfg.CAMERA_TYPE == "PICAM":
            from donkeycar.parts.camera import PiCamera
            cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H)
        elif cfg.CAMERA_TYPE == "WEBCAM":
            from donkeycar.parts.camera import Webcam
            cam = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H)
            
        V.add(cam, outputs=['cam/image_array'], threaded=True)
        
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        #modify max_throttle closer to 1.0 to have more power
        #modify steering_scale lower than 1.0 to have less responsive steering
        ctr = JoystickController(throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
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

    #this throttle filter will allow one tap back for esc reverse
    th_filter = ThrottleFilter()
    V.add(th_filter, inputs=['user/throttle'], outputs=['user/throttle'])
    
    #See if we should even run the pilot module. 
    #This is only needed because the part run_condition only accepts boolean
    def pilot_condition(mode):
        if mode == 'user':
            return False
        else:
            return True
        
    pilot_condition_part = Lambda(pilot_condition)
    V.add(pilot_condition_part, inputs=['user/mode'], outputs=['run_pilot'])
    
    def led_cond(mode, recording, num_records, behavior_state):
        '''
        returns a blink rate. 0 for off. -1 for on. positive for rate.
        '''

        if num_records is not None and num_records % 10 == 0:
            print("recorded", num_records, "records")

        if behavior_state is not None and model_type == 'behavior':
            r, g, b = cfg.BEHAVIOR_LED_COLORS[behavior_state]
            led.set_rgb(r, g, b)
            return -1 #solid on

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
    V.add(led_cond_part, inputs=['user/mode', 'recording', "tub/num_records", 'behavior/state'], outputs=['led/blink_rate'])

    if cfg.HAVE_RGB_LED:
        from donkeycar.parts.led_status import RGB_LED
        led = RGB_LED(cfg.LED_PIN_R, cfg.LED_PIN_G, cfg.LED_PIN_B, cfg.LED_INVERT)
        led.set_rgb(cfg.LED_R, cfg.LED_G, cfg.LED_B)
        V.add(led, inputs=['led/blink_rate'])

    #IMU
    if cfg.HAVE_IMU:
        imu = Mpu6050()
        V.add(imu, outputs=['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z'], threaded=True)

    #Behavioral state
    if model_type == "behavior":
        bh = BehaviorPart(cfg.BEHAVIOR_LIST)
        V.add(bh, outputs=['behavior/state', 'behavior/label', "behavior/one_hot_state_array"])
        try:
            ctr.set_button_down_trigger('L1', bh.increment_state)
        except:
            pass

        kl = KerasBehavioral(num_outputs=2, num_behavior_inputs=len(cfg.BEHAVIOR_LIST))
        inputs = ['cam/image_array', "behavior/one_hot_state_array"]  
    #IMU
    elif model_type == "imu":
        assert(cfg.HAVE_IMU)
        #Run the pilot if the mode is not user.
        kl = KerasIMU(num_outputs=2, num_imu_inputs=6)
        inputs=['cam/image_array',
            'imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z']
    else:
        if model_type == "linear":
            kl = KerasLinear()
        elif model_type == "3d":
            kl = Keras3D_CNN(seq_length=cfg.SEQUENCE_LENGTH)
        elif model_type == "rnn":
            kl = KerasRNN_LSTM(seq_length=cfg.SEQUENCE_LENGTH)
        else:
            kl = KerasCategorical()

        inputs=['cam/image_array']

    if model_path:
        kl.load(model_path)
    
    V.add(kl, inputs=inputs, 
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
    
    
    steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
    steering = PWMSteering(controller=steering_controller,
                                    left_pulse=cfg.STEERING_LEFT_PWM, 
                                    right_pulse=cfg.STEERING_RIGHT_PWM)
    
    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
    throttle = PWMThrottle(controller=throttle_controller,
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

    if cfg.TRAIN_BEHAVIORS:
        inputs += ['behavior/state', 'behavior/label', "behavior/one_hot_state_array"]
        types += ['int', 'str', 'vector']
    
    if cfg.HAVE_IMU:
        inputs += ['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z']

        types +=['float', 'float', 'float',
           'float', 'float', 'float']
    
    th = TubHandler(path=cfg.DATA_PATH)
    tub = th.new_tub_writer(inputs=inputs, types=types)
    V.add(tub, inputs=inputs, outputs=["tub/num_records"], run_condition='recording')

    if type(ctr) is LocalWebController:
        print("You can now go to <your pi ip address>:8887 to drive your car.")
    elif type(ctr) is JoystickController:
        print("You can now move your joystick to drive your car.")
        #tell the controller about the tub        
        ctr.set_tub(tub)

    #run the vehicle for 20 seconds
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
            max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    
    if args['drive']:
        model_type = args['--type']
        camera_type = args['--camera']
        drive(cfg, model_path = args['--model'], use_joystick=args['--js'], model_type=model_type, camera_type=camera_type)
    
    if args['train']:
        from train import multi_train
        
        tub = args['--tub']
        model = args['--model']
        transfer = args['--transfer']
        model_type = args['--type']
        continuous = args['--continuous']
        aug = args['--aug']     
        multi_train(cfg, tub, model, transfer, model_type, continuous, aug)



