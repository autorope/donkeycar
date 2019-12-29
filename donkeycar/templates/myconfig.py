# If desired, all config overrides can be specified here. 
# The update operation will not touch this file.
# """

DRIVE_LOOP_HZ = 15
CAMERA_FRAMERATE = DRIVE_LOOP_HZ

CSIC_IMAGE_W = 224
CSIC_IMAGE_H = 224
CSIC_CAM_GSTREAMER_FLIP_PARM = 6 # flip CSIC camera vertically

# #RealSense CAMERA
D435_IMAGE_W = 424 
D435_IMAGE_H = 240
D435_IMG_TYPE = "color"
D435_FRAME_RATE = DRIVE_LOOP_HZ

T265_IMAGE_W = 240
T265_IMAGE_H = 140
T265_FOV=120 

#USE_RS_IMU = False
SAVE_ROUTE_BTN = 'y_button'        # joystick button to save path
SAVE_WPT_BTN = 'x_button'
RS_PATH_PLANNER = True
RS_ROUTE_FILE = 'rs_route.pkl'
CLEAR_ROUTE_BTN = 'options'
PATH_MIN_DIST = 0.3                # after travelling this distance (m), save a path point
PATH_SCALE = 20
PID_P = -2.5                       # proportional mult for PID path follower
PID_I = 0.0                        # integral mult for PID path follower
PID_D = 0.0                        # differential mult for PID path follower
PID_THROTTLE = 0.3                 # constant throttle value during path following
WPT_TOLERANCE = 0.25

# PWM driver
PCA9685_I2C_BUSNUM = 1 

# #STEERING - Dakar
STEERING_CHANNEL = 0            #channel on the 9685 pwm board 0-15
STEERING_LEFT_PWM = 540         #pwm value for full left steering
STEERING_RIGHT_PWM = 250        #pwm value for full right steering

# #THROTTLE - Dakar
THROTTLE_CHANNEL = 1            #channel on the 9685 pwm board 0-15
THROTTLE_FORWARD_PWM = 480      #pwm value for max forward throttle
THROTTLE_STOPPED_PWM = 390      #pwm value for no movement
THROTTLE_REVERSE_PWM = 300      #pwm value for max reverse throttle

DEFAULT_MODEL_TYPE = 'rnn'   #(linear|categorical|rnn|imu|motion|behavior|3d|localizer|latent)

CONTROLLER_TYPE='xbox'               #(ps3|ps4|xbox|nimbus|wiiu|F710|rc3)# import os
AUTO_RECORD_ON_THROTTLE = False      #if true, we will record whenever throttle is not zero. 
                                     #if false, you must manually toggle recording with button b on xbox ctrl.