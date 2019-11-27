""" 
CAR CONFIG 

This file is read by your car application's manage.py script to change the car
performance. 

EXMAPLE
-----------
import dk
cfg = dk.load_config(config_path='~/mycar/config.py')
print(cfg.CAMERA_RESOLUTION)

"""


import os

#PATHS
CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')

#VEHICLE
DRIVE_LOOP_HZ = 20
MAX_LOOPS = -1

#CAMERA
IMAGE_W = 160
IMAGE_H = 120
IMAGE_DEPTH = 3         # default RGB=3, make 1 for mono

#9865, over rides only if needed, ie. TX2..
PCA9685_I2C_ADDR = 0x40
PCA9685_I2C_BUSNUM = None

#STEERING
STEERING_CHANNEL = 1
STEERING_LEFT_PWM = 460
STEERING_RIGHT_PWM = 290

#THROTTLE
THROTTLE_CHANNEL = 0
THROTTLE_FORWARD_PWM = 500
THROTTLE_STOPPED_PWM = 370
THROTTLE_REVERSE_PWM = 220

#SOMBRERO
HAVE_SOMBRERO = False

