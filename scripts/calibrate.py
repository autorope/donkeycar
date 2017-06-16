"""
calibrate.py

### WARNING: Make sure your car's wheel's are off the groud so it doesn't run away.

Run this script to test what PWM values will work for your car's steering and 
throttle control. You'll be promted to enter the channel to test and then enter 
PWM test values. Start at ~100 and work your way up until you get the desired result.


Usage:
    calibrate.py 

"""
from time import sleep

import donkey as dk


if __name__ == '__main__':

	
	channel = int(input('What actuator channel'))
	c = dk.actuators.PCA9685_Controller(channel)
	
	for i in range(10):
		pmw = int(input('What PMW setting? '))
		c.set_pulse(pmw)

