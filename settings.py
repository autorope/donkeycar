    
import os
from os.path import expanduser

from donkey import cameras
from donkey import recorders
from donkey import vehicles
from donkey import controllers
from donkey import whip

from donkey.predictors.base import RandomPredictor


try:
    from donkey.predictors.keras import ConvolutionPredictor
except ImportError:
    'Print could not import Keras predictors'


DRIVE_LOOP_DELAY = .1 #seconds between vehicle updates

DATA_DIR = expanduser('~/donkey_data/')
RECORDS_DIR = os.path.join(DATA_DIR, 'sessions')
MODELS_DIR = os.path.join(DATA_DIR, 'models')




''' 
Camera - Takes pictures.
'''
try:
    import picamera
    camera = cameras.PiVideoStream #Raspberry Pi Camera

except ImportError:
    print("Cound not load PiCamera. Using FakeCamera for testing.")
    FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/datasets/imgs/'
    camera = cameras.FakeCamera #For testing

CAMERA_RESOLUTION = (160,120)
#CAMERA_RESOLUTION = (340,240)

'''
Vehicle
Updates the vehicle's steering angle and throttle.
'''
vehicle = vehicles.BaseVehicle
#vehicle = vehicles.HelionConquest
#vehicle = vehicles.AdamsVehicle


'''
Recorder
Save images and vehicle variables to a filesytem or webserver
'''
recorder = recorders.FileRecorder


'''
Predictor
Accepts image arrays and returns steering angle and throttle.
'''
predictor = RandomPredictor
#predictor = ConvolutionPredictor


'''
Controller
Get the users input to control vehicle. 
'''
controller = controllers.BaseController
#controller = controllers.XboxController



'''
Connection to remote autopilot.
'''
drive_client = whip.WhipClient


'''
Server used to remotely autopilot vehicles. Not used on car.
'''
drive_server = whip.WhipServer
