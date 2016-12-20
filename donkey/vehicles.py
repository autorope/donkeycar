# Simple car movement using the PCA9685 PWM servo/LED controller library.
# 
# Attribution: hacked from sample code from Tony DiCola

from __future__ import division
import time

# Import the PCA9685 module.



# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)


class BaseVehicle():
    ''' Placeholder until real logic is implemented '''

    #max angle wheels can turn
    LEFT_ANGLE = -45 
    RIGHT_ANGLE = 45

    def update_angle(self, angle):
        #map absolute angle to angle that vehicle can implement.
        pulse = self.map_range(angle, self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                     300, 400)

    def update_throttle(self, speed):
        pulse = self.map_range(speed, self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                     300, 400)

    def update(self, angle, speed):
        self.update_throttle(speed)
        self.update_angle(angle)
        #return actual angle and speed
        return 0, 0

    def hard_stop(self):
        '''stop vehicle quickly'''
        self.update(0,0)


    def map_range(self, x, X_min, X_max, Y_min, Y_max):
        X_range = X_max - X_min
        Y_range = Y_max - Y_min
        XY_ratio = X_range/Y_range
        
        y = (x / XY_ratio + Y_min + .5 * Y_range) // 1

        return int(y)

    def test_steering(self):
        self.update_angle(0)
        time.sleep(1)
        self.update_angle(self.LEFT_ANGLE)
        time.sleep(1)
        self.update_angle(0)
        time.sleep(1)
        self.update_angle(self.RIGHT_ANGLE)
        time.sleep(1)
        self.update_angle(0)

    def test_throttle(self):
        self.update_speed(0)
        time.sleep(1)
        self.update_speed(-50)
        time.sleep(1)
        self.update_speed(-100)
        time.sleep(1)
        self.update_speed(0)
        time.sleep(1)
        self.update_speed(50)
        time.sleep(1)
        self.update(100)
        time.sleep(1)
        self.update_speed(0)



class Adafruit_PCA9685(BaseVehicle):
    STEERING_CHANNEL = 1
    THROTTLE_CHANNEL = 0

    def __init__(self):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        # Set frequency to 60hz, good for servos.
        self.pwm.set_pwm_freq(60)

    def update_angle(self, angle):
        print('updating throttle: %s' %angle)
        pulse = self.map_range(angle, 
                            self.LEFT_ANGLE, self.RIGHT_ANGLE, 
                            self.LEFT_PULSE, self.RIGHT_PULSE)

        self.pwm.set_pwm(self.STEERING_CHANNEL, 0, pulse)


    def update_throttle(self, throttle):
        print('updating throttle: %s' %throttle)
        pulse = self.map_range(throttle,
                             -100, 100, 
                             self.MIN_THROTLE_PULSE, self.MAX_THROTLE_PULSE)

        self.pwm.set_pwm(self.THROTTLE_CHANNEL, 0, pulse)



class HelionConquest(Adafruit_PCA9685):
    ''' Will's Vehicle'''

    #max angle wheels can turn
    LEFT_ANGLE = -45 
    RIGHT_ANGLE = 45

    #pwm pulse length to turn wheels to max angles
    LEFT_PULSE = 325
    RIGHT_PULSE = 475

    #pwm pulse length to move wheelse 
    MIN_THROTLE_PULSE = 280 #max reverse
    MAX_THROTLE_PULSE = 320 #max forward







class Adam(Adafruit_PCA9685):


    #max angle wheels can turn
    LEFT_ANGLE = -45 
    RIGHT_ANGLE = 45

    #pwm pulse length to turn wheels to max angles
    LEFT_PULSE = 325
    RIGHT_PULSE = 475

    #pwm pulse length to move wheelse 
    MIN_THROTLE_PULSE = 375 #max reverse
    MAX_THROTLE_PULSE = 390 #max forward


if __name__ == '__main__':
    car = HelionConquest()
    car.test_steering()
    time.sleep(2)
    car.test_throttle()
