# Simple car movement and ESC calibration using the PCA9685 
# PWM servo/LED controller library.
# Python 3
# Attribution: hacked from sample code from Tony DiCola

import time
# Import the PCA9685 module.
import Adafruit_PCA9685

# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)

# Initialise the PCA9685 using the default address (0x40).
pwm = Adafruit_PCA9685.PCA9685()

# Helper function to make setting a servo pulse width simpler.

def set_servo_pulse(channel, pulse):
    pulse_length = 1000000    # 1,000,000 us per second
    pulse_length //= 60       # 60 Hz
    print('{0}us per period'.format(pulse_length))
    pulse_length //= 4096     # 12 bits of resolution
    print('{0}us per bit'.format(pulse_length))
    pulse *= 1000
    pulse //= pulse_length
    pwm.set_pwm(channel, 0, pulse)

# Calibrate ESC function
def calibrate_esc(channel, high, low, center):
	pwm.set_pwm(channel, 0, int(high))
	time.sleep(2)
	pwm.set_pwm(channel, 0, int(low))
	time.sleep(2)
	pwm.set_pwm(channel, 0, int(center))

# Set frequency to 60hz, good for servos.
pwm.set_pwm_freq(60)

# Set PWM Defaults
MaxPWM = int(480)
MinPWM = int(280)
CenterPWM = int(350)

ServoChannel = int(input("Set servo channel: "))

Option = input("Type 'c' to calibrate or any other character to continue: ")
if Option == 'c':
	calibrate_esc(ServoChannel, MaxPWM, MinPWM, CenterPWM)
else:
	while(True):
		pwm.set_pwm(ServoChannel, 0, int(input('Set PWM Value: ')))




