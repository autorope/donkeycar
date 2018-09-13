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
import time
from docopt import docopt

import donkeycar as dk

#import parts
from donkeycar.parts.transform import Lambda
from donkeycar.parts.datastore import TubHandler, TubGroup
from donkeycar.parts.controller import LocalWebController, JoystickController
from donkeycar.parts.imu import Mpu6050
import numpy as np
from donkeycar.parts.throttle_filter import ThrottleFilter
from donkeycar.parts.behavior import BehaviorPart
from donkeycar.parts.file_watcher import FileWatcher

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
        if cfg.TRAIN_BEHAVIORS:
            model_type = "behavior"
        else:
            model_type = "categorical"
    
    #Initialize car
    V = dk.vehicle.Vehicle()

    if camera_type == "stereo":

        if cfg.CAMERA_TYPE == "WEBCAM":
            from donkeycar.parts.camera import Webcam            

            camA = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 0)
            camB = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 1)

        elif cfg.CAMERA_TYPE == "CVCAM":
            from donkeycar.parts.cv import CvCam

            camA = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 0)
            camB = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 1)
        else:
            raise(Exception("Unsupported camera type: %s" % cfg.CAMERA_TYPE))

        V.add(camA, outputs=['cam/image_array_a'], threaded=True)
        V.add(camB, outputs=['cam/image_array_b'], threaded=True)

        def stereo_pair(image_a, image_b):
            '''
            This will take the two images and combine them into a single image
            One in red, the other in green, and diff in blue channel.
            '''
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
            cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        elif cfg.CAMERA_TYPE == "WEBCAM":
            from donkeycar.parts.camera import Webcam
            cam = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        elif cfg.CAMERA_TYPE == "CVCAM":
            from donkeycar.parts.cv import CvCam
            cam = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        else:
            raise(Exception("Unkown camera type: %s" % cfg.CAMERA_TYPE))
            
        V.add(cam, outputs=['cam/image_array'], threaded=True)
        
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        #modify max_throttle closer to 1.0 to have more power
        #modify steering_scale lower than 1.0 to have less responsive steering
        from donkeycar.parts.controller import PS3JoystickController, PS4JoystickController
        
        cont_class = PS3JoystickController

        if cfg.CONTROLLER_TYPE == "ps4":
            cont_class = PS4JoystickController

        ctr = cont_class(throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
                                 steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                 auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)

        if cfg.USE_NETWORKED_JS:
            from donkeycar.parts.controller import JoyStickSub
            netwkJs = JoyStickSub(cfg.NETWORK_JS_SERVER_IP)
            V.add(netwkJs, threaded=True)
            ctr.js = netwkJs

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
    
    def led_cond(mode, recording, recording_alert, behavior_state, reloaded_model):
        #returns a blink rate. 0 for off. -1 for on. positive for rate.
        
        if reloaded_model:
            led.set_rgb(cfg.MODEL_RELOADED_LED_R, cfg.MODEL_RELOADED_LED_G, cfg.MODEL_RELOADED_LED_B)
            return 0.1
        else:
            led.set_rgb(cfg.LED_R, cfg.LED_G, cfg.LED_B)

        if recording_alert:
            led.set_rgb(*recording_alert)
            return cfg.REC_COUNT_ALERT_BLINK_RATE
        else:
            led.set_rgb(cfg.LED_R, cfg.LED_G, cfg.LED_B)
    
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

    if cfg.HAVE_RGB_LED:
        from donkeycar.parts.led_status import RGB_LED
        led = RGB_LED(cfg.LED_PIN_R, cfg.LED_PIN_G, cfg.LED_PIN_B, cfg.LED_INVERT)
        led.set_rgb(cfg.LED_R, cfg.LED_G, cfg.LED_B)
        
        led_cond_part = Lambda(led_cond)
        V.add(led_cond_part, inputs=['user/mode', 'recording', "records/alert", 'behavior/state', 'reloaded/model'],
              outputs=['led/blink_rate'])

        V.add(led, inputs=['led/blink_rate'])
        

    def get_record_alert_color(num_records):
        col = (0, 0, 0)
        for count, color in cfg.RECORD_ALERT_COLOR_ARR:
            if num_records >= count:
                col = color
        return col    

    def record_tracker(num_records):

        if num_records is None:
            return 0
        
        if record_tracker.last_num_rec_print != num_records or record_tracker.force_alert:
            record_tracker.last_num_rec_print = num_records

            if num_records % 10 == 0:
                print("recorded", num_records, "records")
                    
            if num_records % cfg.REC_COUNT_ALERT == 0 or record_tracker.force_alert:
                record_tracker.dur_alert = num_records // cfg.REC_COUNT_ALERT * cfg.REC_COUNT_ALERT_CYC
                record_tracker.force_alert = 0
                
        if record_tracker.dur_alert > 0:
            record_tracker.dur_alert -= 1

        if record_tracker.dur_alert != 0:
            return get_record_alert_color(num_records)

        return 0   

    record_tracker.last_num_rec_print = 0
    record_tracker.dur_alert = 0
    record_tracker.force_alert = 0
    rec_tracker_part = Lambda(record_tracker)
    V.add(rec_tracker_part, inputs=["tub/num_records"], outputs=['records/alert'])

    if cfg.AUTO_RECORD_ON_THROTTLE and isinstance(ctr, JoystickController):
        #then we are not using the circle button. hijack that to force a record count indication
        def show_record_acount_status():
            record_tracker.last_num_rec_print = 0
            record_tracker.force_alert = 1
        ctr.set_button_down_trigger('circle', show_record_acount_status)

    #IMU
    if cfg.HAVE_IMU:
        imu = Mpu6050()
        V.add(imu, outputs=['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z'], threaded=True)

    #Behavioral state
    if cfg.TRAIN_BEHAVIORS:
        bh = BehaviorPart(cfg.BEHAVIOR_LIST)
        V.add(bh, outputs=['behavior/state', 'behavior/label', "behavior/one_hot_state_array"])
        try:
            ctr.set_button_down_trigger('L1', bh.increment_state)
        except:
            pass

        inputs = ['cam/image_array', "behavior/one_hot_state_array"]  
    #IMU
    elif model_type == "imu":
        assert(cfg.HAVE_IMU)
        #Run the pilot if the mode is not user.
        inputs=['cam/image_array',
            'imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z']
    else:
        inputs=['cam/image_array']

    def load_model(kl, model_path):
        start = time.time()
        try:
            print('loading model', model_path)
            kl.load(model_path)
            print('finished loading in %s sec.' % (str(time.time() - start)) )
        except:
            print('problems loading model', model_path)

    def load_weights(kl, weights_path):
        start = time.time()
        try:
            print('loading model weights', weights_path)
            kl.model.load_weights(weights_path)
            print('finished loading in %s sec.' % (str(time.time() - start)) )
        except:
            print('problems loading weights', weights_path)

    def load_model_json(kl, json_fnm):
        start = time.time()
        print('loading model json', json_fnm)
        import keras
        with open(json_fnm, 'r') as handle:
            contents = handle.read()
            kl.model = keras.models.model_from_json(contents)
        print('finished loading json in %s sec.' % (str(time.time() - start)) )

    if model_path:
        #When we have a model, first create an appropriate Keras part
        kl = dk.utils.get_model_by_type(model_type, cfg)

        if '.h5' in model_path:
            #when we have a .h5 extension
            #load everything from the model file
            load_model(kl, model_path)

            def reload_model(filename):
                print(filename, "was changed!")
                load_model(kl, filename)

            fw_part = FileWatcher(model_path, reload_model, wait_for_write_stop=10.0)
            V.add(fw_part, outputs=['reloaded/model'])

        elif '.json' in model_path:
            #when we have a .json extension
            #load the model from their and look for a matching
            #.wts file with just weights
            load_model_json(kl, model_path)
            weights_path = model_path.replace('.json', '.weights')
            load_weights(kl, weights_path)

            def reload_weights(filename):
                print(filename, "was changed!")
                weights_path = filename.replace('.json', '.weights')
                load_weights(kl, weights_path)
            
            fw_part = FileWatcher(model_path, reload_weights, wait_for_write_stop=1.0)
            V.add(fw_part, outputs=['reloaded/model'])

        else:
            #previous default behavior
            load_model(kl, model_path)
    
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
    
    #Drive train setup
    
    if cfg.DRIVE_TRAIN_TYPE == "SERVO_ESC":
        from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle

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
    

    elif cfg.DRIVE_TRAIN_TYPE == "DC_STEER_THROTTLE":
        from donkeycar.parts.actuator import Mini_HBridge_DC_Motor_PWM
        
        steering = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_LEFT, cfg.HBRIDGE_PIN_RIGHT)
        throttle = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_FWD, cfg.HBRIDGE_PIN_BWD)

        V.add(steering, inputs=['angle'])
        V.add(throttle, inputs=['throttle'])
    

    elif cfg.DRIVE_TRAIN_TYPE == "DC_TWO_WHEEL":
        from donkeycar.parts.actuator import TwoWheelSteeringThrottle, Mini_HBridge_DC_Motor_PWM

        left_motor = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_LEFT_FWD, cfg.HBRIDGE_PIN_LEFT_BWD)
        right_motor = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_RIGHT_FWD, cfg.HBRIDGE_PIN_RIGHT_BWD)
        two_wheel_control = TwoWheelSteeringThrottle()

        V.add(two_wheel_control, 
                inputs=['throttle', 'angle'],
                outputs=['left_motor_speed', 'right_motor_speed'])

        V.add(left_motor, inputs=['left_motor_speed'])
        V.add(right_motor, inputs=['right_motor_speed'])

    elif cfg.DRIVE_TRAIN_TYPE == "SERVO_HBRIDGE_PWM":
        from donkeycar.parts.actuator import ServoBlaster, PWMSteering
        steering_controller = ServoBlaster(cfg.STEERING_CHANNEL) #really pin
        #PWM pulse values should be in the range of 100 to 200
        assert(cfg.STEERING_LEFT_PWM <= 200)
        assert(cfg.STEERING_RIGHT_PWM <= 200)
        steering = PWMSteering(controller=steering_controller,
                                        left_pulse=cfg.STEERING_LEFT_PWM, 
                                        right_pulse=cfg.STEERING_RIGHT_PWM)
       

        from donkeycar.parts.actuator import Mini_HBridge_DC_Motor_PWM
        motor = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_FWD, cfg.HBRIDGE_PIN_BWD)

        V.add(steering, inputs=['angle'])
        V.add(motor, inputs=["throttle"])
    
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
    elif isinstance(ctr, JoystickController):
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



