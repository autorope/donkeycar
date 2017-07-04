"""
calibrate.py

Script to run on the Raspberry PI to start your vehicle's drive loop. The drive loop
will use post requests to the server specified in the remote argument. Run the 
serve.py script on a different computer to start the remote server.

Usage:
    calibrate.py 

"""
import donkey as dk


if __name__ == '__main__':

	
	channel = int(input('Enter the channel your actuator uses (0-15).'))
	c = dk.actuators.PCA9685(channel)
	
	for i in range(10):
		pmw = int(input('Enter a PWM setting to test(0-1500)'))
		c.run(pmw)

