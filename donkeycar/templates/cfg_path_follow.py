# """ 
# My CAR CONFIG 

# This file is read by your car application's manage.py script to change the car
# performance

# If desired, all config overrides can be specified here. 
# The update operation will not touch this file.
# """

import os
# 
# #PATHS
CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')
# 
# #VEHICLE
DRIVE_LOOP_HZ = 20      # the vehicle loop will pause if faster than this speed.
MAX_LOOPS = None        # the vehicle loop can abort after this many iterations, when given a positive integer.
# 

#WEB CONTROL
WEB_CONTROL_PORT = int(os.getenv("WEB_CONTROL_PORT", 8887))  # which port to listen on when making a web controller
WEB_INIT_MODE = "user"              # which control mode to start in. one of user|local_angle|local. Setting local will start in ai mode.


# #9865, over rides only if needed, ie. TX2..
PCA9685_I2C_ADDR = 0x40     #I2C address, use i2cdetect to validate this number
PCA9685_I2C_BUSNUM = None   #None will auto detect, which is fine on the pi. But other platforms should specify the bus num.
# 
# #DRIVETRAIN
# #These options specify which chasis and motor setup you are using. Most are using SERVO_ESC.
# #DC_STEER_THROTTLE uses HBridge pwm to control one steering dc motor, and one drive wheel motor
# #DC_TWO_WHEEL uses HBridge pwm to control two drive motors, one on the left, and one on the right.
# #SERVO_HBRIDGE_PWM use ServoBlaster to output pwm control from the PiZero directly to control steering, and HBridge for a drive motor.
DRIVE_TRAIN_TYPE = "SERVO_ESC" # SERVO_ESC|DC_STEER_THROTTLE|DC_TWO_WHEEL|SERVO_HBRIDGE_PWM
# 
# #STEERING
STEERING_CHANNEL = 1            #channel on the 9685 pwm board 0-15
STEERING_LEFT_PWM = 460         #pwm value for full left steering
STEERING_RIGHT_PWM = 340        #pwm value for full right steering
# 
# #THROTTLE
THROTTLE_CHANNEL = 0            #channel on the 9685 pwm board 0-15
THROTTLE_FORWARD_PWM = 400       #pwm value for auto mode throttle
THROTTLE_STOPPED_PWM = 370      #pwm value for no movement
THROTTLE_REVERSE_PWM = 220      #pwm value for max reverse throttle
# 
# #DC_STEER_THROTTLE with one motor as steering, one as drive
# #these GPIO pinouts are only used for the DRIVE_TRAIN_TYPE=DC_STEER_THROTTLE
HBRIDGE_PIN_LEFT = 18
HBRIDGE_PIN_RIGHT = 16
HBRIDGE_PIN_FWD = 15
HBRIDGE_PIN_BWD = 13
# 
# #DC_TWO_WHEEL - with two wheels as drive, left and right.
# #these GPIO pinouts are only used for the DRIVE_TRAIN_TYPE=DC_TWO_WHEEL
HBRIDGE_PIN_LEFT_FWD = 18
HBRIDGE_PIN_LEFT_BWD = 16
HBRIDGE_PIN_RIGHT_FWD = 15
HBRIDGE_PIN_RIGHT_BWD = 13
# 
# 
# 
# #JOYSTICK
USE_JOYSTICK_AS_DEFAULT = False      #when starting the manage.py, when True, will not require a --js option to use the joystick
JOYSTICK_MAX_THROTTLE = 0.5         #this scalar is multiplied with the -1 to 1 throttle value to limit the maximum throttle. This can help if you drop the controller or just don't need the full speed available.
JOYSTICK_STEERING_SCALE = 1.0       #some people want a steering that is less sensitve. This scalar is multiplied with the steering -1 to 1. It can be negative to reverse dir.
AUTO_RECORD_ON_THROTTLE = True      #if true, we will record whenever throttle is not zero. if false, you must manually toggle recording with some other trigger. Usually circle button on joystick.
CONTROLLER_TYPE='ps4'               #(ps3|ps4|xbox|nimbus|wiiu|F710|rc3)
USE_NETWORKED_JS = False            #should we listen for remote joystick control over the network?
NETWORK_JS_SERVER_IP = "192.168.0.1"#when listening for network joystick control, which ip is serving this information
JOYSTICK_DEADZONE = 0.0             # when non zero, this is the smallest throttle before recording triggered.
JOYSTICK_THROTTLE_DIR = -1.0        # use -1.0 to flip forward/backward, use 1.0 to use joystick's natural forward/backward
JOYSTICK_DEVICE_FILE = "/dev/input/js0" # this is the unix file use to access the joystick.
USE_FPV = False                     # send camera data to FPV webserver

# 
# 
# #SOMBRERO
HAVE_SOMBRERO = False               #set to true when using the sombrero hat from the Donkeycar store. This will enable pwm on the hat.
# 
# 
#Path following
PATH_FILENAME = "donkey_path.pkl"   # the path will be saved to this filename
PATH_SCALE = 10.0                   # the path display will be scaled by this factor in the web page
PATH_OFFSET = (255, 255)            # 255, 255 is the center of the map. This offset controls where the origin is displayed.
PATH_MIN_DIST = 0.2                 # after travelling this distance (m), save a path point
PID_P = -0.5                        # proportional mult for PID path follower
PID_I = 0.000                       # integral mult for PID path follower
PID_D = -0.3                       # differential mult for PID path follower
PID_THROTTLE = 0.30                 # constant throttle value during path following

# the cross button is already reserved for the emergency stop
SAVE_PATH_BTN = "circle"             # joystick button to save path
RESET_ORIGIN_BTN = "square"       # joystick button to press to move car back to origin
ERASE_PATH_BTN = "triangle"     # joystick button to erase path



# 
# #Odometry
HAVE_ODOM = False                   # Do you have an odometer? Uses pigpio 
MM_PER_TICK = 12.7625               # How much travel with a single tick, in mm
ODOM_PIN = 4                        # Which GPIO board mode pin to use as input
ODOM_DEBUG = False                  # Write out values on vel and distance as it runs
# 
# #Intel T265
WHEEL_ODOM_CALIB = "calibration_odometry.json"
# 
# #DonkeyGym
# #Only on Ubuntu linux, you can use the simulator as a virtual donkey and
# #issue the same python manage.py drive command as usual, but have them control a virtual car.
# #This enables that, and sets the path to the simualator and the environment.
# #You will want to download the simulator binary from: https://github.com/tawnkramer/donkey_gym/releases/download/v18.9/DonkeySimLinux.zip
# #then extract that and modify DONKEY_SIM_PATH.
DONKEY_GYM = False
DONKEY_SIM_PATH = "path to sim" #"/home/tkramer/projects/sdsandbox/sdsim/build/DonkeySimLinux/donkey_sim.x86_64"
DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0" # ("donkey-generated-track-v0"|"donkey-generated-roads-v0"|"donkey-warehouse-v0"|"donkey-avc-sparkfun-v0")
