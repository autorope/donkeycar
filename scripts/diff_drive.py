"""
Script to run on the Raspberry PI to start your vehicle's drive loop. The drive loop
will use post requests to the server specified in the remote argument. Use the
serve.py script to start the remote server.

Usage:
    drive.py [--remote=<name>] [--config=<name>]


Options:
  --remote=<name>   recording session name
  --config=<name>   vehicle configuration file name (without extension)  [default: diff_vehicle]
"""

import os
from docopt import docopt

import donkey as dk

# Get args.
args = docopt(__doc__)

if __name__ == '__main__':

    cfg = dk.config.parse_config('~/mydonkey/' + args['--config'] + '.ini')

    remote_url = args['--remote']

    left_motor = dk.actuators.Adafruit_Motor_Hat_Controller(cfg['left_actuator_channel'])
    right_motor = dk.actuators.Adafruit_Motor_Hat_Controller(cfg['right_actuator_channel'])
    dd = dk.mixers.DifferentialDriveMixer(left_motor=left_motor,
                                 right_motor =right_motor)

    #asych img capture from picamera
    mycamera = dk.sensors.PiVideoStream()

    #Get all autopilot signals from remote host
    mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id=vehicle_id=cfg['vehicle_id'])

    #Create your car
    car = dk.vehicles.BaseVehicle(drive_loop_delay=cfg['vehicle_loop_delay'],
                                  camera=mycamera,
                                  actuator_mixer=dd,
                                  pilot=mypilot)
    car.start()
