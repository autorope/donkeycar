""" 
CAR CONFIG 

This file is read by your car application's manage.py script to change the car
performance. 

EXMAPLE
-----------
import dk
cfg = dk.load_config(config_path='~/d2/config.py')
print(cfg.CAMERA_RESOLUTION)

"""


import os

#PATHS
CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')

#VEHICLE
DRIVE_LOOP_HZ = 20
MAX_LOOPS = 100000

#CAMERA
CAMERA_RESOLUTION = (120, 160) #(height, width)
CAMERA_FRAMERATE = DRIVE_LOOP_HZ

#STEERING
STEERING_CHANNEL = 1
STEERING_LEFT_PWM =  410 #420
STEERING_RIGHT_PWM = 310 #360

#THROTTLE
THROTTLE_CHANNEL = 0
THROTTLE_FORWARD_PWM = 400
THROTTLE_STOPPED_PWM = 360
THROTTLE_REVERSE_PWM = 330 # 310

#TRAINING
BATCH_SIZE = 128
TRAIN_TEST_SPLIT = 0.8


#JOYSTICK
USE_JOYSTICK_AS_DEFAULT = False
JOYSTICK_MAX_THROTTLE = 0.25
JOYSTICK_STEERING_SCALE = 1.0
AUTO_RECORD_ON_THROTTLE = True


AUTO_RECORD_ON_THROTTLE = True

#RC Controller (2-channel stock controller for now) - alpha!! 2018-01-02
USE_RC_CONTROLLER   = False
RC_MAX_THROTTLE     = 1.00
# RC_STEERING_SCALE: +1 or -1 depending on transmitter. On mine I needed -1 to map 'right turn'
# on controller to 'right turn' on Donky
RC_STEERING_SCALE   = -1
# these are determined emperically based on your controller and car. Drive your car and run
# raw_pulse_feed.py. Once you have your steering and throttle trim set on the controller,
# make a note of the numbers listed. It's listed [throttle,steering]. This will be your 'center' value
# RC_HIGH is maximum value at full, forward throttle & full Left/Right  (depends on controller)
# RC_LOW is minimum value at full reverse throttle & full Right/Left (depends on controller)
# RC_DEAD is how much tollerance you want at 'center' in order to consider it 'stopped' or
# steering angle = 0, RC_TOLERANCE allows over HIGH and under LOW values to be clampped to LOW or HIGH
# without throwing an error.
RC_CENTER = [1400,1350]
RC_LOW    = [800, 850]
RC_HIGH   = [1950,1930]
RC_DEAD   = 15
RC_TOLERANCE = 100