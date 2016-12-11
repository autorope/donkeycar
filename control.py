# Simple car movement using the PCA9685 PWM servo/LED controller library.
# 
# Attribution: hacked from sample code from Tony DiCola

from __future__ import division
import time

# Import the PCA9685 module.
import Adafruit_PCA9685


# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)

# Initialise the PCA9685 using the default address (0x40).
pwm = Adafruit_PCA9685.PCA9685()

# Configure min and max servo pulse lengths
servo_min = 250  # Min pulse length out of 4096
servo_max = 500  # Max pulse length out of 4096

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

# Set frequency to 60hz, good for servos.
pwm.set_pwm_freq(60)


SteeringChannel = input("set steering channel?  ")
ESCChannel = input("set ESC Channel")

#Calibrate ESC
pwm.set_pwm(ESCChannel, 0, 600)
time.sleep(2)
pwm.set_pwm(ESCChannel, 0, 150)
time.sleep(2)
pwm.set_pwm(ESCChannel, 0, 375)

pwm.set_pwm(SteeringChannel, 0, 400)

print('Moving car on channel, press Ctrl-C to quit...')
while True:
   # Move servo on channel O between extremes.
   # pwm.set_pwm(7, 0, servo_min)
   # time.sleep(1)
    Arrow = input(“1, 2, 3? ")
    if (Arrow==2):
	pwm.set_pwm(ESCChannel, 0, 390)
	time.sleep(1)
	pwm.set_pwm(ESCChannel, 0, 375)
    if (Arrow==3):
	pwm.set_pwm(ESCChannel, 0, 390)
	pwm.set_pwm(SteeringChannel, 0, 250)
	time.sleep(1)
	pwm.set_pwm(ESCChannel, 0, 375)
	pwm.set_pwm(SteeringChannel, 0, 400)
    if (Arrow==1):
	pwm.set_pwm(ESCChannel, 0, 390)
	pwm.set_pwm(SteeringChannel, 0, 500)
	time.sleep(1)
	pwm.set_pwm(ESCChannel, 0, 375)
	pwm.set_pwm(SteeringChannel, 0, 400)

    

