"""
Script to start controlling your car remotely via on Raspberry Pi that 
constantly requests directions from a remote server. See serve_no_pilot.py
to start a server on your laptop. 

Usage:
    drive.py [--remote=<name>] 


Options:
  --remote=<name>   recording session name
"""

import os
from docopt import docopt

import donkey as dk



# Get args.
args = docopt(__doc__)


if __name__ == '__main__':

    remote_url = args['--remote']

    mythrottlecontroller = PCA9685_Controller(channel=0)
    mysteeringcontroller = PCA9685_Controller(channel=1)

    #Set up your PWM values for your steering and throttle actuator here. 
    mythrottle = dk.actuators.PWMThrottleActuator(controller=mythrottlecontroller, 
                                                  min_pulse=280,
                                                  max_pulse=490,
                                                  zero_pulse=350)

    mysteering = dk.actuators.PWMSteeringActuator(controller=mysteeringcontroller,
                                                  left_pulse=300,
                                                  right_pulse=400)

    mymixer = dk.actuators.FrontSteeringMixer(mysteering, mythrottle)

    #asych img capture from picamera
    mycamera = dk.sensors.PiVideoStream()
    
    #Get all autopilot signals from remote host
    mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id='mycar')

    #Create your car
    car = dk.vehicles.BaseVehicle(camera=mycamera,
                                  actuator_mixer=mymixer,
                                  pilot=mypilot)

    
    #Start the drive loop
    car.start()
