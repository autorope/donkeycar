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

#donkey name. This should be unique across the shared mqtt broker
DONKEY_UNIQUE_NAME = 'my_robot1234'

#pi information
PI_USERNAME = "pi"
PI_PASSWD = "raspberry"
PI_HOSTNAME = "raspberrypi.local"
PI_DONKEY_ROOT = "/home/pi/mycar"

#PATHS
CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')

#VEHICLE
DRIVE_LOOP_HZ = 20
MAX_LOOPS = 100000

#CAMERA
CAMERA_TYPE = "PICAM"   # (PICAM|WEBCAM|CVCAM|MOCK)
IMAGE_W = 160
IMAGE_H = 120
IMAGE_DEPTH = 3         # default RGB=3, make 1 for mono
CAMERA_FRAMERATE = DRIVE_LOOP_HZ

#9865, over rides only if needed, ie. TX2..
PCA9685_I2C_ADDR = 0x40
PCA9685_I2C_BUSNUM = None

#drivetrain
DRIVE_TRAIN_TYPE = "SERVO_ESC" # SERVO_ESC|DC_STEER_THROTTLE|DC_TWO_WHEEL|SERVO_HBRIDGE_PWM

#STEERING
STEERING_CHANNEL = 1
STEERING_LEFT_PWM = 460
STEERING_RIGHT_PWM = 290

#THROTTLE
THROTTLE_CHANNEL = 0
THROTTLE_FORWARD_PWM = 500
THROTTLE_STOPPED_PWM = 370
THROTTLE_REVERSE_PWM = 220

#DC_STEER_THROTTLE with one motor as steering, one as drive
HBRIDGE_PIN_LEFT = 18
HBRIDGE_PIN_RIGHT = 16
HBRIDGE_PIN_FWD = 15
HBRIDGE_PIN_BWD = 13

#DC_TWO_WHEEL - with two wheels as drive, left and right.
HBRIDGE_PIN_LEFT_FWD = 18
HBRIDGE_PIN_LEFT_BWD = 16
HBRIDGE_PIN_RIGHT_FWD = 15
HBRIDGE_PIN_RIGHT_BWD = 13

#TRAINING
DEFAULT_MODEL_TYPE = 'linear' #(linear|categorical|rnn|imu|behavior|3d|localizer|latent)
BATCH_SIZE = 128
TRAIN_TEST_SPLIT = 0.8
MAX_EPOCHS = 100
SHOW_PLOT = True
VEBOSE_TRAIN = True
USE_EARLY_STOP = True
EARLY_STOP_PATIENCE = 5
MIN_DELTA = .0005
PRINT_MODEL_SUMMARY = True      #print layers and weights to stdout
OPTIMIZER = None                #adam, sgd, rmsprop, etc.. None accepts default
LEARNING_RATE = 0.001           #only used when OPTIMIZER specified
LEARNING_RATE_DECAY = 0.0       #only used when OPTIMIZER specified
SEND_BEST_MODEL_TO_PI = False   #change to true to automatically send best model during training
CACHE_IMAGES = True             #keep images in memory. will speed succesive epochs, but crater if not enough mem.
PRUNE_CNN = False
PRUNE_PERCENT_TARGET = 75 # The desired percentage of pruning.
PRUNE_PERCENT_PER_ITERATION = 20 # Percenge of pruning that is perform per iteration.
PRUNE_VAL_LOSS_DEGRADATION_LIMIT = 0.2 # The max amout of validation loss that is permitted during pruning.
PRUNE_EVAL_PERCENT_OF_DATASET = .05  # percent of dataset used to perform evaluation of model.

# Region of interst cropping
# only supported in Categorical and Linear models.
ROI_CROP_TOP = 0
ROI_CROP_BOTTOM = 0

#model transfer options
FREEZE_LAYERS = False
NUM_LAST_LAYERS_TO_TRAIN = 7

#JOYSTICK
USE_JOYSTICK_AS_DEFAULT = False
JOYSTICK_MAX_THROTTLE = 0.3
JOYSTICK_STEERING_SCALE = 1.0
AUTO_RECORD_ON_THROTTLE = True
CONTROLLER_TYPE='ps3'           #(ps3|ps4|xbox|nimbus|wiiu|F710)
USE_NETWORKED_JS = False
NETWORK_JS_SERVER_IP = "192.168.0.1"
JOYSTICK_DEADZONE = 0.0         # when non zero, this is the smallest throttle before recording triggered.

#For the categorical model, this limits the upper bound of the learned throttle
#it's very IMPORTANT that this value is matched from the training PC config.py and the robot.py
#and ideally wouldn't change once set.
MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.5

#RNN or 3D
SEQUENCE_LENGTH = 3

#IMU
HAVE_IMU = False

#SOMBRERO
HAVE_SOMBRERO = False

#RECORD OPTIONS
RECORD_DURING_AI = False

#LED
HAVE_RGB_LED = False
LED_INVERT = False              #COMMON ANNODE?

#board pin number for pwm outputs
LED_PIN_R = 12
LED_PIN_G = 10
LED_PIN_B = 16

#LED status color, 0-100
LED_R = 0
LED_G = 0
LED_B = 1

#LED Color for record count indicator
REC_COUNT_ALERT = 1000  #how many records before blinking alert
REC_COUNT_ALERT_CYC = 15 #how many cycles of 1/20 of a second to blink per REC_COUNT_ALERT records
REC_COUNT_ALERT_BLINK_RATE = 0.4 #how fast to blink the led in seconds on/off

#first number is record count, second tuple is color ( r, g, b) (0-100)
#when record count exceeds that number, the color will be used
RECORD_ALERT_COLOR_ARR = [ (0, (1, 1, 1)),
            (3000, (5, 5, 5)),
            (5000, (5, 2, 0)),
            (10000, (0, 5, 0)),
            (15000, (0, 5, 5)),
            (20000, (0, 0, 5)), ]


#LED status color, 0-100, for model reloaded alert
MODEL_RELOADED_LED_R = 100
MODEL_RELOADED_LED_G = 0
MODEL_RELOADED_LED_B = 0


#BEHAVIORS
TRAIN_BEHAVIORS = False
BEHAVIOR_LIST = ['Left_Lane', "Right_Lane"]
BEHAVIOR_LED_COLORS =[ (0, 10, 0), (10, 0, 0) ] #RGB tuples 0-100 per chanel

TRAIN_LOCALIZER = False
BUTTON_PRESS_NEW_TUB = False #should we make a new tub on each X button press?

#in donkey gym env?
DONKEY_GYM = False
DONKEY_SIM_PATH = "path to sim" #"/home/tkramer/projects/sdsandbox/sdsim/build/DonkeySimLinux/donkey_sim.x86_64"
DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0" # "donkey-generated-track-v0" "donkey-generated-roads-v0" "donkey-warehouse-v0" "donkey-avc-sparkfun-v0"

#publish camera over network
PUB_CAMERA_IMAGES = False

#meta data. Strings describing location and/or task
DRIVE_LOCATION = None
DRIVE_TASK = None

#to give the ai a boost, configure these values to
AI_LAUNCH_DURATION = 0.0
AI_LAUNCH_THROTTLE = 0.0
AI_LAUNCH_ENABLE_BUTTON = 'R2'
#scale the output of the throttle of the ai pilot for all model types.
AI_THROTTLE_MULT = 1.0

#path following
PATH_FILENAME = "donkey_path.pkl"
PATH_SCALE = 5.0
PATH_OFFSET = (0, 0)
PATH_MIN_DIST = 0.3
PID_P = -10.0
PID_I = 0.000
PID_D = -0.2
PID_THROTTLE = 0.2
SAVE_PATH_BTN = "cross"
RESET_ORIGIN_BTN = "triangle"