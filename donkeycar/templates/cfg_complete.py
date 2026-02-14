"""
CAR CONFIG

This file is read by your car application's manage.py script to change the car
performance.

EXAMPLE
-----------
import dk
cfg = dk.load_config(config_path='~/mycar/config.py')
print(cfg.CAMERA_RESOLUTION)
"""

import os

# ==============================================================================
# 1. HARDWARE CONFIGURATION & I/O
#    (Camera, Drive Train, Sensors, Pins, Display)
# ==============================================================================

# PATHS
CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')
MODELS_PATH = os.path.join(CAR_PATH, 'models')

# ------------------------------------------------------------------------------
# CAMERA SETUP
# ------------------------------------------------------------------------------

# Select the camera type.
# 'PICAM': Raspberry Pi Camera (CSI)
# 'WEBCAM': USB Camera
# 'CVCAM': OpenCV Camera (often same as WEBCAM)
# 'CSIC': High-speed CSI camera (e.g. Arducam)
# 'D435': Intel Realsense D435
# 'OAKD': Luxonis OAK-D
# 'MOCK': Simulation/Testing or when using GPS path following
CAMERA_TYPE = "PICAM"

# The resolution of the input image. Higher resolution needs more processing power.
IMAGE_W = 160
IMAGE_H = 120

# The depth of the image. 3 for RGB, 1 for Greyscale.
IMAGE_DEPTH = 3

# The framerate of the camera. Should generally match DRIVE_LOOP_HZ.
CAMERA_FRAMERATE = 20

# Flip the image vertically (useful if camera is mounted upside down).
CAMERA_VFLIP = False

# Flip the image horizontally.
CAMERA_HFLIP = False

# Used for 'WEBCAM' and 'CVCAM' when there is more than one camera connected.
CAMERA_INDEX = 0

# CSIC Camera: 0=None, 4=Flip Horizontal, 6=Flip Vertical.
CSIC_CAM_GSTREAMER_FLIP_PARM = 0

# Convert Blue-Green-Red (OpenCV default) to Red-Green-Blue.
BGR2RGB = False

# Intel Realsense D435 specific settings
REALSENSE_D435_RGB = True       # True to capture RGB image
REALSENSE_D435_DEPTH = True     # True to capture depth as image array
REALSENSE_D435_IMU = False      # True to capture IMU data (D435i only)
REALSENSE_D435_ID = None        # Serial number of camera or None for auto-detect

# OAK-D Camera specific settings
OAKD_RGB = True       # True to capture RGB image
OAKD_DEPTH = True     # True to capture depth as image array
OAKD_ID = None        # Serial number of camera or None for auto-detect


# ------------------------------------------------------------------------------
# I2C & DISPLAY
# ------------------------------------------------------------------------------

# I2C address of the PCA9685 servo driver (standard is 0x40).
PCA9685_I2C_ADDR = 0x40

# I2C bus number. None will auto-detect (usually 1 on Pi).
PCA9685_I2C_BUSNUM = None

# Enable the SSD1306 OLED display (small screen on the car).
USE_SSD1306_128_32 = False

# OLED Rotation: 0 = normal, 1 = 90 deg, 2 = 180 deg, 3 = 270 deg.
SSD1306_128_32_I2C_ROTATION = 0

# OLED Resolution: 1 = 128x32, 2 = 128x64.
SSD1306_RESOLUTION = 1


# ------------------------------------------------------------------------------
# INPUT DEVICES (JOYSTICK / CONTROLLER)
# ------------------------------------------------------------------------------

# If True, the joystick is enabled by default without needing '--js' flag.
USE_JOYSTICK_AS_DEFAULT = True

# The maximum throttle output (0.0 to 1.0) allowed by the joystick.
# Useful for limiting speed for beginners.
JOYSTICK_MAX_THROTTLE = 0.5

# Scalar for steering. 1.0 is normal. <1.0 is less sensitive.
JOYSTICK_STEERING_SCALE = 1.0

# The "deadzone" where small joystick movements are ignored (0.0 to 1.0).
JOYSTICK_DEADZONE = 0.01

# Set to -1.0 to flip forward/backward direction on the joystick.
JOYSTICK_THROTTLE_DIR = -1.0

# The linux device file for the joystick.
JOYSTICK_DEVICE_FILE = "/dev/input/js0"

# The type of controller being used.
# Options: 'ps3', 'ps4', 'xbox', 'nimbus', 'wiiu', 'F710', 'rc3', 'MM1 (use for RC Hat)', 'custom'
CONTROLLER_TYPE = 'xbox'

# Enable listening for remote joystick control over the network.
USE_NETWORKED_JS = False
NETWORK_JS_SERVER_IP = None


# ------------------------------------------------------------------------------
# DRIVE TRAIN CONFIGURATION
# ------------------------------------------------------------------------------

# DRIVE_TRAIN_TYPE
# These options specify which chasis and motor setup you are using.
# See Actuators documentation https://docs.donkeycar.com/parts/actuators/
# for a detailed explanation of each drive train type and it's configuration.
# Choose one of the following and then update the related configuration section:
#
# "PWM_STEERING_THROTTLE" uses two PWM output pins to control a steering servo and an ESC, as in a standard RC car.
# "MM1" Robo HAT MM1 board
# "SERVO_HBRIDGE_2PIN" Servo for steering and HBridge motor driver in 2pin mode for motor
# "SERVO_HBRIDGE_3PIN" Servo for steering and HBridge motor driver in 3pin mode for motor
# "DC_STEER_THROTTLE" uses HBridge pwm to control one steering dc motor, and one drive wheel motor
# "DC_TWO_WHEEL" uses HBridge in 2-pin mode to control two drive motors, one on the left, and one on the right.
# "DC_TWO_WHEEL_L298N" using HBridge in 3-pin mode to control two drive motors, one of the left and one on the right.
# "MOCK" no drive train.  This can be used to test other features in a test rig.
# "VESC" VESC Motor controller to set servo angle and duty cycle

# Select the drive train type. This determines how the software talks to the motors.
# "PWM_STEERING_THROTTLE": Standard RC car (Servo + ESC)
# "MM1": RoboHat MM1 or RC Hat
# "SERVO_HBRIDGE_2PIN": Servo for steering, HBridge (2 pin) for motor
# "SERVO_HBRIDGE_3PIN": Servo for steering, HBridge (3 pin) for motor
# "DC_STEER_THROTTLE": DC Motor for steering, DC Motor for drive (L298N)
# "DC_TWO_WHEEL": Differential drive (tank style), 2 Pin HBridge
# "DC_TWO_WHEEL_L298N": Differential drive (tank style), 3 Pin HBridge
# "VESC": VESC Motor Controller
DRIVE_TRAIN_TYPE = "PWM_STEERING_THROTTLE"

# Configuration for PWM_STEERING_THROTTLE (Standard RC Car)
# Drive train for RC car with a steering servo and ESC.
# Uses a PwmPin for steering (servo) and a second PwmPin for throttle (ESC)
# Base PWM Frequence is presumed to be 60hz; use PWM_xxxx_SCALE to adjust pulse with for non-standard PWM frequencies
# Requires calibration using 'donkey calibrate'.
PWM_STEERING_THROTTLE = {
	"PWM_STEERING_PIN": "PCA9685.1:40.1",   # Pin for steering servo
	"PWM_STEERING_SCALE": 1.0,              # PWM frequency compensation
	"PWM_STEERING_INVERTED": False,         # Invert steering direction
	"PWM_THROTTLE_PIN": "PCA9685.1:40.0",   # Pin for ESC (Throttle)
	"PWM_THROTTLE_SCALE": 1.0,              # PWM frequency compensation
	"PWM_THROTTLE_INVERTED": False,         # Invert throttle direction
	"STEERING_LEFT_PWM": 460,               # Calibrated value: Full Left
	"STEERING_RIGHT_PWM": 290,              # Calibrated value: Full Right
	"THROTTLE_FORWARD_PWM": 500,            # Calibrated value: Max Forward
	"THROTTLE_STOPPED_PWM": 370,            # Calibrated value: Stopped
	"THROTTLE_REVERSE_PWM": 220,            # Calibrated value: Max Reverse
}

#
# SERVO_HBRIDGE_2PIN
# - configures a steering servo and an HBridge in 2pin mode (2 pwm pins)
# - Servo takes a standard servo PWM pulse between 1 millisecond (fully reverse)
#   and 2 milliseconds (full forward) with 1.5ms being neutral.
# - the motor is controlled by two pwm pins, 
#   one for forward and one for backward (reverse). 
# - the pwm pin produces a duty cycle from 0 (completely LOW)
#   to 1 (100% completely high), which is proportional to the
#   amount of power delivered to the motor.
# - in forward mode, the reverse pwm is 0 duty_cycle,
#   in backward mode, the forward pwm is 0 duty cycle.
# - both pwms are 0 duty cycle (LOW) to 'detach' motor and 
#   and glide to a stop.
# - both pwms are full duty cycle (100% HIGH) to brake
#
# Pin specifier string format:
# - use RPI_GPIO for RPi/Nano header pin output
#   - use BOARD for board pin numbering
#   - use BCM for Broadcom GPIO numbering
#   - for example "RPI_GPIO.BOARD.18"
# - use PIPGIO for RPi header pin output using pigpio server
#   - must use BCM (broadcom) pin numbering scheme
#   - for example, "PIGPIO.BCM.13"
# - use PCA9685 for PCA9685 pin output
#   - include colon separated I2C channel and address 
#   - for example "PCA9685.1:40.13"
# - RPI_GPIO, PIGPIO and PCA9685 can be mixed arbitrarily,
#   although it is discouraged to mix RPI_GPIO and PIGPIO.
#
# Configuration for SERVO_HBRIDGE_2PIN
SERVO_HBRIDGE_2PIN = {
	"FWD_DUTY_PIN": "RPI_GPIO.BOARD.18",  # Pin for Forward
	"BWD_DUTY_PIN": "RPI_GPIO.BOARD.16",  # Pin for Reverse
	"PWM_STEERING_PIN": "RPI_GPIO.BOARD.33", # Pin for Servo
	"PWM_STEERING_SCALE": 1.0,
	"PWM_STEERING_INVERTED": False,
	"STEERING_LEFT_PWM": 460,
	"STEERING_RIGHT_PWM": 290,
}

#
# SERVO_HBRIDGE_3PIN
# - configures a steering servo and an HBridge in 3pin mode (2 ttl pins, 1 pwm pin)
# - Servo takes a standard servo PWM pulse between 1 millisecond (fully reverse)
#   and 2 milliseconds (full forward) with 1.5ms being neutral.
# - the motor is controlled by three pins, 
#   one ttl output for forward, one ttl output 
#   for backward (reverse) enable and one pwm pin
#   for motor power.
# - the pwm pin produces a duty cycle from 0 (completely LOW)
#   to 1 (100% completely high), which is proportional to the
#   amount of power delivered to the motor.
# - in forward mode, the forward pin  is HIGH and the
#   backward pin is LOW,
# - in backward mode, the forward pin is LOW and the 
#   backward pin is HIGH.
# - both forward and backward pins are LOW to 'detach' motor 
#   and glide to a stop.
# - both forward and backward pins are HIGH to brake
#
# Pin specifier string format:
# - use RPI_GPIO for RPi/Nano header pin output
#   - use BOARD for board pin numbering
#   - use BCM for Broadcom GPIO numbering
#   - for example "RPI_GPIO.BOARD.18"
# - use PIPGIO for RPi header pin output using pigpio server
#   - must use BCM (broadcom) pin numbering scheme
#   - for example, "PIGPIO.BCM.13"
# - use PCA9685 for PCA9685 pin output
#   - include colon separated I2C channel and address 
#   - for example "PCA9685.1:40.13"
# - RPI_GPIO, PIGPIO and PCA9685 can be mixed arbitrarily,
#   although it is discouraged to mix RPI_GPIO and PIGPIO.
#
# Configuration for SERVO_HBRIDGE_3PIN
SERVO_HBRIDGE_3PIN = {
	"FWD_PIN": "RPI_GPIO.BOARD.18",   # Enable Forward
	"BWD_PIN": "RPI_GPIO.BOARD.16",   # Enable Reverse
	"DUTY_PIN": "RPI_GPIO.BOARD.35",  # Speed Control (PWM)
	"PWM_STEERING_PIN": "RPI_GPIO.BOARD.33",
	"PWM_STEERING_SCALE": 1.0,
	"PWM_STEERING_INVERTED": False,
	"STEERING_LEFT_PWM": 460,
	"STEERING_RIGHT_PWM": 290,
}

#
# DC_STEER_THROTTLE with one motor as steering, one as drive
# - uses L298N type motor controller in two pin wiring
#   scheme utilizing two pwm pins per motor; one for 
#   forward(or right) and one for reverse (or left)
# 
# GPIO pin configuration for the DRIVE_TRAIN_TYPE=DC_STEER_THROTTLE
# - use RPI_GPIO for RPi/Nano header pin output
#   - use BOARD for board pin numbering
#   - use BCM for Broadcom GPIO numbering
#   - for example "RPI_GPIO.BOARD.18"
# - use PIPGIO for RPi header pin output using pigpio server
#   - must use BCM (broadcom) pin numbering scheme
#   - for example, "PIGPIO.BCM.13"
# - use PCA9685 for PCA9685 pin output
#   - include colon separated I2C channel and address 
#   - for example "PCA9685.1:40.13"
# - RPI_GPIO, PIGPIO and PCA9685 can be mixed arbitrarily,
#   although it is discouraged to mix RPI_GPIO and PIGPIO.
#
# Configuration for DC_STEER_THROTTLE (Motor for steering, Motor for drive)
DC_STEER_THROTTLE = {
	"LEFT_DUTY_PIN": "RPI_GPIO.BOARD.18",   # Steer Left
	"RIGHT_DUTY_PIN": "RPI_GPIO.BOARD.16",  # Steer Right
	"FWD_DUTY_PIN": "RPI_GPIO.BOARD.15",    # Drive Forward
	"BWD_DUTY_PIN": "RPI_GPIO.BOARD.13",    # Drive Reverse
}

# DC_TWO_WHEEL pin configuration
# - configures L298N_HBridge_2pin driver
# - two wheels as differential drive, left and right.
# - each wheel is controlled by two pwm pins, 
#   one for forward and one for backward (reverse). 
# - each pwm pin produces a duty cycle from 0 (completely LOW)
#   to 1 (100% completely high), which is proportional to the
#   amount of power delivered to the motor.
# - in forward mode, the reverse pwm is 0 duty_cycle,
#   in backward mode, the forward pwm is 0 duty cycle.
# - both pwms are 0 duty cycle (LOW) to 'detach' motor and 
#   and glide to a stop.
# - both pwms are full duty cycle (100% HIGH) to brake
#
# Pin specifier string format:
# - use RPI_GPIO for RPi/Nano header pin output
#   - use BOARD for board pin numbering
#   - use BCM for Broadcom GPIO numbering
#   - for example "RPI_GPIO.BOARD.18"
# - use PIPGIO for RPi header pin output using pigpio server
#   - must use BCM (broadcom) pin numbering scheme
#   - for example, "PIGPIO.BCM.13"
# - use PCA9685 for PCA9685 pin output
#   - include colon separated I2C channel and address 
#   - for example "PCA9685.1:40.13"
# - RPI_GPIO, PIGPIO and PCA9685 can be mixed arbitrarily,
#   although it is discouraged to mix RPI_GPIO and PIGPIO.
#
# Configuration for DC_TWO_WHEEL (Differential/Tank Drive)
DC_TWO_WHEEL = {
	"LEFT_FWD_DUTY_PIN": "RPI_GPIO.BOARD.18",
	"LEFT_BWD_DUTY_PIN": "RPI_GPIO.BOARD.16",
	"RIGHT_FWD_DUTY_PIN": "RPI_GPIO.BOARD.15",
	"RIGHT_BWD_DUTY_PIN": "RPI_GPIO.BOARD.13",
}

# DC_TWO_WHEEL_L298N pin configuration
# - configures L298N_HBridge_3pin driver
# - two wheels as differential drive, left and right.
# - each wheel is controlled by three pins, 
#   one ttl output for forward, one ttl output 
#   for backward (reverse) enable and one pwm pin
#   for motor power.
# - the pwm pin produces a duty cycle from 0 (completely LOW)
#   to 1 (100% completely high), which is proportional to the
#   amount of power delivered to the motor.
# - in forward mode, the forward pin  is HIGH and the
#   backward pin is LOW,
# - in backward mode, the forward pin is LOW and the 
#   backward pin is HIGH.
# - both forward and backward pins are LOW to 'detach' motor 
#   and glide to a stop.
# - both forward and backward pins are HIGH to brake
#
# GPIO pin configuration for the DRIVE_TRAIN_TYPE=DC_TWO_WHEEL_L298N
# - use RPI_GPIO for RPi/Nano header pin output
#   - use BOARD for board pin numbering
#   - use BCM for Broadcom GPIO numbering
#   - for example "RPI_GPIO.BOARD.18"
# - use PIPGIO for RPi header pin output using pigpio server
#   - must use BCM (broadcom) pin numbering scheme
#   - for example, "PIGPIO.BCM.13"
# - use PCA9685 for PCA9685 pin output
#   - include colon separated I2C channel and address 
#   - for example "PCA9685.1:40.13"
# - RPI_GPIO, PIGPIO and PCA9685 can be mixed arbitrarily,
#   although it is discouraged to mix RPI_GPIO and PIGPIO.
# Configuration for DC_TWO_WHEEL_L298N (Differential Drive 3-pin)
DC_TWO_WHEEL_L298N = {
	"LEFT_FWD_PIN": "RPI_GPIO.BOARD.16",
	"LEFT_BWD_PIN": "RPI_GPIO.BOARD.18",
	"LEFT_EN_DUTY_PIN": "RPI_GPIO.BOARD.22",
	"RIGHT_FWD_PIN": "RPI_GPIO.BOARD.15",
	"RIGHT_BWD_PIN": "RPI_GPIO.BOARD.13",
	"RIGHT_EN_DUTY_PIN": "RPI_GPIO.BOARD.11",
}

# Configuration for VESC Motor Controller
VESC_MAX_SPEED_PERCENT = .2
VESC_SERIAL_PORT = "/dev/ttyACM0"
VESC_HAS_SENSOR = True
VESC_START_HEARTBEAT = True
VESC_BAUDRATE = 115200
VESC_TIMEOUT = 0.05
VESC_STEERING_SCALE = 0.5
VESC_STEERING_OFFSET = 0.5

# Configuration for RoboHat MM1 and RC Hat
MM1_STEERING_MID = 1500
MM1_MAX_FORWARD = 2000
MM1_STOPPED_PWM = 1500
MM1_MAX_REVERSE = 1000
MM1_SHOW_STEERING_VALUE = False
MM1_SERIAL_PORT = '/dev/ttyAMA0'


# ------------------------------------------------------------------------------
# SENSORS & ADD-ONS
# ------------------------------------------------------------------------------

# ODOMETRY: Set to True if you have an encoder/odometer installed.
HAVE_ODOM = False
ENCODER_TYPE = 'GPIO'       # GPIO|Arduino|Astar 
MM_PER_TICK = 12.7625       # Calibration: MM travel per encoder tick
ODOM_PIN = 13               # GPIO pin for encoder
ODOM_DEBUG = False          

# LIDAR: Set to True if you have a LIDAR (RP or YD).
USE_LIDAR = False
LIDAR_TYPE = 'RP'           # (RP|YD)
LIDAR_LOWER_LIMIT = 90      # Angle limit to ignore (e.g. looking back at car)
LIDAR_UPPER_LIMIT = 270

# TFMINI: Short range laser radar.
HAVE_TFMINI = False
TFMINI_SERIAL_PORT = "/dev/serial0" 

# IMU: Inertial Measurement Unit (e.g. MPU6050).
HAVE_IMU = False
IMU_SENSOR = 'mpu6050'      # (mpu6050|mpu9250)
IMU_ADDRESS = 0x68          # I2C address
IMU_DLP_CONFIG = 0          # Digital Lowpass Filter (0-6)

# SOMBRERO HAT: Enable if using the Sombrero Hat.
HAVE_SOMBRERO = False

# LEDS: RGB Status LED configuration.
HAVE_RGB_LED = False
LED_INVERT = False          # True for Common Anode
LED_PIN_R = 12
LED_PIN_G = 10
LED_PIN_B = 16
LED_R = 0
LED_G = 0
LED_B = 1

# Hardware Alert Logic (Blink LED when recording count reached)
REC_COUNT_ALERT = 1000
REC_COUNT_ALERT_CYC = 15
REC_COUNT_ALERT_BLINK_RATE = 0.4 
RECORD_ALERT_COLOR_ARR = [ (0, (1, 1, 1)), (3000, (5, 5, 5)), (5000, (5, 2, 0)), (10000, (0, 5, 0)), (15000, (0, 5, 5)), (20000, (0, 0, 5)) ]
MODEL_RELOADED_LED_R = 100
MODEL_RELOADED_LED_G = 0
MODEL_RELOADED_LED_B = 0


# ==============================================================================
# 2. AI, MODELS & TRAINING
#    (Frameworks, Hyperparams, Transformations, Augmentations)
# ==============================================================================

# TRAINING FUNDAMENTALS

# The DEFAULT_MODEL_TYPE will choose which model will be created at training
# time. This chooses between different neural network designs. You can
# override this setting by passing the command line parameter --type to the
# python manage.py train and drive commands.
# tensorflow models: (linear|categorical|tflite_linear|tensorrt_linear)
# pytorch models: (resnet18)
# The AI framework to use (tensorflow|pytorch).
DEFAULT_AI_FRAMEWORK = 'tensorflow'

# The architecture of the model to use.
# 'linear': Standard regression (predicts steer/throttle floats)
# 'categorical': Classification (bins steer/throttle into categories)
# 'resnet18': Pytorch heavy model
DEFAULT_MODEL_TYPE = 'linear'

# Number of training samples per pass.
BATCH_SIZE = 128

# Percentage of data used for training vs validation (0.8 = 80% train).
TRAIN_TEST_SPLIT = 0.8

# Max training iterations.
MAX_EPOCHS = 100

# Show a plot of loss after training.
SHOW_PLOT = True

# Show text progress bar during training.
VERBOSE_TRAIN = True

# Stop training early if loss stops improving.
USE_EARLY_STOP = True
EARLY_STOP_PATIENCE = 5
MIN_DELTA = .0005

# Print model summary to console.
PRINT_MODEL_SUMMARY = True

# Optimizer (None uses default for framework).
OPTIMIZER = None
LEARNING_RATE = 0.001
LEARNING_RATE_DECAY = 0.0

# Store images as 'ARRAY' (faster), 'BINARY', or 'NOCACHE' (saves RAM).
CACHE_POLICY = 'ARRAY'

# MODEL OPTIMIZATION
# Automatically create TFLite model for faster inference on Pi.
CREATE_TF_LITE = True
CREATE_TENSOR_RT = False
SAVE_MODEL_AS_H5 = False
SEND_BEST_MODEL_TO_PI = False

# Model Pruning (Remove weights to increase speed).
PRUNE_CNN = False
PRUNE_PERCENT_TARGET = 75
PRUNE_PERCENT_PER_ITERATION = 20
PRUNE_VAL_LOSS_DEGRADATION_LIMIT = 0.2
PRUNE_EVAL_PERCENT_OF_DATASET = .05

# MODEL SPECIFIC SETTINGS
#Limits the upper bound of the learned throttle for categorical models.
#For the categorical model, this limits the upper bound of the learned throttle
#it's very IMPORTANT that this value is matched from the training PC config.py and the robot.py
#and ideally wouldn't change once set.
MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.8

# Number of images in a sequence for RNN/3D models.
SEQUENCE_LENGTH = 3

# Transfer Learning options.
FREEZE_LAYERS = False
NUM_LAST_LAYERS_TO_TRAIN = 7


# ------------------------------------------------------------------------------
# AUGMENTATIONS (Applied randomly ONLY during training)
# ------------------------------------------------------------------------------
# List of augmentations to apply. e.g. ['MULTIPLY', 'BLUR']
AUGMENTATIONS = []

# Brightness range for augmentation [-0.2, 0.2].
AUG_BRIGHTNESS_RANGE = 0.2

# Blur range for augmentation (kernel size).
AUG_BLUR_RANGE = (0, 3)


# ------------------------------------------------------------------------------
# TRANSFORMATIONS (Applied during Training AND Inference)
# ------------------------------------------------------------------------------
# Augmentations and Transformations
#
# - Augmentations are changes to the image that are only applied during
#   training and are applied randomly to create more variety in the data.
#   Available augmentations are:
#   - BRIGHTNESS  - modify the image brightness. See [albumentations](https://albumentations.ai/docs/api_reference/augmentations/transforms/#albumentations.augmentations.transforms.RandomBrightnessContrast)
#   - BLUR        - blur the image. See [albumentations](https://albumentations.ai/docs/api_reference/augmentations/blur/transforms/#albumentations.augmentations.blur.transforms.Blur)
#
# - Transformations are changes to the image that apply both in
#   training and at inference.  They are always applied and in
#   the configured order.  Available image transformations are:
#   - Apply a mask to the image:
#     - 'CROP'      - apply rectangular mask to borders of image
#     - 'TRAPEZE'   - apply a trapezoidal mask to image
#   - Apply an enhancement to the image
#     - 'CANNY'     - apply canny edge detection
#     - 'BLUR'      - blur the image
#   - resize the image
#     - 'RESIZE'    - resize to given pixel width and height
#     - 'SCALE'     - resize by given scale factor
#   - change the color space of the image
#     - 'RGB2BGR'   - change color model from RGB to BGR
#     - 'BGR2RGB'   - change color model from BGR to RGB
#     - 'RGB2HSV'   - change color model from RGB to HSV
#     - 'HSV2RGB'   - change color model from HSV to RGB
#     - 'BGR2HSV'   - change color model from BGR to HSV
#     - 'HSV2BGR'   - change color model from HSV to BGR
#     - 'RGB2GRAY'  - change color model from RGB to greyscale
#     - 'BGR2GRAY'  - change color model from BGR to greyscale
#     - 'HSV2GRAY'  - change color model from HSV to greyscale
#     - 'GRAY2RGB'  - change color model from greyscale to RGB
#     - 'GRAY2BGR'  - change color model from greyscale to BGR
#
# You can create custom tranformations and insert them into the pipeline.
# - Use a tranformer label that beings with `CUSTOM`, like `CUSTOM_CROP`
#   and add that to the TRANSFORMATIONS or POST_TRANFORMATIONS list.
#   So for the custom crop example, that might look like this;
#   `POST_TRANSFORMATIONS = ['CUSTOM_CROP']`
# - Set configuration properties for the module and class that
#   implement your custom transformation.
#   - The module config will begin with the transformer label
#     and end with `_MODULE`, like `CUSTOM_CROP_MODULE`.  It's value is
#     the absolute file path to the python file that has the transformer
#     class.  For instance, if you called the file
#     `my_custom_transformer.py` and put in in the root of
#     your `mycar` folder, next to `myconfig.py`, then you would add 
#     the following to your myconfig.py file (keeping with the crop example);
#     `CUSTOM_CROP_MODULE = "/home/pi/mycar/my_custom_transformer.py"`
#     The actual path will depend on what OS you are using and what
#     your user name is.
#   - The class config will begin with the transformer label and end with `_CLASS`,
#     like `CUSTOM_CROP_CLASS`.  So if your class is called `CustomCropTransformer`
#     the you would add the following property to your `myconfig.py` file:
#     `CUSTOM_CROP_CLASS = "CustomCropTransformer"`
# - Your custom class' constructor will take in the Config object to
#   it it's constructor.  So you can add whatever configuration properties
#   you need to your myconfig.py, then read them in the constructor.
#   You can name the properties anything you want, but it is good practice
#   to prefix them with the custom tranformer label so they don't conflict
#   with any other config and so it is way to see what they go with.
#   For instance, in the custom crop example, we would want the border
#   values, so that could look like;
#   ```
#   CUSTOM_CROP_TOP = 45    # rows to ignore on the top of the image
#   CUSTOM_CROP_BOTTOM = 5  # rows ignore on the bottom of the image
#   CUSTOM_CROP_RIGHT = 10  # pixels to ignore on the right of the image
#   CUSTOM_CROP_LEFT = 10   # pixels to ignore on the left of the image
#   ```
# - Your custom class must have a `run` method that takes an image and
#   returns an image.  It is in this method where you will implement your
#   transformation logic.
# - For example, a custom crop that did a blur after the crop might look like;
#   ```
#   from donkeycar.parts.cv import ImgCropMask, ImgSimpleBlur
#
#   class CustomCropTransformer:
#       def __init__(self, config) -> None:
#           self.top = config.CUSTOM_CROP_TOP
#           self.bottom = config.CUSTOM_CROP_BOTTOM
#           self.left = config.CUSTOM_CROP_LEFT
#           self.right = config.CUSTOM_CROP_RIGHT
#           self.crop = ImgCropMask(self.left, self.top, self.right, self.bottom)
#           self.blur = ImgSimpleBlur()
#
#       def run(self, image):
#           image = self.crop.run(image)
#           return self.blur.run(image)
#   ```
#

# Operations applied to the image before it hits the AI.
TRANSFORMATIONS = []
POST_TRANSFORMATIONS = []

# "CROP" Transformation
# Apply mask to borders of the image
# defined by a rectangle.
# If these crops values are too large, they will cause the stride values to
# become negative and the model with not be valid.
# # # # # # # # # # # # #
# xxxxxxxxxxxxxxxxxxxxx #
# xxxxxxxxxxxxxxxxxxxxx #
# xx                 xx # top
# xx                 xx #
# xx                 xx #
# xxxxxxxxxxxxxxxxxxxxx # bottom
# xxxxxxxxxxxxxxxxxxxxx #
# # # # # # # # # # # # #
ROI_CROP_TOP = 45
ROI_CROP_BOTTOM = 0
ROI_CROP_RIGHT = 0
ROI_CROP_LEFT = 0

# "TRAPEZE" tranformation
# Apply mask to borders of image
# defined by a trapezoid.
# # # # # # # # # # # # # #
# xxxxxxxxxxxxxxxxxxxxxxx #
# xxxx ul     ur xxxxxxxx # min_y
# xxx             xxxxxxx #
# xx               xxxxxx #
# x                 xxxxx #
# ll                lr xx # max_y
# # # # # # # # # # # # # #
ROI_TRAPEZE_LL = 0
ROI_TRAPEZE_LR = 160
ROI_TRAPEZE_UL = 20
ROI_TRAPEZE_UR = 140
ROI_TRAPEZE_MIN_Y = 60
ROI_TRAPEZE_MAX_Y = 120

# "CANNY" Edge Detection Settings.
CANNY_LOW_THRESHOLD = 60
CANNY_HIGH_THRESHOLD = 110
CANNY_APERTURE = 3

# "BLUR" Transformation Settings.
BLUR_KERNEL = 5
BLUR_KERNEL_Y = None
BLUR_GAUSSIAN = True

# "RESIZE" / "SCALE" Settings.
RESIZE_WIDTH = 160
RESIZE_HEIGHT = 120
SCALE_WIDTH = 1.0
SCALE_HEIGHT = None


# ==============================================================================
# 3. MODES, FEATURES & OPERATION
#    (Driving modes, Web/Joystick control, Simulation, Logging)
# ==============================================================================

# VEHICLE LOOP
# The main loop frequency (Hz). Hardware is updated this many times per second.
DRIVE_LOOP_HZ = 20

# Max loops to run before quitting (useful for testing, None = infinite).
MAX_LOOPS = None


# AUTOMATION & BEHAVIORS

# Show the image the pilot sees (with overlays) in the web UI.
SHOW_PILOT_IMAGE = False

# Scale all AI throttle output by this multiplier.
AI_THROTTLE_MULT = 1.0

# "Launch Control": Boost throttle for X seconds at start of autonomous mode.
AI_LAUNCH_DURATION = 0.0
AI_LAUNCH_THROTTLE = 0.0
AI_LAUNCH_ENABLE_BUTTON = 'R2'
AI_LAUNCH_KEEP_ENABLED = False

#BEHAVIORS
#When training the Behavioral Neural Network model, make a list of the behaviors,
#Set the TRAIN_BEHAVIORS = True, and use the BEHAVIOR_LED_COLORS to give each behavior a color
TRAIN_BEHAVIORS = False
BEHAVIOR_LIST = ['Left_Lane', "Right_Lane"]
BEHAVIOR_LED_COLORS = [(0, 10, 0), (10, 0, 0)]

#Localizer
#The localizer is a neural network that can learn to predict its location on the track.
#This is an experimental feature that needs more developement. But it can currently be used
#to predict the segement of the course, where the course is divided into NUM_LOCATIONS segments.
TRAIN_LOCALIZER = False
NUM_LOCATIONS = 10
BUTTON_PRESS_NEW_TUB = False


# PATH FOLLOWING (GPS or Odometry based)
PATH_FILENAME = "donkey_path.pkl"
PATH_SCALE = 5.0
PATH_OFFSET = (0, 0)
PATH_MIN_DIST = 0.3
PID_P = -10.0
PID_I = 0.000
PID_D = -0.2
PID_THROTTLE = 0.2
USE_CONSTANT_THROTTLE = False
SAVE_PATH_BTN = "cross"
RESET_ORIGIN_BTN = "triangle"

# STOP SIGN DETECTOR
STOP_SIGN_DETECTOR = False
STOP_SIGN_MIN_SCORE = 0.2
STOP_SIGN_SHOW_BOUNDING_BOX = True
STOP_SIGN_MAX_REVERSE_COUNT = 10
STOP_SIGN_REVERSE_THROTTLE = -0.5


# RECORDING & LOGGING

# Automatically record data when throttle is > 0 (Standard training data collection).
AUTO_RECORD_ON_THROTTLE = True

# Record data even when the AI is driving (Careful: don't train on this data!).
RECORD_DURING_AI = False

# Create a new directory for every session (True) or append to existing (False).
AUTO_CREATE_NEW_TUB = False

# Console logging settings.
HAVE_CONSOLE_LOGGING = True
LOGGING_LEVEL = 'INFO'
LOGGING_FORMAT = '%(message)s'
HAVE_PERFMON = False
SHOW_FPS = False
FPS_DEBUG_INTERVAL = 10


# TELEMETRY (MQTT)
HAVE_MQTT_TELEMETRY = False
TELEMETRY_DONKEY_NAME = 'my_robot1234'
TELEMETRY_MQTT_TOPIC_TEMPLATE = 'donkey/%s/telemetry'
TELEMETRY_MQTT_JSON_ENABLE = False
TELEMETRY_MQTT_BROKER_HOST = 'broker.hivemq.com'
TELEMETRY_MQTT_BROKER_PORT = 1883
TELEMETRY_PUBLISH_PERIOD = 1
TELEMETRY_LOGGING_ENABLE = True
TELEMETRY_LOGGING_LEVEL = 'INFO'
TELEMETRY_LOGGING_FORMAT = '%(message)s'
TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle,recording'
TELEMETRY_DEFAULT_TYPES = 'float,float'


# SIMULATION (DONKEY GYM)
#Only on Ubuntu linux, you can use the simulator as a virtual donkey and
#issue the same python manage.py drive command as usual, but have them control a virtual car.
#This enables that, and sets the path to the simualator and the environment.
#You will want to download the simulator binary from: https://github.com/tawnkramer/donkey_gym/releases/download/v18.9/DonkeySimLinux.zip
#then extract that and modify DONKEY_SIM_PATH.

# Settings for connecting to the Donkey Gym Unity simulator.
DONKEY_GYM = False
DONKEY_SIM_PATH = "path to sim"
DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0"
GYM_CONF = { "body_style" : "donkey", "body_rgb" : (128, 128, 128), "car_name" : "car", "font_size" : 100}
GYM_CONF["racer_name"] = "Your Name"
GYM_CONF["country"] = "Place"
GYM_CONF["bio"] = "I race robots."
SIM_HOST = "127.0.0.1"
SIM_ARTIFICIAL_LATENCY = 0
SIM_RECORD_LOCATION = False
SIM_RECORD_GYROACCEL = False
SIM_RECORD_VELOCITY = False
SIM_RECORD_LIDAR = False
PUB_CAMERA_IMAGES = False       # Publish camera over network
USE_FPV = False                 # send camera data to FPV webserver


# PI CONNECTION
PI_USERNAME = "pi"
PI_HOSTNAME = "donkeypi.local"


# WEB CONTROL
# The port for the web server (default 8887).
WEB_CONTROL_PORT = int(os.getenv("WEB_CONTROL_PORT", 8887))

# Initial mode on startup.
# 'user': Human control
# 'local_angle': AI Steering, Human Throttle
# 'local': AI Steering and Throttle
WEB_INIT_MODE = "user"
