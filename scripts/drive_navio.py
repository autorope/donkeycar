"""
drive_navio.py

Script to run on the Raspberry PI to start your vehicle's drive loop. The drive loop
will use post requests to the server specified in the remote argument. Run the 
serve.py script on a different computer to start the remote server. This module is 
compatible with the NAVIO2 HAT.

Usage:
    drive.py [--remote=<name>] [--config=<name>]

Options:
  --remote=<name>   recording session name
  --config=<name>   vehicle configuration file name (without extension)  [default: minitrooper_navio]
"""

import os
from docopt import docopt

import donkey as dk



# Get args.
args = docopt(__doc__)


if __name__ == '__main__':

    cfg = dk.config.parse_config('~/mydonkey/' + args['--config'] + '.ini')

    #get the url for the remote host (for user control)
    remote_url = args['--remote']

    #set the PWM ranges
    mythrottle = dk.actuators.PWMThrottleActuator(controller=mythrottlecontroller, 
                                                  min_pulse=cfg['throttle_actuator_min_pulse'],
                                                  max_pulse=cfg['throttle_actuator_max_pulse'],
                                                  zero_pulse=cfg['throttle_actuator_zero_pulse'])

    mysteering = dk.actuators.PWMSteeringActuator(controller=mysteeringcontroller,
                                                  left_pulse=cfg['steering_actuator_min_pulse'],
                                                  right_pulse=cfg['steering_actuator_max_pulse'])


    #Set up your PWM values for your steering and throttle actuator here. 
    mythrottle = dk.actuators.PWMThrottleActuator(controller=mythrottlecontroller, 
                                                  min_pulse=1,
                                                  max_pulse=2,
                                                  zero_pulse=1.5)

    mysteering = dk.actuators.PWMSteeringActuator(controller=mysteeringcontroller,
                                                  left_pulse=1,
                                                  right_pulse=2)

    mymixer = dk.mixers.FrontSteeringMixer(mysteering, mythrottle)

    #abstract class to combine actuators
    mymixer = dk.mixers.AckermannSteeringMixer(mysteering, mythrottle)

    #asych img capture from picamera
    mycamera = dk.sensors.PiVideoStream()
    
    #setup the remote host
    myremote = dk.remotes.RemoteClient(remote_url, vehicle_id=cfg['vehicle_id'])

    #setup a local pilot
    mypilot = dk.pilots.KerasCategorical(model_path=cfg['pilot_model_path'])
    mypilot.load()

    #Create your car
    car = dk.vehicles.BaseVehicle(drive_loop_delay=cfg['vehicle_loop_delay'],
                                  camera=mycamera,
                                  actuator_mixer=mymixer,
                                  remote=myremote,
                                  pilot=mypilot)
    
    #Start the drive loop
    car.start()
