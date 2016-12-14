
from donkey import cameras
from donkey import recorders
from donkey import predictors
from donkey import vehicles
from donkey import webcontroller

import os
from os.path import expanduser


DRIVE_LOOP_DELAY = 1 #seconds between vehicle updates

''' 
Camera - Takes pictures.
'''
try:
    camera = cameras.PiVideoStream() #Raspberry Pi Camera
except ImportError:
    print("Cound not load PiCamera. Trying FakeCamera for testing.")
    FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'
    camera = cameras.FakeCamera() #For testing


'''
Vehicle - Updates the vehicle's steering angle and throttle.
'''
vehicle = vehicles.BaseVehicle()


''' 
Recorder - Save images and vehicle variables to a filesytem or webserver
'''
DATA_DIR = '~/donkey_data/'
recorder = recorders.FileRecorder()


'''
Predictor - Accepts image and returns steering angle and throttle.
'''
predictor = predictors.RandomPredictor()


'''
Controller - Get the users input to control vehicle. 
'''
controller = webcontroller.Controller()


'''
GLOBAL

angle and speed variables that are set by
the controller and accessed in the drive_loop.
'''

global angle_manual
global speed_manual
angle_manual = 0
speed_manual = 0 