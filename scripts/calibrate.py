"""
calibrate.py

### WARNING: Make sure your car's wheel's are off the groud so it doesn't run away.

Run this script to test what PWM values will work for your car's steering and 
throttle control. You'll be promted to enter the channel to test and then enter 
PWM test values. Start at ~100 and work your way up until you get the desired result.


Usage:
    calibrate.py 

"""
import donkey as dk


if __name__ == '__main__':

	
	channel = int(input('Enter the channel your actuator uses (0-15).'))
	c = dk.parts.PCA9685(channel)
	
	for i in range(10):
		pmw = int(input('Enter a PWM setting to test(0-1500)'))
		c.run(pmw)

