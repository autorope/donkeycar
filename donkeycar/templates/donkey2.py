#!/usr/bin/env python3
"""
Upload a file to S3 (requires amazon credentials).

Usage:
    drive.py (--rate_hz=<rate_hz>) [--bucket=<buck

Options:
  --file_path=<file_path> name of dataset file to save.
  --bucket=<bucket>  name of S3 bucket to upload data. [default: donkey_resources].
"""

import os
import donkeycar as dk 

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')

#Initialized car
V = dk.vehicle.Vehicle()
cam = dk.parts.PiCamera()
V.add(cam, outputs=['cam/image_array'], threaded=True)

ctr = dk.parts.LocalWebController()
V.add(ctr, 
      inputs=['cam/image_array'],
      outputs=['user/angle', 'user/throttle', 'user/mode'],
      threaded=True)


steering_controller = dk.parts.PCA9685(1)
steering = dk.parts.PWMSteering(controller=steering_controller,
                                left_pulse=460, right_pulse=260)

throttle_controller = dk.parts.PCA9685(0)
throttle = dk.parts.PWMThrottle(controller=throttle_controller,
                                max_pulse=500, zero_pulse=370, min_pulse=220)

V.add(steering, inputs=['user/angle'])
V.add(throttle, inputs=['user/throttle'])

#add tub to save data
path=os.path.join(DATA_PATH, 'tub1')
inputs=['user/angle', 'user/throttle', 'cam/image_array']
types=['float', 'float', 'image_array']
tub=dk.parts.TubWriter(path, inputs=inputs, types=types)
V.add(tub, inputs=inputs)

#run the vehicle for 20 seconds




V.start(rate_hz=10, max_loop_count=1000)

print("You can now go to localhost:8887 to move a square around the image.")
#
