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
from transitions.extensions import HierarchicalMachine
from collections import deque

mylogger = init_special_logger ("Rx")
mylogger.setLevel(logging.INFO)

def dualMap (input, input_min, input_idle, input_max, output_min, output_idle, output_max, enforce_input_in_range=False) :
    if (input < input_idle) :
        output = dk.utils.map_range_float (input, input_min, input_idle, output_min, output_idle, enforce_input_in_range)
    elif (input>input_idle) :
        output = dk.utils.map_range_float (input, input_idle, input_max, output_idle, output_max, enforce_input_in_range)
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

class RobocarsHatInCtrl(metaclass=Singleton):
    AUX_FEATURE_NONE=0
    AUX_FEATURE_RECORDandPILOT=1
    AUX_FEATURE_RECORD=2
    AUX_FEATURE_PILOT=3
    AUX_FEATURE_THROTTLEEXP=4
    AUX_FEATURE_STEERINGEXP=5
    AUX_FEATURE_OUTPUT_STEERING_TRIM=6
    AUX_FEATURE_OUTPUT_STEERING_EXP=7
    AUX_FEATURE_THROTTLE_SCALAR_EXP=8
    AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP = 9

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
        elif feature == 'throttle_scalar_exp':
            return self.AUX_FEATURE_THROTTLE_SCALAR_EXP
        elif feature == 'adaptative_steering_scalar_exp':
            return self.AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP
        elif feature != 'none':
            mylogger.info(f"CtrlIn : Unkown requested feature : {feature}")

    def __init__(self, cfg):

        self.cfg = cfg
        self.inSteering = 0.0
        self.inThrottle = 0.0
        self.fixThrottle = 0.0
        self.throttleTriggered = False
        self.fixSteering = 0.0
        self.fixOutputSteeringTrim = None
        self.fixOutputSteering = None
        self.fixThrottleExtraScalar = 0.0
        self.adaptativeSteeringExtraScalar = 0.0
        self.inAux1 = 0.0
        self.inAux2 = 0.0
        self.lastAux1 = -1.0
        self.lastAux2 = -1.0
        self.lastMode = 'user'
        self.applyBrake = 0

        if (self.cfg.ROBOCARSHAT_USE_AUTOCALIBRATION==True) :
            self.inThrottleIdle = -1
            self.inSteeringIdle = -1
        else:
            self.inThrottleIdle = 1500
            self.inSteeringIdle = 1500

        #Aux feature
        self.aux1Feature = self.AUX_FEATURE_NONE
        self.aux2Feature = self.AUX_FEATURE_NONE

        self.aux1Feature = self._map_aux_feature (self.cfg.ROBOCARSHAT_CH3_FEATURE)
        self.aux2Feature = self._map_aux_feature (self.cfg.ROBOCARSHAT_CH4_FEATURE)

        if (self.aux1Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM) or (self.aux2Feature == self.AUX_FEATURE_OUTPUT_STEERING_TRIM):
            self.fixOutputSteeringTrim = 1500
        if (self.aux1Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP) or (self.aux2Feature == self.AUX_FEATURE_OUTPUT_STEERING_EXP):
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
                        self.inThrottle = dk.utils.map_range_float(int(params[1]),
                                self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MIN, self.cfg.ROBOCARSHAT_PWM_IN_THROTTLE_MAX,
                            -1, 1, enforce_input_in_range=True)

                if params[2].isnumeric() and self.inSteeringIdle != -1:
                    if (self.cfg.ROBOCARSHAT_USE_AUTOCALIBRATION==True) :
                        self.inSteering = dualMap(int(params[2]),
                                self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MIN, self.inSteeringIdle, self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MAX,
                            -1, 0, 1)
                    else:
                        self.inSteering = dk.utils.map_range_float(int(params[2]),
                            self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MIN, self.cfg.ROBOCARSHAT_PWM_IN_STEERING_MAX,
                            -1, 1, enforce_input_in_range=True)

                if params[3].isnumeric():
                    self.inAux1 = dk.utils.map_range_float(int(params[3]),
                        self.cfg.ROBOCARSHAT_PWM_IN_AUX_MIN, self.cfg.ROBOCARSHAT_PWM_IN_AUX_MAX,
                        -1, 1)
                if params[4].isnumeric():
                    self.inAux2 = dk.utils.map_range_float(int(params[4]),
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

    def getFixThrottleExtraScalar(self):
        return self.fixThrottleExtraScalar

    def getAdaptativeSteeringExtraScalar(self):
        return self.adaptativeSteeringExtraScalar

    def getCommand(self):
        self.processRxCh()
        self.processCalibration()

    def isFeatActive(self, feature):
        # return actual value read from channel, and indication on whether value has changed or not since last check.
        # has_changed information is for switch like feature
        if (self.aux1Feature == feature or self.aux2Feature == feature):
            return True
        return False

    def getAuxValuePerFeat(self, feature):
        # return actual value read from channel, and indication on whether value has changed or not since last check.
        # has_changed information is for switch like feature
        if self.aux1Feature == feature:
            return self.inAux1, abs(self.lastAux1 - self.inAux1)>0.1
        elif self.aux2Feature == feature:
            return self.inAux2, abs(self.lastAux2 - self.inAux2)>0.1
        else:
            return None,None

    def processAltModes(self):
        mode='user'
        recording=False
        user_throttle = self.inThrottle
        user_steering = self.inSteering

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_RECORDandPILOT)
        if command != None :
            if (command<-0.5):
                recording=True
                mode='user'
            elif (command>0.5):
                mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                user_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE
            else:
                mode='user'

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_RECORD)
        if command != None :
            if command > 0.5:
                recording=True

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_PILOT)
        if command != None :
            if command > 0.5:
                mode=self.cfg.ROBOCARSHAT_PILOT_MODE
                user_throttle = self.cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_THROTTLEEXP)
        if command != None :
            if has_changed :
                if command > 0.5:
                    self.fixThrottle = min(self.fixThrottle+self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
                if command < -0.5:
                    self.fixThrottle = max(self.fixThrottle-self.cfg.ROBOCARSHAT_THROTTLE_EXP_INC,0.0)
                    mylogger.info("CtrlIn Fixed throttle set to {}".format(self.fixThrottle))
            user_throttle = self.fixThrottle

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_STEERINGEXP)
        if command != None :
            if has_changed :
                if command > 0.5:
                    self.fixSteering = min(self.fixSteering+self.cfg.ROBOCARSHAT_STEERING_EXP_INC,1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
                if command < -0.5:
                    self.fixSteering = max(self.fixSteering-self.cfg.ROBOCARSHAT_STEERING_EXP_INC,-1.0)
                    mylogger.info("CtrlIn Fixed steering set to {}".format(self.fixSteering))
            user_steering = self.fixSteering            

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_OUTPUT_STEERING_TRIM)
        if command != None :
            if has_changed :
                if command > 0.5:
                    self.fixOutputSteeringTrim = min(self.fixOutputSteeringTrim+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                if command < -0.5:
                    self.fixOutputSteeringTrim = max(self.fixOutputSteeringTrim-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteeringTrim))
                self.hatActuator.setSteeringTrim (self.fixOutputSteeringTrim)            

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_OUTPUT_STEERING_EXP)
        if command != None :
            if has_changed :
                if command > 0.5:
                    self.fixOutputSteering = min(self.fixOutputSteering+self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,2000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                if command < -0.5:
                    self.fixOutputSteering = max(self.fixOutputSteering-self.cfg.ROBOCARSHAT_OUTPUT_STEERING_TRIM_INC,1000)
                    mylogger.info("CtrlIn Fixed output steering set to {}".format(self.fixOutputSteering))
                self.hatActuator.setFixSteering (self.fixOutputSteering)            

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_THROTTLE_SCALAR_EXP)
        if command != None :
            newScalar =  dk.utils.map_range_float(command,
                        -1.0, 1.0,
                        0.0, self.cfg.AUX_FEATURE_THROTTLE_SCALAR_EXP_MAX_VALUE, enforce_input_in_range=True)
            if (abs(newScalar - self.fixThrottleExtraScalar)>0.01) :
                 mylogger.info("CtrlIn fix throttle scalar set to {}".format(newScalar))
            self.fixThrottleExtraScalar = newScalar

        command, has_changed = self.getAuxValuePerFeat(self.AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP)
        if command != None :
            newScalar =  dk.utils.map_range_float(command,
                        -1.0, 1.0,
                        0.0, self.cfg.AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP_MAX_VALUE, enforce_input_in_range=True)
            if (abs(newScalar - self.adaptativeSteeringExtraScalar)>0.01) :
                 mylogger.info("CtrlIn adaptative steering scalar set to {}".format(newScalar))
            self.adaptativeSteeringExtraScalar = newScalar

        # Process other features 
        if self.cfg.ROBOCARSHAT_STEERING_FIX != None:
             user_steering = self.cfg.ROBOCARSHAT_STEERING_FIX

        if self.cfg.ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL and mode != 'user':

            # if throttle trigger is pushed forward or backward, incremet/decrement fixThrottleExtraScalar
            if (abs(self.inThrottle) > 0.3) and (self.throttleTriggered == False):
                self.throttleTriggered = True
                if self.inThrottle > 0.3:
                    self.fixThrottleExtraScalar = self.fixThrottleExtraScalar + self.cfg.ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL_INC
                elif self.inThrottle < -0.3:
                    self.fixThrottleExtraScalar = self.fixThrottleExtraScalar - self.cfg.ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL_INC
                self.fixThrottleExtraScalar = min(self.cfg.AUX_FEATURE_THROTTLE_SCALAR_EXP_MAX_VALUE,max(0.0, self.fixThrottleExtraScalar))
                mylogger.info("CtrlIn fixed throttle scalar set to {:.2f}".format(self.fixThrottleExtraScalar))
            # Wait for trigger to be released, 
            if (abs(self.inThrottle) < 0.1) and (self.throttleTriggered == True):
                self.throttleTriggered = False
            
            # Full Reverse trigger will stop the car as long as maintained 
            if self.inThrottle < -0.9:
                mode = 'user'
                user_throttle = 0

        # Discret throttle mode
        if mode=='user':
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

        #if switching back to user, then apply brake
        if mode=='user' and self.lastMode != 'user' and self.cfg.ROBOCARSHAT_BRAKE_ON_IDLE_THROTTLE != None:
            self.applyBrake=10 #brake duration

        self.lastMode = mode
        self.lastAux1 = self.inAux1
        self.lastAux2 = self.inAux2
        
        if self.applyBrake>0:
            user_throttle = self.cfg.ROBOCARSHAT_BRAKE_ON_IDLE_THROTTLE
            self.applyBrake-=1

        return user_throttle, user_steering, mode, recording

    def update(self):

        while self.on:
            start = datetime.now()
            self.getCommand()
            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        user_throttle, user_steering, user_mode, recording = self.processAltModes ()
        return user_steering, user_throttle, user_mode, recording

    def run (self):
        self.getCommand()
        user_throttle, user_steering, user_mode, recording = self.processAltModes ()
        return user_steering, user_throttle, user_mode, recording
    

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
                    self.inSpeed = dk.utils.map_range_float(min(abs(int(params[2])),self.cfg.ROBOCARSHAT_ODOM_IN_MAX),
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
        print('stopping Robocars Hat Odom Controller')
        time.sleep(.5)

class RobocarsHatInBattery:

    def __init__(self, cfg):

        self.cfg = cfg
        self.inBattery = 0
        self.hatInMsg = RobocarsHatIn(self.cfg)
        self.on = True

    def processBattery(self):
        battery_msg = self.hatInMsg.getBattery()
        if battery_msg:
            params = battery_msg.split(',')
            if len(params) == 5 and int(params[0])==0 :
                 mylogger.debug("CtrlIn SBattery {} mv".format(int(params[1])))
                 if params[1].isnumeric():
                     self.inBattery = int(params[1])

    def getCommand(self):
        self.processBattery()

    def update(self):

        while self.on:
            start = datetime.now()
            self.getCommand()
            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        return self.inBattery

    def run (self):
        self.getCommand()
        return self.inBattery
    

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping Robocars Hat Battery Controller')
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
        self.reconnect=True
        self.reconnectDelay=500
        if self.cfg.ROBOCARSHAT_CONTROL_LED_DEDICATED_TTY :
            self.connectPort()
        else:
            self.cmdinterface = RobocarsHat(self.cfg)

        if cfg.ROBOCARSHAT_LED_MODEL == 'Alpine':
            self.LED_INDEX_FRONT_TURN_RIGHT = 3
            self.LED_INDEX_FRONT_TURN_LEFT = 4
            self.LED_INDEX_REAR_TURN_RIGHT = 1
            self.LED_INDEX_REAR_TURN_LEFT = 0
            self.LED_INDEX_FRONT_LIGHT_RIGHT = 2
            self.LED_INDEX_FRONT_LIGHT_LEFT = 5

        else: #default
            self.LED_INDEX_FRONT_TURN_RIGHT = 0
            self.LED_INDEX_FRONT_TURN_LEFT = 1
            self.LED_INDEX_REAR_TURN_RIGHT = 2
            self.LED_INDEX_REAR_TURN_LEFT = 3
            self.LED_INDEX_FRONT_LIGHT_RIGHT = 4
            self.LED_INDEX_FRONT_LIGHT_LEFT = 5


        self.idx = 0
        self.last_mode = None
        self.last_steering_state = 0
        self.last_refresh = 0

    def connectPort(self):
        import serial
        self.reconnectDelay=100
        try:
            self.cmdinterface = serial.Serial(self.cfg.ROBOCARSHAT_CONTROL_LED_DEDICATED_TTY, 250000, timeout = 0.01)
            self.reconnect = False
        except Exception as e:
            mylogger.info(f"LED : Failed to connect to port {self.cfg.ROBOCARSHAT_CONTROL_LED_DEDICATED_TTY}")
        
    def setLed(self, i, r, v, b, timing):
        from serial import SerialException
        cmd=("2,%01d,%03d,%03d,%03d,%05d\n" % (int(i), int(r), int(v), int(b), int(timing))).encode('ascii')
        if self.cfg.ROBOCARSHAT_CONTROL_LED_DEDICATED_TTY:
            if not self.reconnect:
                try:
                    self.cmdinterface.write(cmd)
                except SerialException:
                    mylogger.info("LED : Serial port issue")
                    if self.cmdinterface:
                        self.cmdinterface.close()
                    self.reconnect=True
                    self.reconnectDelay=500

        else:
            self.cmdinterface.sendCmd(cmd)

    def setAnim(self, n):
        cmd=("3,%01d\n" % (int(n))).encode('ascii')
        if self.cfg.ROBOCARSHAT_CONTROL_LED_DEDICATED_TTY :
            self.cmdinterface.write(cmd)
        else:
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

        if (self.reconnect):
            if self.reconnectDelay==0:
                self.connectPort()
            else:
                self.reconnectDelay-=1
        refresh = (time.perf_counter()-self.last_refresh) >= 2.0
        if refresh:
            self.last_refresh = time.perf_counter()
        if self.last_mode == None:
            self.setLed(self.LED_INDEX_FRONT_TURN_RIGHT, 0, 0, 0, 0x0);
            self.setLed(self.LED_INDEX_FRONT_TURN_LEFT, 0, 0, 0, 0x0);
            self.setLed(self.LED_INDEX_REAR_TURN_RIGHT, 0, 0, 0, 0x0);
            self.setLed(self.LED_INDEX_REAR_TURN_LEFT, 0, 0, 0, 0x0);
            self.setLed(self.LED_INDEX_FRONT_LIGHT_RIGHT, 0, 0, 0, 0x0);
            self.setLed(self.LED_INDEX_FRONT_LIGHT_LEFT, 0, 0, 0, 0x0);

        if mode != self.last_mode or refresh:
            if mode=='user' :
                self.setLed(self.LED_INDEX_FRONT_LIGHT_RIGHT, *self.USER_FRONT_LIGH, 0xffff);
                self.setLed(self.LED_INDEX_FRONT_LIGHT_LEFT, *self.USER_FRONT_LIGH, 0xffff);
            else:
                if self.cfg.ROBOCARSHAT_CONTROL_LED_PILOT_ANIM:
                    self.setAnim(self.cfg.ROBOCARSHAT_CONTROL_LED_PILOT_ANIM)
                else:
                    self.setLed(self.LED_INDEX_FRONT_LIGHT_RIGHT, *self.AUTO_FRONT_LIGH, 0xffff);
                    self.setLed(self.LED_INDEX_FRONT_LIGHT_LEFT, *self.AUTO_FRONT_LIGH, 0xffff);

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

drivetrainlogger = init_special_logger ("DrivetrainCtrl")
drivetrainlogger.setLevel(logging.INFO)
logging.getLogger('transitions').setLevel(logging.INFO)

class RobocarsHatDriveCtrl(metaclass=Singleton):

    ACC_DEFAULT = 0
    ACC_STRAIGHT_LINE = 1

    ACC_LABEL=["regular","straight line"]

    states = [
            {'name':'stopped'}, 
            {'name':'driving','initial':'regularspeed', 'children':['regularspeed', 'fullspeed','braking']}
            ]

    def set_brakespeed(self):
        if self.cfg.ROBOCARS_THROTTLE_SCALER_ON_SL>0.0:
            self.throttle_out  = self.cfg.ROBOCARS_THROTTLE_ON_ACC_BRAKE_SPEED
            self.brake_cycle = self.cfg.ROBOCARS_THROTTLE_ON_ACC_BRAKE_DURATION
        else:
            # no active brake
            self.brake_cycle = 0


    #transitions = [
    #    {'trigger':'drive', 'source':'stopped', 'dest':'driving','before':set_regularspeed},
    #    {'trigger':'stop', 'source':'driving', 'dest':'stopped'},
    #    {'trigger':'accelerate', 'source':['driving','driving_regularspeed'], 'dest':'driving_fullspeed', 'before':set_fullspeed},
    #    {'trigger':'brake', 'source':['driving', 'driving_fullspeed'], 'dest':'driving_braking', 'before':set_brakespeed},
    #    {'trigger':'drive', 'source':['driving', 'driving_braking'], 'dest':'driving_regularspeed', 'before':set_regularspeed},
    #    ]

    def __init__(self, cfg):
        self.cfg = cfg

        self.hatInCtrl = None
        if (self.cfg.USE_ROBOCARSHAT_AS_CONTROLLER):
            self.hatInCtrl = RobocarsHatInCtrl(self.cfg)
        self.fix_throttle = 0
        self.brake_cycle = 0
        self.last_sl=deque(maxlen=self.cfg.ROBOCARS_THROTTLE_SCALER_ON_SL_FILTER_SIZE)
        self.lane = 0
        self.on = True

        self.machine = HierarchicalMachine(self, states=self.states, initial='stopped', ignore_invalid_triggers=True)
        self.machine.add_transition (trigger='drive', source='stopped', dest='driving')
        self.machine.add_transition (trigger='stop', source='driving', dest='stopped')
        self.machine.add_transition (trigger='accelerate', source='driving_regularspeed', dest='driving_fullspeed')
        self.machine.add_transition (trigger='brake', source='driving_fullspeed', dest='driving_braking', before='set_brakespeed')
        self.machine.add_transition (trigger='drive', source='driving_braking', dest='driving_regularspeed')

        drivetrainlogger.info('starting RobocarsHatLaneCtrl Hat Controller')

    def update_sl_filter (self,sl):
        if (sl != None) :
            self.last_sl.append(sl)

    def is_sl_confition(self):
        sl_arr = list(self.last_sl)
        sl_count = sum(sl_arr)
        if sl_count >= self.cfg.ROBOCARS_SL_FILTER_TRESH_HIGH:
            return True
        if sl_count <= self.cfg.ROBOCARS_SL_FILTER_TRESH_LOW:
            return False
        return None

    def processState(self, throttle, angle, mode, sl):
            
        self.throttle_from_pilot = throttle
        self.angle_from_pilot = angle

        # default output value from pilot 
        self.throttle_out = self.throttle_from_pilot
        self.angle_out = self.angle_from_pilot

        # apply static scalar on throttle :
        self.throttle_out = self.throttle_from_pilot * (1.0 + self.cfg.ROBOCARS_THROTTLE_SCALER)
        if self.hatInCtrl.isFeatActive(self.hatInCtrl.AUX_FEATURE_THROTTLE_SCALAR_EXP) or self.cfg.ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL :
            # if feature to explore throttle scalar is enabled, override scalar with current value beeing tested
            self.throttle_out = self.throttle_from_pilot * (1.0 + self.cfg.ROBOCARS_THROTTLE_SCALER + self.hatInCtrl.getFixThrottleExtraScalar())

        # apply steering compensation based on targeted throttle
        # compute the scalar to apply, proportionnaly to the targeted throttle comparted to throttle from model or from local_angle mode
        # dyn_steering_factor = dk.utils.map_range_float(self.throttle_out, self.throttle_from_pilot, 1.0, 0.0, self.cfg.ROBOCARS_CTRL_ADAPTATIVE_STEERING_SCALER)
        dyn_steering_factor = self.cfg.ROBOCARS_CTRL_ADAPTATIVE_STEERING_SCALER
        if self.hatInCtrl.isFeatActive(self.hatInCtrl.AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP):
            # if feature to explore adaptative steering scalar is enabled, override scalar with current value beeing tested
            dyn_steering_factor = self.hatInCtrl.getAdaptativeSteeringExtraScalar()

        # then, if straight line detected, apply specific scalar
        if self.is_stopped(allow_substates=True):
            if (mode != 'user') :
                self.drive() #engage autonomous mode

        if self.is_driving(allow_substates=True):
            self.update_sl_filter (sl)
            if (mode == 'user') :
                self.stop() #disengage autonomous mode

        if self.is_driving_regularspeed(allow_substates=True):
            if not self.cfg.ROBOCARS_CTRL_ADAPTATIVE_STEERING_IN_TURN_ONLY:
                # apply steering scaler even at low speed (turn)
                self.angle_out = max(min(self.angle_from_pilot * (1.0+dyn_steering_factor),1.0),-1.0)
            if (self.is_sl_confition()==True) :
                self.accelerate() #sl detected and confirmed 
                

        if self.is_driving_fullspeed(allow_substates=True):
            # apply extra scalar factor on throttle when in straight line
            self.throttle_out = self.throttle_out * self.cfg.ROBOCARS_THROTTLE_SCALER_ON_SL
            # apply steering scaler
            self.angle_out = max(min(self.angle_from_pilot * (1.0+dyn_steering_factor),1.0),-1.0)
            if (self.is_sl_confition()==False):
                self.brake() # end of sl

        if self.is_driving_braking(allow_substates=True):
            if self.brake_cycle == 0:
                self.drive() # end of braking cycle
            else:
                self.brake_cycle -=1

        return self.throttle_out, self.angle_out
 
    def update(self):
        # not implemented
        pass

    def run_threaded(self, throttle, angle, mode, sl):
        # not implemented
        pass

    def run (self,throttle, angle, mode, sl,):
        throttle, angle = self.processState (throttle, angle, mode, sl)
        return throttle, angle
    

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        drivetrainlogger.info('stopping RobocarsHatLaneCtrl Hat Controller')
        time.sleep(.5)


