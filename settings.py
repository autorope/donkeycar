
import cameras
import recorders
import predictors
import vehicles


from os.path import expanduser


#ENV='pi'
ENV='laptop'

LOOP_DELAY = 3 #seconds between vehicle updates

#CAMERA
try:
    cam = cameras.Camera() #Raspberry Pi Camera
except ImportError:
    print("Cound not load PiCamera. Trying FakeCamera for testing.")
    cam = cameras.FakeCamera() #For testing


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

global angle_manual
global speed_manual
angle_manual = 0
speed_manual = 0 







#WHIP (remote service)
BASE_URL='http://localhost:8888/'
