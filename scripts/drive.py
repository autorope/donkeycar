"""
Script to run on the Raspberry PI to start your vehicle's drive loop. The drive loop
will use post requests to the server specified in the remote argument. Use the
serve.py script to start the remote server.

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

    mythrottlecontroller = dk.actuators.PCA9685_Controller(channel=0)
    mysteeringcontroller = dk.actuators.PCA9685_Controller(channel=1)

    #Set up your PWM values for your steering and throttle actuator here. 
    #Default settings are for Exceed Magnet 1/16th scale truck
    mythrottle = dk.actuators.PWMThrottleActuator(controller=mythrottlecontroller, 
                                                  min_pulse=220,
                                                  max_pulse=370,
                                                  zero_pulse=520)

    mysteering = dk.actuators.PWMSteeringActuator(controller=mysteeringcontroller,
                                                  left_pulse=523,
                                                  right_pulse=225)

    mymixer = dk.mixers.FrontSteeringMixer(mysteering, mythrottle)

    #asych img capture from picamera
    mycamera = dk.sensors.PiVideoStream()
    
    #Get all autopilot signals from remote host
    mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id='mycar')

    #Create your car
    car = dk.vehicles.BaseVehicle(drive_loop_delay=.1,
                                  camera=mycamera,
                                  actuator_mixer=mymixer,
                                  pilot=mypilot)
    
    #Start the drive loop
    car.start()
