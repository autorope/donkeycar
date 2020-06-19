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
DRIVE_LOOP_HZ = 20      # the vehicle loop will pause if faster than this speed.
MAX_LOOPS = None        # the vehicle loop can abort after this many iterations, when given a positive integer.

#CAMERA
CAMERA_TYPE = "PICAM"   # (PICAM|WEBCAM|CVCAM|CSIC|V4L|D435|MOCK|IMAGE_LIST)
IMAGE_W = 160
IMAGE_H = 120
IMAGE_DEPTH = 3         # default RGB=3, make 1 for mono
CAMERA_FRAMERATE = DRIVE_LOOP_HZ
CAMERA_VFLIP = False
CAMERA_HFLIP = False
# For CSIC camera - If the camera is mounted in a rotated position, changing the below parameter will correct the output frame orientation
CSIC_CAM_GSTREAMER_FLIP_PARM = 0 # (0 => none , 4 => Flip horizontally, 6 => Flip vertically)

# For IMAGE_LIST camera
# PATH_MASK = "~/mycar/data/tub_1_20-03-12/*.jpg"

#9865, over rides only if needed, ie. TX2..
PCA9685_I2C_ADDR = 0x40     #I2C address, use i2cdetect to validate this number
PCA9685_I2C_BUSNUM = None   #None will auto detect, which is fine on the pi. But other platforms should specify the bus num.

#SSD1306_128_32
USE_SSD1306_128_32 = False    # Enable the SSD_1306 OLED Display
SSD1306_128_32_I2C_BUSNUM = 1 # I2C bus number

#DRIVETRAIN
#These options specify which chasis and motor setup you are using. Most are using SERVO_ESC.
#DC_STEER_THROTTLE uses HBridge pwm to control one steering dc motor, and one drive wheel motor
#DC_TWO_WHEEL uses HBridge pwm to control two drive motors, one on the left, and one on the right.
#SERVO_HBRIDGE_PWM use ServoBlaster to output pwm control from the PiZero directly to control steering, and HBridge for a drive motor.
#PIGPIO_PWM uses Raspberrys internal PWM
DRIVE_TRAIN_TYPE = "SERVO_ESC" # SERVO_ESC|DC_STEER_THROTTLE|DC_TWO_WHEEL|SERVO_HBRIDGE_PWM|PIGPIO_PWM|MM1|MOCK

#STEERING
STEERING_CHANNEL = 1            #channel on the 9685 pwm board 0-15
STEERING_LEFT_PWM = 460         #pwm value for full left steering
STEERING_RIGHT_PWM = 290        #pwm value for full right steering

#STEERING FOR PIGPIO_PWM
STEERING_PWM_PIN = 13           #Pin numbering according to Broadcom numbers
STEERING_PWM_FREQ = 50          #Frequency for PWM
STEERING_PWM_INVERTED = False   #If PWM needs to be inverted

#THROTTLE
THROTTLE_CHANNEL = 0            #channel on the 9685 pwm board 0-15
THROTTLE_FORWARD_PWM = 500      #pwm value for max forward throttle
THROTTLE_STOPPED_PWM = 370      #pwm value for no movement
THROTTLE_REVERSE_PWM = 220      #pwm value for max reverse throttle

#THROTTLE FOR PIGPIO_PWM
THROTTLE_PWM_PIN = 18           #Pin numbering according to Broadcom numbers
THROTTLE_PWM_FREQ = 50          #Frequency for PWM
THROTTLE_PWM_INVERTED = False   #If PWM needs to be inverted

#DC_STEER_THROTTLE with one motor as steering, one as drive
#these GPIO pinouts are only used for the DRIVE_TRAIN_TYPE=DC_STEER_THROTTLE
HBRIDGE_PIN_LEFT = 18
HBRIDGE_PIN_RIGHT = 16
HBRIDGE_PIN_FWD = 15
HBRIDGE_PIN_BWD = 13

#DC_TWO_WHEEL - with two wheels as drive, left and right.
#these GPIO pinouts are only used for the DRIVE_TRAIN_TYPE=DC_TWO_WHEEL
HBRIDGE_PIN_LEFT_FWD = 18
HBRIDGE_PIN_LEFT_BWD = 16
HBRIDGE_PIN_RIGHT_FWD = 15
HBRIDGE_PIN_RIGHT_BWD = 13


#TRAINING
#The DEFAULT_MODEL_TYPE will choose which model will be created at training time. This chooses
#between different neural network designs. You can override this setting by passing the command
#line parameter --type to the python manage.py train and drive commands.
DEFAULT_MODEL_TYPE = 'linear'   #(linear|categorical|rnn|imu|behavior|3d|localizer|latent)
BATCH_SIZE = 128                #how many records to use when doing one pass of gradient decent. Use a smaller number if your gpu is running out of memory.
TRAIN_TEST_SPLIT = 0.8          #what percent of records to use for training. the remaining used for validation.
MAX_EPOCHS = 100                #how many times to visit all records of your data
SHOW_PLOT = True                #would you like to see a pop up display of final loss?
VERBOSE_TRAIN = True             #would you like to see a progress bar with text during training?
USE_EARLY_STOP = True           #would you like to stop the training if we see it's not improving fit?
EARLY_STOP_PATIENCE = 5         #how many epochs to wait before no improvement
MIN_DELTA = .0005               #early stop will want this much loss change before calling it improved.
PRINT_MODEL_SUMMARY = True      #print layers and weights to stdout
OPTIMIZER = None                #adam, sgd, rmsprop, etc.. None accepts default
LEARNING_RATE = 0.001           #only used when OPTIMIZER specified
LEARNING_RATE_DECAY = 0.0       #only used when OPTIMIZER specified
SEND_BEST_MODEL_TO_PI = False   #change to true to automatically send best model during training
CACHE_IMAGES = True             #keep images in memory. will speed succesive epochs, but crater if not enough mem.

PRUNE_CNN = False               #This will remove weights from your model. The primary goal is to increase performance.
PRUNE_PERCENT_TARGET = 75       # The desired percentage of pruning.
PRUNE_PERCENT_PER_ITERATION = 20 # Percenge of pruning that is perform per iteration.
PRUNE_VAL_LOSS_DEGRADATION_LIMIT = 0.2 # The max amout of validation loss that is permitted during pruning.
PRUNE_EVAL_PERCENT_OF_DATASET = .05  # percent of dataset used to perform evaluation of model.

#Pi login information
#When using the continuous train option, these credentials will
#be used to copy the final model to your vehicle. If not using this option, no need to set these.
PI_USERNAME = "pi"                  # username on pi
PI_PASSWD = "raspberry"             # password is optional. Only used from Windows machine. Ubuntu and mac users should copy their public keys to the pi. `ssh-copy-id username@hostname`
PI_HOSTNAME = "raspberrypi.local"   # the network hostname or ip address
PI_DONKEY_ROOT = "/home/pi/mycar"   # the location of the mycar dir on the pi. this will be used to help locate the final model destination.

# Region of interst cropping
# only supported in Categorical and Linear models.
# If these crops values are too large, they will cause the stride values to become negative and the model with not be valid.
ROI_CROP_TOP = 0                    #the number of rows of pixels to ignore on the top of the image
ROI_CROP_BOTTOM = 0                 #the number of rows of pixels to ignore on the bottom of the image

#Model transfer options
#When copying weights during a model transfer operation, should we freeze a certain number of layers
#to the incoming weights and not allow them to change during training?
FREEZE_LAYERS = False               #default False will allow all layers to be modified by training
NUM_LAST_LAYERS_TO_TRAIN = 7        #when freezing layers, how many layers from the last should be allowed to train?

#WEB CONTROL
WEB_CONTROL_PORT = 8887             # which port to listen on when making a web controller
WEB_INIT_MODE = "user"              # which control mode to start in. one of user|local_angle|local. Setting local will start in ai mode.

#JOYSTICK
USE_JOYSTICK_AS_DEFAULT = False     #when starting the manage.py, when True, will not require a --js option to use the joystick
JOYSTICK_MAX_THROTTLE = 0.5         #this scalar is multiplied with the -1 to 1 throttle value to limit the maximum throttle. This can help if you drop the controller or just don't need the full speed available.
JOYSTICK_STEERING_SCALE = 1.0       #some people want a steering that is less sensitve. This scalar is multiplied with the steering -1 to 1. It can be negative to reverse dir.
AUTO_RECORD_ON_THROTTLE = True      #if true, we will record whenever throttle is not zero. if false, you must manually toggle recording with some other trigger. Usually circle button on joystick.
CONTROLLER_TYPE='ps3'               #(ps3|ps4|xbox|nimbus|wiiu|F710|rc3|MM1|custom) custom will run the my_joystick.py controller written by the `donkey createjs` command
USE_NETWORKED_JS = False            #should we listen for remote joystick control over the network?
NETWORK_JS_SERVER_IP = "192.168.0.1"#when listening for network joystick control, which ip is serving this information
JOYSTICK_DEADZONE = 0.0             # when non zero, this is the smallest throttle before recording triggered.
JOYSTICK_THROTTLE_DIR = -1.0        # use -1.0 to flip forward/backward, use 1.0 to use joystick's natural forward/backward
USE_FPV = False                     # send camera data to FPV webserver
JOYSTICK_DEVICE_FILE = "/dev/input/js0" # this is the unix file use to access the joystick.

#For the categorical model, this limits the upper bound of the learned throttle
#it's very IMPORTANT that this value is matched from the training PC config.py and the robot.py
#and ideally wouldn't change once set.
MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.5

#RNN or 3D
SEQUENCE_LENGTH = 3             #some models use a number of images over time. This controls how many.

#IMU
HAVE_IMU = False                #when true, this add a Mpu6050 part and records the data. Can be used with a
IMU_SENSOR = 'mpu6050'          # (mpu6050|mpu9250)
IMU_DLP_CONFIG = 0              # Digital Lowpass Filter setting (0:250Hz, 1:184Hz, 2:92Hz, 3:41Hz, 4:20Hz, 5:10Hz, 6:5Hz)

#SOMBRERO
HAVE_SOMBRERO = False           #set to true when using the sombrero hat from the Donkeycar store. This will enable pwm on the hat.

#ROBOHAT MM1
HAVE_ROBOHAT = False            # set to true when using the Robo HAT MM1 from Robotics Masters.  This will change to RC Control.
MM1_STEERING_MID = 1500         # Adjust this value if your car cannot run in a straight line
MM1_MAX_FORWARD = 2000          # Max throttle to go fowrward. The bigger the faster
MM1_STOPPED_PWM = 1500
MM1_MAX_REVERSE = 1000          # Max throttle to go reverse. The smaller the faster
MM1_SHOW_STEERING_VALUE = False
# Serial port 
# -- Default Pi: '/dev/ttyS0'
# -- Jetson Nano: '/dev/ttyTHS1'
# -- Google coral: '/dev/ttymxc0'
# -- Windows: 'COM3', Arduino: '/dev/ttyACM0'
# -- MacOS/Linux:please use 'ls /dev/tty.*' to find the correct serial port for mm1 
#  eg.'/dev/tty.usbmodemXXXXXX' and replace the port accordingly
MM1_SERIAL_PORT = '/dev/ttyS0'  # Serial Port for reading and sending MM1 data.

#RECORD OPTIONS
RECORD_DURING_AI = False        #normally we do not record during ai mode. Set this to true to get image and steering records for your Ai. Be careful not to use them to train.

#LED
HAVE_RGB_LED = False            #do you have an RGB LED like https://www.amazon.com/dp/B07BNRZWNF
LED_INVERT = False              #COMMON ANODE? Some RGB LED use common anode. like https://www.amazon.com/Xia-Fly-Tri-Color-Emitting-Diffused/dp/B07MYJQP8B

#LED board pin number for pwm outputs
#These are physical pinouts. See: https://www.raspberrypi-spy.co.uk/2012/06/simple-guide-to-the-rpi-gpio-header-and-pins/
LED_PIN_R = 12
LED_PIN_G = 10
LED_PIN_B = 16

#LED status color, 0-100
LED_R = 0
LED_G = 0
LED_B = 1

#LED Color for record count indicator
REC_COUNT_ALERT = 1000          #how many records before blinking alert
REC_COUNT_ALERT_CYC = 15        #how many cycles of 1/20 of a second to blink per REC_COUNT_ALERT records
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
#When training the Behavioral Neural Network model, make a list of the behaviors,
#Set the TRAIN_BEHAVIORS = True, and use the BEHAVIOR_LED_COLORS to give each behavior a color
TRAIN_BEHAVIORS = False
BEHAVIOR_LIST = ['Left_Lane', "Right_Lane"]
BEHAVIOR_LED_COLORS =[ (0, 10, 0), (10, 0, 0) ] #RGB tuples 0-100 per chanel

#Localizer
#The localizer is a neural network that can learn to predice it's location on the track.
#This is an experimental feature that needs more developement. But it can currently be used
#to predict the segement of the course, where the course is divided into NUM_LOCATIONS segments.
TRAIN_LOCALIZER = False
NUM_LOCATIONS = 10
BUTTON_PRESS_NEW_TUB = False #when enabled, makes it easier to divide our data into one tub per track length if we make a new tub on each X button press.

#DonkeyGym
#Only on Ubuntu linux, you can use the simulator as a virtual donkey and
#issue the same python manage.py drive command as usual, but have them control a virtual car.
#This enables that, and sets the path to the simualator and the environment.
#You will want to download the simulator binary from: https://github.com/tawnkramer/donkey_gym/releases/download/v18.9/DonkeySimLinux.zip
#then extract that and modify DONKEY_SIM_PATH.
DONKEY_GYM = False
DONKEY_SIM_PATH = "path to sim" #"/home/tkramer/projects/sdsandbox/sdsim/build/DonkeySimLinux/donkey_sim.x86_64" when racing on virtual-race-league use "remote", or user "remote" when you want to start the sim manually first.
DONKEY_GYM_ENV_NAME = "donkey-mountain-track-v0" # ("donkey-generated-track-v0"|"donkey-generated-roads-v0"|"donkey-warehouse-v0"|"donkey-avc-sparkfun-v0")
GYM_CONF = { "body_style" : "donkey", "body_rgb" : (128, 128, 128), "car_name" : "me", "font_size" : 100} # body style(donkey|bare|car01) body rgb 0-255
SIM_HOST = "127.0.0.1"              # when racing on virtual-race-league use host "trainmydonkey.com"
SIM_ARTIFICIAL_LATENCY = 0          # this is the millisecond latency in controls. Can use useful in emulating the delay when useing a remote server. values of 100 to 400 probably reasonable.

#publish camera over network
#This is used to create a tcp service to pushlish the camera feed
PUB_CAMERA_IMAGES = False

#When racing, to give the ai a boost, configure these values.
AI_LAUNCH_DURATION = 0.0            # the ai will output throttle for this many seconds
AI_LAUNCH_THROTTLE = 0.0            # the ai will output this throttle value
AI_LAUNCH_ENABLE_BUTTON = 'R2'      # this keypress will enable this boost. It must be enabled before each use to prevent accidental trigger.
AI_LAUNCH_KEEP_ENABLED = False      # when False ( default) you will need to hit the AI_LAUNCH_ENABLE_BUTTON for each use. This is safest. When this True, is active on each trip into "local" ai mode.

#Scale the output of the throttle of the ai pilot for all model types.
AI_THROTTLE_MULT = 1.0              # this multiplier will scale every throttle value for all output from NN models

#Path following
PATH_FILENAME = "donkey_path.pkl"   # the path will be saved to this filename
PATH_SCALE = 5.0                    # the path display will be scaled by this factor in the web page
PATH_OFFSET = (0, 0)                # 255, 255 is the center of the map. This offset controls where the origin is displayed.
PATH_MIN_DIST = 0.3                 # after travelling this distance (m), save a path point
PID_P = -10.0                       # proportional mult for PID path follower
PID_I = 0.000                       # integral mult for PID path follower
PID_D = -0.2                        # differential mult for PID path follower
PID_THROTTLE = 0.2                  # constant throttle value during path following
SAVE_PATH_BTN = "cross"             # joystick button to save path
RESET_ORIGIN_BTN = "triangle"       # joystick button to press to move car back to origin

# Intel Realsense D435 and D435i depth sensing camera
REALSENSE_D435_RGB = True       # True to capture RGB image
REALSENSE_D435_DEPTH = True     # True to capture depth as image array
REALSENSE_D435_IMU = False      # True to capture IMU data (D435i only)
REALSENSE_D435_ID = None        # serial number of camera or None if you only have one camera (it will autodetect)


