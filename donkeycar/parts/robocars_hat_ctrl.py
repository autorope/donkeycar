from datetime import datetime
import donkeycar as dk
import re
import time
import logging
from donkeycar.utils import Singleton
import numpy as np
from donkeycar.parts.actuator import RobocarsHat
from donkeycar.utilities.logger import init_special_logger
import socket
import errno
import sys
import fcntl,os

mylogger = init_special_logger ("Rx")
mylogger.setLevel(logging.INFO)

def map_range(x, X_min, X_max, Y_min, Y_max):
    '''
    Linear mapping between two ranges of values
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    x=max(min(x,X_max),X_min)
    return ((x-X_min) / XY_ratio + Y_min)

def map_range_float(x, X_min, X_max, Y_min, Y_max):
    '''
    Same as map_range but supports floats return, rounded to 2 decimal places
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    x=max(min(x,X_max),X_min)
    y = ((x-X_min) / XY_ratio + Y_min)

    # print("y= {}".format(y))

    return round(y,2)

def dualMap (input, input_min, input_idle, input_max, output_min, output_idle, output_max) :
    if (input < input_idle) :
        output = map_range (input, input_min, input_idle, output_min, output_idle)
    elif (input>input_idle) :
        output = map_range (input, input_idle, input_max, output_idle, output_max)
    else:
        output = output_idle
    return output

class RobocarsHatIn(metaclass=Singleton):

    def __init__(self, cfg):
        self.cfg = cfg
        self.sensor = RobocarsHat(self.cfg)
        self.last_rxch_msg = None
        self.last_battery_msg=None
        self.last_sensors_msg=None
        self.last_calibration_msg=None

    def getCommand(self):
        cmds = self.sensor.readline()
        if cmds != None and len(cmds)>0:
            for l in cmds:
                params = l.split(',')
                if len(params) == 5 and int(params[0])==1 : # Radio CHannels
                    self.last_rxch_msg = l
                if len(params) == 3 and int(params[0])==3 : # Calibration
                    self.last_calibration_msg = l
                if len(params) == 3 and int(params[0])==2 : # Sensors
                    self.last_sensors_msg = l
                if len(params) == 5 and int(params[0])==0 : # Battery
                    self.last_battery_msg = l

    def getRxCh(self):
        self.getCommand()
        return self.last_rxch_msg
    
    def getBattery(self):
        self.getCommand()
        return self.last_battery_msg

    def getSensors(self):
        self.getCommand()
        return self.last_sensors_msg

    def getCalibration(self):
        self.getCommand()
        return self.last_calibration_msg

class RobocarsHatInCtrl:
    AUX_FEATURE_NONE=0
    AUX_FEATURE_RECORDandPILOT=1
    AUX_FEATURE_RECORD=2
    AUX_FEATURE_PILOT=3
    AUX_FEATURE_THROTTLEEXP=4
    AUX_FEATURE_STEERINGEXP=5
    AUX_FEATURE_OUTPUT_STEERING_TRIM=6
    AUX_FEATURE_OUTPUT_STEERING_EXP=7
    AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE=8

    def _map_aux_feature (self, feature):
        if feature == 'record/pilot':
            return self.AUX_FEATURE_RECORDandPILOT
        elif feature == 'record':
            return self.AUX_FEATURE_RECORD
        elif feature == 'pilot':
            return self.AUX_FEATURE_PILOT
        elif feature == 'throttle_exploration':
            return self.AUX_FEATURE_THROTTLEEXP
        elif feature == 'steering_exploration':
            return self.AUX_FEATURE_STEERINGEXP
        elif feature == 'output_steering_trim':
            return self.AUX_FEATURE_OUTPUT_STEERING_TRIM
        elif feature == 'output_steering_exp':
            return self.AUX_FEATURE_OUTPUT_STEERING_EXP
        elif feature == 'local_angle_fix_throttle':
            return self.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE

    def __init__(self, cfg):

        self.cfg = cfg
        self.inSteering = 0.0
        self.inThrottle = 0.0
        self.fixThrottle = 0.0
        self.fixSteering = 0.0
        self.fixOutputSteeringTrim = None
        self.fixOutputSteering = None
        self.inAux1 = 0.0
        self.inAux2 = 0.0
        self.lastAux1 = -1.0
        self.lastAux2 = -1.0
        self.recording=False
        self.mode = 'user'
        self.lastMode = self.mode
        self.applyBrake = 0
        self.lastPilotThrottle = 0.0

        if (self.cfg.ROBOCARSHAT_USE_AUTOCALIBRATION==True) :
            self.inThrottleIdle = -1
            self.inSteeringIdle = -1
        else:
            self.inThrottleIdle = 1500
            self.inSteeringIdle = 1500

        self.inSpeed = 0

        #Aux feature
        self.ch3Feature = self.AUX_FEATURE_NONE
        self.ch4Feature = self.AUX_FEATURE_NONE

        self.ch3Feature = self._map_aux_feature (self.cfg.ROBOCARSHAT_CH3_FEATURE)
        self.ch4Feature = self._map_aux_feature (self.cfg.ROBOCARSHAT_CH4_FEATURE)
        if (self.ch3Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM) or (self.ch4Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM):
            self.fixOutputSteeringTrim = 1500
        if (self.ch3Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP) or (self.ch4Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP):
            self.fixOutputSteering = 1500

        if self.cfg.ROBOCARSHAT_THROTTLE_DISCRET != None:
            self.discretesThrottle = np.arange(0.0,1.0001,1.0/len(self.cfg.ROBOCARSHAT_THROTTLE_DISCRET))
            self.discretesThrottle[1]=0.1 #fix first threshold 
            mylogger.info("CtrlIn Discrete throttle thresholds set to {}".format(self.discretesThrottle))

        self.hatInMsg = RobocarsHatIn(self.cfg)
        self.hatActuator = RobocarsHat(self.cfg)
        self.on = True

    def processRxCh(self):
        rxch_msg = self.hatInMsg.getRxCh()
        if rxch_msg:
            params = rxch_msg.split(',')
            if len(params) == 5 and int(params[0])==1 :
                if params[1].isnumeric() and self.inThrottleIdle != -1:
                    if (self.cfg.ROBOCARSHAT_USE_AUTOCALIBRATION==True) :
                        self.inThrottle = dualMap(int(params[1]),
                                self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MIN, self.inThrottleIdle, self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MAX,
                            -1, 0, 1)
                    else :
                        self.inThrottle = map_range(int(params[1]),
                                self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MIN, self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MAX,
                            -1, 1)

                if params[2].isnumeric() and self.inSteeringIdle != -1:
                    if (self.cfg.ROBOCARSHAT_USE_AUTOCALIBRATION==True) :
                        self.inSteering = dualMap(int(params[2]),
                                self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MIN, self.inSteeringIdle, self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MAX,
                            -1, 0, 1)
                    else:
                        self.inSteering = map_range(int(params[2]),
                            self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MIN, self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MAX,
                            -1, 1)

                if params[3].isnumeric():
                    self.inAux1 = map_range(int(params[3]),
                        self.cfg.ROBOCARSHAT_PWM_IN_AUX_MIN, self.cfg.ROBOCARSHAT_PWM_IN_AUX_MAX,
                        -1, 1)
                if params[4].isnumeric():
                    self.inAux2 = map_range(int(params[4]),
                        self.cfg.ROBOCARSHAT_PWM_IN_AUX_MIN, self.cfg.ROBOCARSHAT_PWM_IN_AUX_MAX,
                        -1, 1)

                mylogger.debug("CtrlIn PWM {} {} {} {}".format(int(params[1]), int(params[2]), int(params[3]), int(params[4])))
                mylogger.debug("CtrlIn Std {} {} {} {}".format(self.inThrottle, self.inSteering, self.inAux1, self.inAux2))

    def processCalibration(self):
        cal_msg = self.hatInMsg.getCalibration()
        if cal_msg:
            params = cal_msg.split(',')
            if len(params) == 3 and int(params[0])==3 :
                if params[1].isnumeric():
                    self.inThrottleIdle = int(params[1])
                if params[2].isnumeric():
                    self.inSteeringIdle = int(params[2])
                mylogger.debug("CtrlIn Idle {} {} ".format(int(params[1]), int(params[2])))

    def getCommand(self):
        self.processRxCh()
        self.processCalibration()

    def processAltModes(self):
        self.recording=False
        self.mode='user'
        user_throttle = self.inThrottle
        user_steering = self.inSteering
        pilot_throttle = 0.0

        #Process Aux ch3
        if self.ch3Feature == self.AUX_FEATURE_RECORDandPILOT :

            if (self.inAux1<-0.5):
                self.recording=True
            if (self.inAux1>0.5):
                self.mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                pilot_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

        elif self.ch3Feature == self.AUX_FEATURE_RECORD :
            if self.inAux1 > 0.5:
                self.recording=True

        elif self.ch3Feature == self.AUX_FEATURE_PILOT :
            if self.inAux1 > 0.5:
                self.mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                pilot_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

        elif self.ch3Feature == self.AUX_FEATURE_THROTTLEEXP :
            if (abs(self.lastAux1 - self.inAux1)>0.5) :
                if self.inAux1 > 0.5:
                    self.fixThrottle = min(self.fixThrottle+self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
                if self.inAux1 < -0.5:
                    self.fixThrottle = max(self.fixThrottle-self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,0.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
            user_throttle = self.fixThrottle

        elif self.ch3Feature == self.AUX_FEATURE_STEERINGEXP :
            if (abs(self.lastAux1 - self.inAux1)>0.5) :
                if self.inAux1 > 0.5:
                    self.fixSteering = min(self.fixSteering+self.cfg.ROBOCARSHAT_STEERING_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
                if self.inAux1 < -0.5:
                    self.fixSteering = max(self.fixSteering-self.cfg.ROBOCARSHAT_STEERING_EXP_INC,-1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
                user_steering = self.fixSteering            

        elif self.ch3Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM :
            if (abs(self.lastAux1 - self.inAux1)>0.5) :
                if self.inAux1 > 0.5:
                    self.fixOutputSteeringTrim = min(self.fixOutputSteeringTrim+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                if self.inAux1 < -0.5:
                    self.fixOutputSteeringTrim = max(self.fixOutputSteeringTrim-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                self.hatActuator.setSteeringTrim (self.fixOutputSteeringTrim)            

        elif self.ch3Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP :
            if (abs(self.lastAux1 - self.inAux1)>0.5) :
                if self.inAux1 > 0.5:
                    self.fixOutputSteering = min(self.fixOutputSteering+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                if self.inAux1 < -0.5:
                    self.fixOutputSteering = max(self.fixOutputSteering-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                self.hatActuator.setFixSteering (self.fixOutputSteering)            

        elif self.ch3Feature == self.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE and self.mode!='user':
            # take precedence on pilot and record&pilot features
            pilot_throttle =  map_range_float(self.inAux1,
                        -1.0, 1.0,
                        self.cfg.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE_MIN, self.cfg.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE_MAX)

        # Process aux ch4
        if self.ch4Feature == self.AUX_FEATURE_RECORDandPILOT :

            if (self.inAux2<-0.5):
                self.recording=True
            if (self.inAux2>0.5):
                self.mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                pilot_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

        elif self.ch4Feature == self.AUX_FEATURE_RECORD :
            if self.inAux2 > 0.5:
                self.recording=True

        elif self.ch4Feature == self.AUX_FEATURE_PILOT :
            if self.inAux2 > 0.5:
                self.mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                pilot_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

        elif self.ch4Feature == self.AUX_FEATURE_THROTTLEEXP :
            if (abs(self.lastAux2 - self.inAux2)>0.5) :
                if self.inAux2 > 0.5:
                    self.fixThrottle = min(self.fixThrottle+self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
                if self.inAux2 < -0.5:
                    self.fixThrottle = max(self.fixThrottle-self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,0.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
            user_throttle = self.fixThrottle

        elif self.ch4Feature == self.AUX_FEATURE_STEERINGEXP :
            if (abs(self.lastAux2 - self.inAux2)>0.5) :
                if self.inAux2 > 0.5:
                    self.fixSteering = min(self.fixSteering+self.cfg.ROBOCARSHAT_STEERING_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
                if self.inAux2 < -0.5:
                    self.fixSteering = max(self.fixSteering-self.cfg.ROBOCARSHAT_STEERING_EXP_INC,-1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
                user_steering = self.fixSteering            

        elif self.ch4Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM :
            if (abs(self.lastAux2 - self.inAux2)>0.5) :
                if self.inAux2 > 0.5:
                    self.fixOutputSteeringTrim = min(self.fixOutputSteeringTrim+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                if self.inAux2 < -0.5:
                    self.fixOutputSteeringTrim = max(self.fixOutputSteeringTrim-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                self.hatActuator.setSteeringTrim (self.fixOutputSteeringTrim)            

        elif self.ch4Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP :
            if (abs(self.lastAux2 - self.inAux2)>0.5) :
                if self.inAux2 > 0.5:
                    self.fixOutputSteering = min(self.fixOutputSteering+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                if self.inAux2 < -0.5:
                    self.fixOutputSteering = max(self.fixOutputSteering-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                self.hatActuator.setFixSteering (self.fixOutputSteering)            

        elif self.ch4Feature == self.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE and self.mode!='user':
            # take precedence on pilot and record&pilot features
            pilot_throttle =  map_range_float(self.inAux2,
                        -1.0, 1.0,
                        self.cfg.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE_MIN, self.cfg.AUX_FEATURE_LOCAL_ANGLE_FIX_THROTTLE_MAX)
                        
        if self.cfg.ROBOCARSHAT_STEERING_FIX != None:
            user_steering = self.cfg.ROBOCARSHAT_STEERING_FIX

        # Discret throttle mode
        if self.mode=='user':
            # Discret mode, apply profile
            if self.cfg.ROBOCARSHAT_THROTTLE_DISCRET != None :
                inds = np.digitize(user_throttle, self.discretesThrottle)
                inds = min(max(inds,1), len(self.cfg.ROBOCARSHAT_THROTTLE_DISCRET))
                user_throttle = self.cfg.ROBOCARSHAT_THROTTLE_DISCRET[inds-1]
            else:
                # direct throttle from remote control, Keep throttle in authorized range
                if self.cfg.ROBOCARSHAT_THROTTLE_FLANGER != None :
                    user_throttle = dualMap(user_throttle,
                    -1, 0, 1,
                    self.cfg.ROBOCARSHAT_THROTTLE_FLANGER[0], 0, self.cfg.ROBOCARSHAT_THROTTLE_FLANGER[1])

        # when in pilot mode, if enabled, apply output throttle proportionnaly to current throttle value from controller
        if self.mode!='user': 
            if self.cfg.ROBOCARSHAT_USER_CONTROLED_LOCAL_ANGLE_THROTTLE:
                pilot_throttle =  map_range_float(user_throttle,
                    0.0, 1.0,
                    self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE, self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE_MAX)
            if (abs(pilot_throttle - self.lastPilotThrottle)>0.01) :
                mylogger.info("CtrlIn user throttle in pilot mode set to {}".format(pilot_throttle))
            self.lastPilotThrottle = pilot_throttle
            user_throttle = pilot_throttle
            mylogger.debug("CtrlIn user throttle in pilot mode set to {}".format(user_throttle))


        #if switching back to user, then apply brake
        if self.mode=='user' and self.lastMode != 'user' and self.cfg.ROBOCARSHAT_BRAKE_ON_IDLE_THROTTLE != None:
            self.applyBrake=10 #brake duration

        self.lastMode = self.mode
        self.lastAux1 = self.inAux1
        self.lastAux2 = self.inAux2
        
        if self.applyBrake>0:
            user_throttle = self.cfg.ROBOCARSHAT_BRAKE_ON_IDLE_THROTTLE
            self.applyBrake-=1

        return user_throttle, user_steering

    def update(self):

        while self.on:
            start = datetime.now()
            self.getCommand()
            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        user_throttle, user_steering = self.processAltModes ()
        return user_steering, user_throttle, self.mode, self.recording, self.inSpeed

    def run (self):
        self.getCommand()
        user_throttle, user_steering = self.processAltModes ()
        return user_steering, user_throttle, self.mode, self.recording, self.inSpeed
    

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping Robocars Hat Controller')
        time.sleep(.5)

class RobocarsHatInOdom:

    def __init__(self, cfg):

        self.cfg = cfg
        self.inSpeed = 0
        self.hatInMsg = RobocarsHatIn(self.cfg)
        self.on = True

    def processSensors(self):
        odom_msg = self.hatInMsg.getSensors()
        if odom_msg:
            params = odom_msg.split(',')
            if len(params) == 3 and int(params[0])==2 :
                mylogger.debug("CtrlIn Sensors {} {} ".format(int(params[1]), int(params[2])))
                if params[2].isnumeric():
                    self.inSpeed = map_range(min(abs(int(params[2])),self.cfg.ROBOCARSHAT_ODOM_IN_MAX),
                                0, self.cfg.ROBOCARSHAT_ODOM_IN_MAX,
                            1, 0)

    def getCommand(self):
        self.processSensors()

    def update(self):

        while self.on:
            start = datetime.now()
            self.getCommand()
            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        return self.inSpeed

    def run (self):
        self.getCommand()
        return self.inSpeed
    

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping Robocars Hat Controller')
        time.sleep(.5)

class RobocarsHatLedCtrl():
    NUM_LED=6
    INDEX_LED_1=0
    INDEX_LED_2=1
    INDEX_LED_3=2
    INDEX_LED_4=3
    INDEX_LED_5=4
    INDEX_LED_6=5

    STEERING_HIGH=0.4
    STEERING_LOW=0.2
    
    STEERING_LEFT=1
    STEERING_RIGHT=-1

    TURN_LIGHT=(223,128,0)
    USER_FRONT_LIGH=(127,127,127)
    AUTO_FRONT_LIGH=(127,127,160)


    def __init__(self, cfg):
        self.cfg = cfg
        self.cmdinterface = RobocarsHat(self.cfg)
        if cfg.ROBOCARSHAT_LED_MODEL == 'Alpine':
            self.LED_INDEX_FRONT_TURN_RIGHT = 3
            self.LED_INDEX_FRONT_TURN_LEFT = 4
            self.LED_INDEX_REAR_TURN_RIGHT = 1
            self.LED_INDEX_REAR_TURN_LEFT = 0
            self.LED_FRONT_LIGHT_RIGHT = 2
            self.LED_FRONT_LIGHT_LEFT = 5

        else: #default
            self.LED_INDEX_FRONT_TURN_RIGHT = 0
            self.LED_INDEX_FRONT_TURN_LEFT = 1
            self.LED_INDEX_REAR_TURN_RIGHT = 2
            self.LED_INDEX_REAR_TURN_LEFT = 3
            self.LED_FRONT_LIGHT_RIGHT = 4
            self.LED_FRONT_LIGHT_LEFT = 5


        self.idx = 0
        self.last_mode = None
        self.last_steering_state = 0

    def setLed(self, i, r, v, b, timing):
        cmd=("2,%d,%d,%d,%d,%d\n" % (int(i), int(r), int(v), int(b), int(timing))).encode('ascii')
        self.cmdinterface.sendCmd(cmd)

    def updateAnim(self):
        self.setLed(int(self.idx/10), 0, 0, 0, 0x0);
        self.idx=(self.idx+1)%(self.NUM_LED*10)
        self.setLed(int(self.idx/10), 255, 0, 0, 0xffff);
    
    def update(self):
        while self.on:
            start = datetime.now()
            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self, steering, throttle, mode):
        #self.updateAnim()
        return None

    def run (self, steering, throttle, mode):
        if self.last_mode == None:
            self.setLed(self.INDEX_LED_1, 0, 0, 0, 0x0);
            self.setLed(self.INDEX_LED_2, 0, 0, 0, 0x0);
            self.setLed(self.INDEX_LED_3, 0, 0, 0, 0x0);
            self.setLed(self.INDEX_LED_4, 0, 0, 0, 0x0);
            self.setLed(self.INDEX_LED_5, 0, 0, 0, 0x0);
            self.setLed(self.INDEX_LED_6, 0, 0, 0, 0x0);

        if mode != self.last_mode:
            if mode=='user' :
                self.setLed(self.LED_FRONT_LIGHT_RIGHT, *self.USER_FRONT_LIGH, 0xffff);
                self.setLed(self.LED_FRONT_LIGHT_LEFT, *self.USER_FRONT_LIGH, 0xffff);
            else:
                self.setLed(self.LED_FRONT_LIGHT_RIGHT, *self.AUTO_FRONT_LIGH, 0xffff);
                self.setLed(self.LED_FRONT_LIGHT_LEFT, *self.AUTO_FRONT_LIGH, 0xffff);

            self.last_mode = mode

        if (abs(steering)>self.STEERING_HIGH and steering<0 and self.last_steering_state != self.STEERING_RIGHT):
            self.setLed(self.LED_INDEX_FRONT_TURN_RIGHT, *self.TURN_LIGHT, 0x3333)
            self.setLed(self.LED_INDEX_REAR_TURN_RIGHT, *self.TURN_LIGHT, 0x3333)
            self.setLed(self.LED_INDEX_FRONT_TURN_LEFT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_REAR_TURN_LEFT, 0, 0, 0, 0xffff)
            self.last_steering_state = self.STEERING_RIGHT
        if (abs(steering)>self.STEERING_HIGH and steering>0 and self.last_steering_state != self.STEERING_LEFT):
            self.setLed(self.LED_INDEX_FRONT_TURN_RIGHT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_REAR_TURN_RIGHT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_FRONT_TURN_LEFT, *self.TURN_LIGHT, 0x3333)
            self.setLed(self.LED_INDEX_REAR_TURN_LEFT, *self.TURN_LIGHT, 0x3333)
            self.last_steering_state = self.STEERING_LEFT
        if (abs(steering)<self.STEERING_LOW and self.last_steering_state != 0):
            self.setLed(self.LED_INDEX_FRONT_TURN_RIGHT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_REAR_TURN_RIGHT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_FRONT_TURN_LEFT, 0, 0, 0, 0xffff)
            self.setLed(self.LED_INDEX_REAR_TURN_LEFT, 0, 0, 0, 0xffff)
            self.last_steering_state = 0
        #self.updateAnim()
        return None
    

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping Robocars Hat Led Controller')
        time.sleep(.5)

#class RobocarsHatInBattery:



