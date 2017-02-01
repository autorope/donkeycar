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

    lf_pwm = dk.actuators.NAVIO2_Controller(channel=0)
    lf_f = dk.actuators.NAVIO2_Controller(channel=1)
    lf_r = dk.actuators.NAVIO2_Controller(channel=2)

    rf_pwm = dk.actuators.NAVIO2_Controller(channel=3)
    rf_f = dk.actuators.NAVIO2_Controller(channel=4)
    rf_r = dk.actuators.NAVIO2_Controller(channel=5)

    lr_pwm = dk.actuators.NAVIO2_Controller(channel=6)
    lr_f = dk.actuators.NAVIO2_Controller(channel=7)
    lr_r = dk.actuators.NAVIO2_Controller(channel=8)

    rr_pwm = dk.actuators.NAVIO2_Controller(channel=9)
    rr_f = dk.actuators.NAVIO2_Controller(channel=10)
    rr_r = dk.actuators.NAVIO2_Controller(channel=11)

    #Set up your PWM values for your actuators here. 
    lf = dk.actuators.PWMThrottleActuator(controllerPWM=lf_pwm, 
                                          controllerF=lf_f,
                                          controllerR=lf_r)

    rf = dk.actuators.PWMThrottleActuator(controllerPWM=rf_pwm, 
                                          controllerF=rf_f,
                                          controllerR=rf_r)

    lr = dk.actuators.PWMThrottleActuator(controllerPWM=lr_pwm, 
                                          controllerF=lr_f,
                                          controllerR=lr_r)

    rr = dk.actuators.PWMThrottleActuator(controllerPWM=rr_pwm, 
                                          controllerF=rr_f,
                                          controllerR=rr_r)

    mymixer = dk.mixers.MecanumMixer(lf, rf, lr, rr)

    #asych img capture from picamera
    
    #Get all autopilot signals from remote host
    mypilot = dk.remotes.RemoteClient(remote_url, vehicle_id='mycar')

    #Create your car
    car = dk.vehicles.BaseVehicle(drive_loop_delay=.05,
                                  camera=mycamera,
                                  actuator_mixer=mymixer)
    
    #Start the drive loop
    car.start()
