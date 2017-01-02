# Simple car movement using the PCA9685 PWM servo/LED controller library.
# 
# Attribution: hacked from sample code from Tony DiCola

import time

# Import the PCA9685 module.



# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)


def map_range(x, X_min, X_max, Y_min, Y_max):
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range
    
    y = (x / XY_ratio + Y_min + .5 * Y_range) // 1

    return int(y)


class BaseSteeringActuator():
    ''' Placeholder until real logic is implemented '''

    def update(self, angle):
        print('BaseSteeringActuator.update: angle=%s' %angle)

class BaseThrottleActuator():
    ''' Placeholder until real logic is implemented '''

    def update(self, throttle):
        print('BaseThrottleActuator.update: angle=%s' %angle)


class Adafruit_PCA9685_Actuator():

    def __init__(self, channel, frequency=60):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        # Set frequency to 60hz, good for servos.
        self.pwm.set_pwm_freq(frequency)
        self.channel = channel


class PWMSteeringActuator(Adafruit_PCA9685_Actuator):

    #max angle wheels can turn
    LEFT_ANGLE = -45 
    RIGHT_ANGLE = 45

    #PWM pulse values for turns
    LEFT_PULSE = 300
    RIGHT_PULSE = 400

    def update(self, angle):
        #map absolute angle to angle that vehicle can implement.
        pulse = map_range(angle, 
                          self.LEFT_ANGLE, self.RIGHT_ANGLE,
                          self.LEFT_PULSE, self.RIGHT_PULSE)

        self.pwm.set_pwm(self.channel, 0, pulse)



class PWMThrottleActuator(Adafruit_PCA9685_Actuator):

    MIN_THROTTLE = -100
    MAX_THROTTLE =  100

    MIN_THROTTLE_PULSE = 300
    MAX_THROTTLE_PULSE = 400
    CENTER_THROTTLE_PULSE = 325

    def __init__(self, channel, frequency=60):
        super().__init__(channel, frequency)
        self.calibrate()

    def calibrate(self):
        #Calibrate ESC
        print('center: %s' % self.CENTER_THROTTLE_PULSE)
        self.pwm.set_pwm(self.channel, 0, self.CENTER_THROTTLE_PULSE)  #Set Max Throttle
        time.sleep(1)

    def update(self, throttle):
        print('throttle update: %s' %throttle)
        if throttle > 0:
            pulse = map_range(throttle,
                              0, self.MAX_THROTTLE, 
                              self.CENTER_THROTTLE_PULSE, self.MAX_THROTTLE_PULSE)
        else:
            pulse = map_range(throttle,
                              self.MIN_THROTTLE, 0, 
                              self.MIN_THROTTLE_PULSE, self.CENTER_THROTTLE_PULSE)

        print('pulse: %s' % pulse)
        self.pwm.set_pwm(self.channel, 0, pulse)














