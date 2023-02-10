# """ 
# My CAR CONFIG 

# This file is read by your car application's manage.py script to change the car
# performance

# If desired, all config overrides can be specified here. 
# The update operation will not touch this file.
# """


# #VEHICLE
DRIVE_LOOP_HZ = 35      # the vehicle loop will pause if faster than this speed.
# MAX_LOOPS = None        # the vehicle loop can abort after this many iterations, when given a positive integer.

# #CAMERA
CAMERA_TYPE = "OAK"   # (PICAM|WEBCAM|CVCAM|CSIC|V4L|D435|MOCK|IMAGE_LIST) OAK_SEG
CAMERA_FRAMERATE = DRIVE_LOOP_HZ
CAMERA_ISP_SCALE = (1,8)
IMAGE_W = 240 # 640 320 160
IMAGE_H = 135 # 400 200 120
IMAGE_DEPTH = 3         # default RGB=3, make 1 for mono
# CAMERA_FRAMERATE = DRIVE_LOOP_HZ
# CAMERA_VFLIP = False
# CAMERA_HFLIP = False
# CAMERA_INDEX = 0  # used for 'WEBCAM' and 'CVCAM' when there is more than one camera connected 
# # For CSIC camera - If the camera is mounted in a rotated position, changing the below parameter will correct the output frame orientation
# CSIC_CAM_GSTREAMER_FLIP_PARM = 0 # (0 => none , 4 => Flip horizontally, 6 => Flip vertically)
OAK_SEGMENTATION_MODEL_BLOB_PATH = '~/car/models/road-segmentation-adas-0001_openvino_2021.4_6shave.blob'

# OAK-D-LITE: "1080p" for rgb
# OAK-D-WIDE: "800p" for rgb
RGB_RESOLUTION = "1080p"

# OAK-D-LITE: from 1920/1080 (1,8)>>240/135 
# OAK-D-WIDE: from 1280/800  (1,8)>>160/100 (3,16)>>240/150 5/32>>200/125 
# OAK_D_ISP_SCALE = (3,16)

# OAK-D-LITE: color cam = 240 ISP 1/8 ou 192 ISP 1/10 ou 224 ISP 7/60
# OAK-D-WIDE: 240 ou 200 ou 160
# IMAGE_W = 240
# OAK-D-LITE: color cam = 135 ISP 1/8 ou 108 ISP 1/10 ou 126 ISP 7/60
# OAK-D-WIDE: 150 ou 125 ou 100
# IMAGE_H = 150

# IMAGE_DEPTH = 3         # default RGB=3, make 1 for mono

OAK_ENABLE_DEPTH_MAP = False # enables depth map output
OAK_OBSTACLE_DETECTION_ENABLED = False # enable roi distances output

# OBSTACLE_AVOIDANCE SETTINGS
OBSTACLE_AVOIDANCE_ENABLED = False
OBSTACLE_AVOIDANCE_FOR_AUTOPILOT = False # True activates avoidance for autopilot, False for user (manual control)
CLOSE_AVOIDANCE_DIST_MM = 1000


# # For IMAGE_LIST camera
# # PATH_MASK = "~/mycar/data/tub_1_20-03-12/*.jpg"

# #
# # DRIVE_TRAIN_TYPE
# # These options specify which chasis and motor setup you are using.
# # See Actuators documentation https://docs.donkeycar.com/parts/actuators/
# # for a detailed explanation of each drive train type and it's configuration.
# # Choose one of the following and then update the related configuration section:
# #
# # "PWM_STEERING_THROTTLE" uses two PWM output pins to control a steering servo and an ESC, as in a standard RC car.
# # "MM1" Robo HAT MM1 board
# # "SERVO_HBRIDGE_2PIN" Servo for steering and HBridge motor driver in 2pin mode for motor
# # "SERVO_HBRIDGE_3PIN" Servo for steering and HBridge motor driver in 3pin mode for motor
# # "DC_STEER_THROTTLE" uses HBridge pwm to control one steering dc motor, and one drive wheel motor
# # "DC_TWO_WHEEL" uses HBridge in 2-pin mode to control two drive motors, one on the left, and one on the right.
# # "DC_TWO_WHEEL_L298N" using HBridge in 3-pin mode to control two drive motors, one of the left and one on the right.
# # "ROBOCARSHAT" using robocars hat
# # "MOCK" no drive train.  This can be used to test other features in a test rig.
# # (deprecated) "SERVO_HBRIDGE_PWM" use ServoBlaster to output pwm control from the PiZero directly to control steering,
# #                                  and HBridge for a drive motor.
# # (deprecated) "PIGPIO_PWM" uses Raspberrys internal PWM
# # (deprecated) "I2C_SERVO" uses PCA9685 servo controller to control a steering servo and an ESC, as in a standard RC car
# #
DRIVE_TRAIN_TYPE = "ROBOCARSHAT"

#ROBOCARSHAT
# USE_ROBOCARSHAT_AS_CONTROLLER  = True
ROBOCARSHAT_SERIAL_PORT = '/dev/serial0'

# # Following values must be aligned with values in Hat !
# ROBOCARSHAT_PWM_OUT_THROTTLE_MIN    =   1000
# ROBOCARSHAT_PWM_OUT_THROTTLE_IDLE   =   1500
# ROBOCARSHAT_PWM_OUT_THROTTLE_MAX    =   2000
# ROBOCARSHAT_PWM_OUT_STEERING_MIN    =   1000
# ROBOCARSHAT_PWM_OUT_STEERING_IDLE   =   1500
# ROBOCARSHAT_PWM_OUT_STEERING_MAX    =   2000

# # Folowing values can be ajusted to normalized between -1 and 1.
# # # If  ROBOCARSHAT_USE_AUTOCALIBRATION is used, IDLE values are automatically identified by the Hat
# ROBOCARSHAT_PWM_IN_THROTTLE_MIN    =   1000
# ROBOCARSHAT_PWM_IN_THROTTLE_IDLE   =   1500
# ROBOCARSHAT_PWM_IN_THROTTLE_MAX    =   2000
# ROBOCARSHAT_PWM_IN_STEERING_MIN    =   1000
# ROBOCARSHAT_PWM_IN_STEERING_IDLE   =   1500
# ROBOCARSHAT_PWM_IN_STEERING_MAX    =   2000
# ROBOCARSHAT_PWM_IN_AUX_MIN    =   1000
# ROBOCARSHAT_PWM_IN_AUX_IDLE   =   1500
# ROBOCARSHAT_PWM_IN_AUX_MAX    =   2000

ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE = 0.09 # For pilot_angle autonomous mode (aka constant throttle)
ROBOCARSHAT_LOCAL_ANGLE_BRAKE_THROTTLE = -0.2

#ODOM Sensor max value (max matching lowest speed)
ROBOCARSHAT_ODOM_IN_MAX = 20000
ROBOCARSHAT_PILOT_MODE = 'local_angle' # Which autonomous mode is triggered by Hat : local_angle or local
ROBOCARSHAT_BRAKE_ON_IDLE_THROTTLE = -0.2

THROTTLE_BRAKE_REV_FILTER = True # False: ESC is configured in Fw/Rv mode (no braking)

# #ROBOCARSHAT_CH3_FEATURE control the feature attached to radio ch3
# # 'record/pilot' mean ch3 is used to control either data recording (lower position), either to enable pilot mode (upper position)
# # 'throttle_exploration' means special mode where CH3 is used to increment/decrement a fixed throttle value in user mode 
# # 'steering_exploration' means special mode where CH3 is used to increment/decrement a fixed steering value in user mode 
# # 'output_steering_trim' means special mode where CH3 is used to increment/decrement a steering idle output for triming direction in user mode, resulting value must be reported in  ROBOCARSHAT_PWM_OUT_STEERING_IDLE
# # 'output_steering_exp' means special mode where CH3 is used to increment/decrement a fixed steering output to calibrate direction in user mode, resulting values must be reported in  ROBOCARSHAT_PWM_IN_STEERING_MIN and ROBOCARSHAT_PWM_IN_STEERING_MAX
# ROBOCARSHAT_CH3_FEATURE = '' 
ROBOCARSHAT_CH3_FEATURE = 'record/pilot' 
ROBOCARSHAT_CH4_FEATURE = 'none' 
# ROBOCARSHAT_THROTTLE_EXP_INC = 0.05 
# ROBOCARSHAT_STEERING_EXP_INC = 0.05 
# ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC = 10 

# #ROBOCARSHAT_STEERING_FIX used for steering calibration, enforce a fixed steering value (betzeen -1.0 and 1.0). None means no enforcment
# ROBOCARSHAT_STEERING_FIX = None 

# # ROBOCARSHAT_THROTTLE_DISCRET used to control throttle with discretes values (only in user mode, first value must be 0.0)
# # ROBOCARSHAT_THROTTLE_DISCRET has precedence over ROBOCARSHAT_THROTTLE_FLANGER
# #Example : ROBOCARSHAT_THROTTLE_DISCRET = [0.0, 0.1, 0.2], if not used, set to None 
ROBOCARSHAT_THROTTLE_DISCRET = None
# ROBOCARSHAT_THROTTLE_DISCRET = [0.0, ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE] 

# # ROBOCARSHAT_THROTTLE_FLANGER used to control throttle flange (map outputs to given range), ONLY in USER MODE
# # giving a range between -1 and 1, like [-0.1, 0.1]
# #Example : ROBOCARSHAT_THROTTLE_FLANGER = [-0.1, 0.1], if not used, set to None 
# ROBOCARSHAT_THROTTLE_FLANGER = None 
ROBOCARSHAT_THROTTLE_FLANGER = [-0.2,0.2]

# # ROBOCARSHAT_USE_AUTOCALIBRATION used to rely on idle coming from autocalibation done by hat
ROBOCARSHAT_USE_AUTOCALIBRATION = True

ROBOCARSHAT_EMERGENCY_STOP=False


# #ODOMETRY
# HAVE_ODOM = False                   # Do you have an odometer/encoder 
# ENCODER_TYPE = 'GPIO'            # What kind of encoder? GPIO|Arduino|Astar 
# MM_PER_TICK = 12.7625               # How much travel with a single tick, in mm. Roll you car a meter and divide total ticks measured by 1,000
# ODOM_PIN = 13                        # if using GPIO, which GPIO board mode pin to use as input
# ODOM_DEBUG = False                  # Write out values on vel and distance as it runs

# # #LIDAR
# USE_LIDAR = False
# LIDAR_TYPE = 'RP' #(RP|YD)
# LIDAR_LOWER_LIMIT = 90 # angles that will be recorded. Use this to block out obstructed areas on your car, or looking backwards. Note that for the RP A1M8 Lidar, "0" is in the direction of the motor
# LIDAR_UPPER_LIMIT = 270

# #TRAINING
# # The default AI framework to use. Choose from (tensorflow|pytorch)
# DEFAULT_AI_FRAMEWORK = 'tensorflow'

# # The DEFAULT_MODEL_TYPE will choose which model will be created at training
# # time. This chooses between different neural network designs. You can
# # override this setting by passing the command line parameter --type to the
# # python manage.py train and drive commands.
# # tensorflow models: (linear|categorical|tflite_linear|tensorrt_linear)
# # pytorch models: (resnet18)
DEFAULT_MODEL_TYPE = 'tflite_linear'
# BATCH_SIZE = 128                #how many records to use when doing one pass of gradient decent. Use a smaller number if your gpu is running out of memory.
# TRAIN_TEST_SPLIT = 0.8          #what percent of records to use for training. the remaining used for validation.
# MAX_EPOCHS = 100                #how many times to visit all records of your data
# SHOW_PLOT = True                #would you like to see a pop up display of final loss?
# VERBOSE_TRAIN = True            #would you like to see a progress bar with text during training?
# USE_EARLY_STOP = True           #would you like to stop the training if we see it's not improving fit?
# EARLY_STOP_PATIENCE = 5         #how many epochs to wait before no improvement
# MIN_DELTA = .0005               #early stop will want this much loss change before calling it improved.
# PRINT_MODEL_SUMMARY = True      #print layers and weights to stdout
# OPTIMIZER = None                #adam, sgd, rmsprop, etc.. None accepts default
# LEARNING_RATE = 0.001           #only used when OPTIMIZER specified
# LEARNING_RATE_DECAY = 0.0       #only used when OPTIMIZER specified
# SEND_BEST_MODEL_TO_PI = False   #change to true to automatically send best model during training
# CREATE_TF_LITE = True           # automatically create tflite model in training
# CREATE_TENSOR_RT = False        # automatically create tensorrt model in training

# PRUNE_CNN = False               #This will remove weights from your model. The primary goal is to increase performance.
# PRUNE_PERCENT_TARGET = 75       # The desired percentage of pruning.
# PRUNE_PERCENT_PER_ITERATION = 20 # Percenge of pruning that is perform per iteration.
# PRUNE_VAL_LOSS_DEGRADATION_LIMIT = 0.2 # The max amout of validation loss that is permitted during pruning.
# PRUNE_EVAL_PERCENT_OF_DATASET = .05  # percent of dataset used to perform evaluation of model.

# # Augmentations and Transformations
# AUGMENTATIONS = []
TRANSFORMATIONS = ['CROP']
# # Settings for brightness and blur, use 'MULTIPLY' and/or 'BLUR' in
# # AUGMENTATIONS
# AUG_MULTIPLY_RANGE = (0.5, 3.0)
# AUG_BLUR_RANGE = (0.0, 3.0)
# # Region of interest cropping, requires 'CROP' in TRANSFORMATIONS to be set
# # If these crops values are too large, they will cause the stride values to
# # become negative and the model with not be valid.
ROI_CROP_TOP = 10               # the number of rows of pixels to ignore on the top of the image
# ROI_CROP_BOTTOM = 0             # the number of rows of pixels to ignore on the bottom of the image
# ROI_CROP_RIGHT = 0              # the number of rows of pixels to ignore on the right of the image
# ROI_CROP_LEFT = 0               # the number of rows of pixels to ignore on the left of the image
# # For trapezoidal see explanation in augmentations.py. Requires 'TRAPEZE' in
# # TRANSFORMATIONS to be set
# ROI_TRAPEZE_LL = 0
# ROI_TRAPEZE_LR = 160
# ROI_TRAPEZE_UL = 20
# ROI_TRAPEZE_UR = 140
# ROI_TRAPEZE_MIN_Y = 60
# ROI_TRAPEZE_MAX_Y = 120

# #Model transfer options
# #When copying weights during a model transfer operation, should we freeze a certain number of layers
# #to the incoming weights and not allow them to change during training?
# FREEZE_LAYERS = False               #default False will allow all layers to be modified by training
# NUM_LAST_LAYERS_TO_TRAIN = 7        #when freezing layers, how many layers from the last should be allowed to train?

# #WEB CONTROL
# WEB_CONTROL_PORT = int(os.getenv("WEB_CONTROL_PORT", 8887))  # which port to listen on when making a web controller
# WEB_INIT_MODE = "user"              # which control mode to start in. one of user|local_angle|local. Setting local will start in ai mode.

# #JOYSTICK
# USE_JOYSTICK_AS_DEFAULT = False      #when starting the manage.py, when True, will not require a --js option to use the joystick
# JOYSTICK_MAX_THROTTLE = 0.5         #this scalar is multiplied with the -1 to 1 throttle value to limit the maximum throttle. This can help if you drop the controller or just don't need the full speed available.
# JOYSTICK_STEERING_SCALE = 1.0       #some people want a steering that is less sensitve. This scalar is multiplied with the steering -1 to 1. It can be negative to reverse dir.
AUTO_RECORD_ON_THROTTLE = False      #if true, we will record whenever throttle is not zero. if false, you must manually toggle recording with some other trigger. Usually circle button on joystick.
# CONTROLLER_TYPE = 'ps4'            #(ps3|ps4|xbox|pigpio_rc|nimbus|wiiu|F710|rc3|MM1|custom) custom will run the my_joystick.py controller written by the `donkey createjs` command
# USE_NETWORKED_JS = False            #should we listen for remote joystick control over the network?
# NETWORK_JS_SERVER_IP = None         #when listening for network joystick control, which ip is serving this information
# JOYSTICK_DEADZONE = 0.01            # when non zero, this is the smallest throttle before recording triggered.
# JOYSTICK_THROTTLE_DIR = -1.0         # use -1.0 to flip forward/backward, use 1.0 to use joystick's natural forward/backward
# USE_FPV = False                     # send camera data to FPV webserver
# JOYSTICK_DEVICE_FILE = "/dev/input/js0" # this is the unix file use to access the joystick.

# #For the categorical model, this limits the upper bound of the learned throttle
# #it's very IMPORTANT that this value is matched from the training PC config.py and the robot.py
# #and ideally wouldn't change once set.
# MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.8

# #RNN or 3D
# SEQUENCE_LENGTH = 3             #some models use a number of images over time. This controls how many.

# #IMU
# HAVE_IMU = False                #when true, this add a Mpu6050 part and records the data. Can be used with a
# IMU_SENSOR = 'mpu6050'          # (mpu6050|mpu9250)
# IMU_DLP_CONFIG = 0              # Digital Lowpass Filter setting (0:250Hz, 1:184Hz, 2:92Hz, 3:41Hz, 4:20Hz, 5:10Hz, 6:5Hz)

# #LOGGING
HAVE_CONSOLE_LOGGING = False
# LOGGING_LEVEL = 'INFO'          # (Python logging level) 'NOTSET' / 'DEBUG' / 'INFO' / 'WARNING' / 'ERROR' / 'FATAL' / 'CRITICAL'
# LOGGING_FORMAT = '%(message)s'  # (Python logging format - https://docs.python.org/3/library/logging.html#formatter-objects

# #TELEMETRY
# HAVE_MQTT_TELEMETRY = False
# TELEMETRY_DONKEY_NAME = 'my_robot1234'
# TELEMETRY_MQTT_TOPIC_TEMPLATE = 'donkey/%s/telemetry'
# TELEMETRY_MQTT_JSON_ENABLE = False
# TELEMETRY_MQTT_BROKER_HOST = 'broker.hivemq.com'
# TELEMETRY_MQTT_BROKER_PORT = 1883
# TELEMETRY_PUBLISH_PERIOD = 1
# TELEMETRY_LOGGING_ENABLE = True
# TELEMETRY_LOGGING_LEVEL = 'INFO' # (Python logging level) 'NOTSET' / 'DEBUG' / 'INFO' / 'WARNING' / 'ERROR' / 'FATAL' / 'CRITICAL'
# TELEMETRY_LOGGING_FORMAT = '%(message)s'  # (Python logging format - https://docs.python.org/3/library/logging.html#formatter-objects
# TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle,recording'
# TELEMETRY_DEFAULT_TYPES = 'float,float'

# # PERF MONITOR
# HAVE_PERFMON = False

# #RECORD OPTIONS
RECORD_DURING_AI = False        #normally we do not record during ai mode. Set this to true to get image and steering records for your Ai. Be careful not to use them to train.
AUTO_CREATE_NEW_TUB = True     #create a new tub (tub_YY_MM_DD) directory when recording or append records to data directory directly

# #BEHAVIORS
# #When training the Behavioral Neural Network model, make a list of the behaviors,
# #Set the TRAIN_BEHAVIORS = True, and use the BEHAVIOR_LED_COLORS to give each behavior a color
# TRAIN_BEHAVIORS = False
# BEHAVIOR_LIST = ['Left_Lane', "Right_Lane"]
# BEHAVIOR_LED_COLORS = [(0, 10, 0), (10, 0, 0)]  #RGB tuples 0-100 per chanel

# #Localizer
# #The localizer is a neural network that can learn to predict its location on the track.
# #This is an experimental feature that needs more developement. But it can currently be used
# #to predict the segement of the course, where the course is divided into NUM_LOCATIONS segments.
# TRAIN_LOCALIZER = False
# NUM_LOCATIONS = 10
# BUTTON_PRESS_NEW_TUB = False #when enabled, makes it easier to divide our data into one tub per track length if we make a new tub on each X button press.

# #DonkeyGym
# #Only on Ubuntu linux, you can use the simulator as a virtual donkey and
# #issue the same python manage.py drive command as usual, but have them control a virtual car.
# #This enables that, and sets the path to the simualator and the environment.
# #You will want to download the simulator binary from: https://github.com/tawnkramer/donkey_gym/releases/download/v18.9/DonkeySimLinux.zip
# #then extract that and modify DONKEY_SIM_PATH.
DONKEY_GYM = False
DONKEY_SIM_PATH = "/Users/romain/Sources/perso/DonkeySimMac/donkey_sim.app/Contents/MacOS/donkey_sim" #"/home/tkramer/projects/sdsandbox/sdsim/build/DonkeySimLinux/donkey_sim.x86_64" when racing on virtual-race-league use "remote", or user "remote" when you want to start the sim manually first.
DONKEY_GYM_ENV_NAME = "donkey-roboracingleague-track-v0" # ("donkey-generated-track-v0"|"donkey-generated-roads-v0"|"donkey-warehouse-v0"|"donkey-avc-sparkfun-v0")
GYM_CONF = { "body_style" : "donkey", "body_rgb" : (128, 128, 128), "car_name" : "car", "font_size" : 100} # body style(donkey|bare|car01) body rgb 0-255
GYM_CONF["cam_resolution"] = (120, 160, 3)
GYM_CONF["cam_config"] = { "fov": 120 }
# GYM_CONF["racer_name"] = "Your Name"
# GYM_CONF["country"] = "Place"
# GYM_CONF["bio"] = "I race robots."

# SIM_HOST = "127.0.0.1"              # when racing on virtual-race-league use host "trainmydonkey.com"
# SIM_ARTIFICIAL_LATENCY = 0          # this is the millisecond latency in controls. Can use useful in emulating the delay when useing a remote server. values of 100 to 400 probably reasonable.

# # Save info from Simulator (pln)
# SIM_RECORD_LOCATION = False
# SIM_RECORD_GYROACCEL= False
# SIM_RECORD_VELOCITY = False
# SIM_RECORD_LIDAR = False

# #publish camera over network
# #This is used to create a tcp service to publish the camera feed
# PUB_CAMERA_IMAGES = False

# #When racing, to give the ai a boost, configure these values.
# AI_LAUNCH_DURATION = 0.0            # the ai will output throttle for this many seconds
# AI_LAUNCH_THROTTLE = 0.0            # the ai will output this throttle value
# AI_LAUNCH_ENABLE_BUTTON = 'R2'      # this keypress will enable this boost. It must be enabled before each use to prevent accidental trigger.
# AI_LAUNCH_KEEP_ENABLED = False      # when False ( default) you will need to hit the AI_LAUNCH_ENABLE_BUTTON for each use. This is safest. When this True, is active on each trip into "local" ai mode.

# #Scale the output of the throttle of the ai pilot for all model types.
# AI_THROTTLE_MULT = 1.0              # this multiplier will scale every throttle value for all output from NN models

# #Path following
# PATH_FILENAME = "donkey_path.pkl"   # the path will be saved to this filename
# PATH_SCALE = 5.0                    # the path display will be scaled by this factor in the web page
# PATH_OFFSET = (0, 0)                # 255, 255 is the center of the map. This offset controls where the origin is displayed.
# PATH_MIN_DIST = 0.3                 # after travelling this distance (m), save a path point
# PID_P = -10.0                       # proportional mult for PID path follower
# PID_I = 0.000                       # integral mult for PID path follower
# PID_D = -0.2                        # differential mult for PID path follower
# PID_THROTTLE = 0.2                  # constant throttle value during path following
# SAVE_PATH_BTN = "cross"             # joystick button to save path
# RESET_ORIGIN_BTN = "triangle"       # joystick button to press to move car back to origin

# # FPS counter
# SHOW_FPS = False
# FPS_DEBUG_INTERVAL = 10    # the interval in seconds for printing the frequency info into the shell
