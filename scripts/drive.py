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

    cfg = dk.config_parser.get_config('~/mydonkey/vehicle.ini')

    remote_url = args['--remote']

    mythrottlecontroller = dk.actuators.PCA9685_Controller(cfg['throttle_actuator_channel'])
    mysteeringcontroller = dk.actuators.PCA9685_Controller(cfg['steering_actuator_channel'])

    #Set up your PWM values for your steering and throttle actuator here. 
    #Default settings are for Exceed Magnet 1/16th scale truck
    mythrottle = dk.actuators.PWMThrottleActuator(controller=mythrottlecontroller, 
                                                  min_pulse=cfg['throttle_actuator_min_pulse'],
                                                  max_pulse=cfg['throttle_actuator_max_pulse'],
                                                  zero_pulse=cfg['throttle_actuator_zero_pulse'])

    mysteering = dk.actuators.PWMSteeringActuator(controller=mysteeringcontroller,
                                                  left_pulse=cfg['steering_actuator_min_pulse'],
                                                  right_pulse=cfg['steering_actuator_max_pulse'])

    mymixer = dk.mixers.FrontSteeringMixer(mysteering, mythrottle)

    #asych img capture from picamera
    mycamera = dk.sensors.PiVideoStream()
    
    #Get all autopilot signals from remote host
    mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id=cfg['vehicle_id'])

    #Create your car
    car = dk.vehicles.BaseVehicle(drive_loop_delay=cfg['vehicle_loop_delay'],
                                  camera=mycamera,
                                  actuator_mixer=mymixer,
                                  pilot=mypilot)
    
    #Start the drive loop
    car.start()
