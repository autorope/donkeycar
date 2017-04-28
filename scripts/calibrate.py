"""
calibrate.py

Script to run on the Raspberry PI to start your vehicle's drive loop. The drive loop
will use post requests to the server specified in the remote argument. Run the 
serve.py script on a different computer to start the remote server.

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

