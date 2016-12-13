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


    def update_angle(self, angle):
        #map absolute angle to angle that vehicle can implement.
        pass

    def update_speed(self, speed):
        pass

    def update(self, angle, speed):
        self.update_speed(speed)
        self.update_angle(angle)
        #return actual angle and speed
        return 0, 0

    def hard_stop(self):
        '''stop vehicle quickly'''
        self.update(0,0)






class Adam():
    def __init__(self):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        # Configure min and max servo pulse lengths
        self.servo_min = 250  # Min pulse length out of 4096
        self.servo_max = 500  # Max pulse length out of 4096

        # Set frequency to 60hz, good for servos.
        self.pwm.set_pwm_freq(60)

    # Helper function to make setting a servo pulse width simpler.
    def set_servo_pulse(self, channel, pulse):
        pulse_length = 1000000    # 1,000,000 us per second
        pulse_length //= 60       # 60 Hz
        print('{0}us per period'.format(pulse_length))
        pulse_length //= 4096     # 12 bits of resolution
        print('{0}us per bit'.format(pulse_length))
        pulse *= 1000
        pulse //= pulse_length
        self.pwm.set_pwm(channel, 0, pulse)


    def calibrate_ESC_channel(self, channel):

        #Calibrate ESC
        self.pwm.set_pwm(ESCChannel, 0, 600)
        time.sleep(2)
        self.pwm.set_pwm(ESCChannel, 0, 150)
        time.sleep(2)
        self.pwm.set_pwm(ESCChannel, 0, 375)


    def calibrate_steering_channel(channel):
        self.pwm.set_pwm(SteeringChannel, 0, 400)




    def move_forward(seconds):
        self.pwm.set_pwm(ESCChannel, 0, 390)
        time.sleep(seconds)
        self.pwm.set_pwm(ESCChannel, 0, 375)


    def move_forward_right(seconds):
        self.pwm.set_pwm(ESCChannel, 0, 390)
        self.pwm.set_pwm(SteeringChannel, 0, 500)
        time.sleep(seconds)
        self.set_pwm(ESCChannel, 0, 375)
        self.set_pwm(SteeringChannel, 0, 400)




    

if __name__ == '__main__':
    SteeringChannel = input("set steering channel?  ")
    ESCChannel = input("set ESC Channel")

    vehicle = Adam()
    vehicle.calibrate_steering_channel(SteeringChannel)
    vehicle.calibrate_ESC_channel(ESCChannel)

    time.sleep(1)

    vehicle.move_forward(1)
    time.sleep(1)
    vehicle.move_forward_right(2)