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
MAX_LOOPS = 100000

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

#TRAINING
DEFAULT_MODEL_TYPE = 'linear' #(linear|categorical|rnn|imu|behavior|3d|localizer|latent)
BATCH_SIZE = 128
TRAIN_TEST_SPLIT = 0.8
MAX_EPOCHS = 100
SHOW_PLOT = True
VERBOSE_TRAIN = True
USE_EARLY_STOP = True
EARLY_STOP_PATIENCE = 5
MIN_DELTA = .0005
PRINT_MODEL_SUMMARY = True      #print layers and weights to stdout
OPTIMIZER = None                #adam, sgd, rmsprop, etc.. None accepts default
LEARNING_RATE = 0.001           #only used when OPTIMIZER specified
LEARNING_RATE_DECAY = 0.0       #only used when OPTIMIZER specified
CACHE_IMAGES = True             #keep images in memory. will speed succesive epochs, but crater if not enough mem.
PRUNE_CNN = False
PRUNE_PERCENT_TARGET = 75 # The desired percentage of pruning.
PRUNE_PERCENT_PER_ITERATION = 20 # Percenge of pruning that is perform per iteration.
PRUNE_VAL_LOSS_DEGRADATION_LIMIT = 0.2 # The max amout of validation loss that is permitted during pruning.
PRUNE_EVAL_PERCENT_OF_DATASET = .05  # percent of dataset used to perform evaluation of model.

#model transfer options
FREEZE_LAYERS = False
NUM_LAST_LAYERS_TO_TRAIN = 7

#For the categorical model, this limits the upper bound of the learned throttle
#it's very IMPORTANT that this value is matched from the training PC config.py and the robot.py
#and ideally wouldn't change once set.
MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.5

#RNN or 3D
SEQUENCE_LENGTH = 3

#SOMBRERO
HAVE_SOMBRERO = False

#RECORD OPTIONS
RECORD_DURING_AI = False
