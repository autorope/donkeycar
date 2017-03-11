# Simple car movement using the PCA9685 PWM servo/LED controller library.
# 
# Attribution: hacked from sample code from Tony DiCola

import time
import sys

# Import the PCA9685 module.

# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)


def map_range(x, X_min, X_max, Y_min, Y_max):
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    y = ((x-X_min) / XY_ratio + Y_min) // 1

    return int(y)

class Dummy_Controller:

    def __init__(self, channel, frequency):
        pass
    
class RasPiRobot_Controller:
    def __init__(self, driveLeft, driveRight):
        import rrb3
        rr = RRB3(9, 6)
        leftDir = 0
        rightDir = 0
        if driveLeft < 0:  # change direction if number is negative
            leftDir = 1
        if driveRight < 0:
            rightDir = 1
        rr.set_motors(abs(driveLeft), leftDir, abs(driveRight), rightDir)
        
class PCA9685_Controller:
    # Init with 60hz frequency by default, good for servos.
    def __init__(self, channel, frequency=60):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        self.pwm.set_pwm_freq(frequency)
        self.channel = channel

    def set_pulse(self, pulse):
        self.pwm.set_pwm(self.channel, 0, pulse) 
        
class PWMSteeringActuator:
    #max angle wheels can turn
    LEFT_ANGLE = -1 
    RIGHT_ANGLE = 1

    def __init__(self, controller=None,
                       left_pulse=290,
                       right_pulse=490):

        self.controller = controller
        self.left_pulse = left_pulse
        self.right_pulse = right_pulse

    def update(self, angle):
        #map absolute angle to angle that vehicle can implement.
        pulse = map_range(angle, 
                          self.LEFT_ANGLE, self.RIGHT_ANGLE,
                          self.left_pulse, self.right_pulse)

        self.controller.set_pulse(pulse)


class PWMThrottleActuator:

    MIN_THROTTLE = -1
    MAX_THROTTLE =  1

    def __init__(self, controller=None,
                       max_pulse=300,
                       min_pulse=490,
                       zero_pulse=350):

        #super().__init__(channel, frequency)
        self.controller = controller
        self.max_pulse = max_pulse
        self.min_pulse = min_pulse
        self.zero_pulse = zero_pulse
        self.calibrate()


    def calibrate(self):
        #Calibrate ESC (TODO: THIS DOES NOT WORK YET)
        print('center: %s' % self.zero_pulse)
        self.controller.set_pulse(self.zero_pulse)  #Set Max Throttle
        time.sleep(1)


    def update(self, throttle):
        print('throttle update: %s' %throttle)
        if throttle > 0:
            pulse = map_range(throttle,
                              0, self.MAX_THROTTLE, 
                              self.zero_pulse, self.max_pulse)
        else:
            pulse = map_range(throttle,
                              self.MIN_THROTTLE, 0, 
                              self.min_pulse, self.zero_pulse)

        print('pulse: %s' % pulse)
        sys.stdout.flush()
        self.controller.set_pulse(pulse)
        return '123'


class Adafruit_Motor_Hat_Controller:
    def __init__(self, motor_num):
        from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor
        import atexit
        
        self.FORWARD = Adafruit_MotorHAT.FORWARD
        self.BACKWARD = Adafruit_MotorHAT.BACKWARD
        self.mh = Adafruit_MotorHAT(addr=0x60) 
        
        self.motor = self.mh.getMotor(motor_num)
        self.motor_num = motor_num
        
        atexit.register(self.turn_off_motors)
        self.speed = 0
        self.throttle = 0
    
    def turn_off_motors(self):
        self.mh.getMotor(self.motor_num).run(Adafruit_MotorHAT.RELEASE)

        
    def turn(self, speed):
        if speed > 1 or speed < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")
        
        self.speed = speed
        self.throttle = int(map_range(abs(speed), -1, 1, -255, 255))
        
        if speed > 0:            
            self.motor.run(self.FORWARD)
        else:
            self.motor.run(self.BACKWARD)
            
        self.motor.setSpeed(self.throttle)
        
    def test(self, seconds=.5):
        speeds = [-.5, -1, -.5, 0, .5, 1, 0]
        for s in speeds:
            self.turn(s)
            time.sleep(seconds)
            print('speed: %s   throttle: %s' % (self.speed, self.throttle))
        print('motor #%s test complete'% self.motor_num)
        

