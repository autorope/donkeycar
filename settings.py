
from donkey import cameras
import recorders
import predictors
import vehicles

import os
from os.path import expanduser


#ENV='pi'
ENV='laptop'

LOOP_DELAY = 1 #seconds between vehicle updates

#CAMERA
try:
    cam = cameras.PiVideoStream() #Raspberry Pi Camera
except ImportError:
    print("Cound not load PiCamera. Trying FakeCamera for testing.")
    cam = cameras.FakeCamera() #For testing
    FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'



#VEHICLE
#What's used to change update the vehicle's steering angle and throttle.
vehicle = vehicles.BaseVehicle()
car_connected=True

#RECORDER
DATA_DIR = '~/donkey_data/'
recorder = recorders.FileRecorder()


#predictor
predictor = predictors.BasePredictor()




#WEBSERVER CONTROL
#Global vars used to control the vehicle from the webserver.
use_webserver = True



