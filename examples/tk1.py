# -*- coding: utf-8 -*-

"""
Script to drive a donkey car using a webserver hosted on the vehicle.

"""
import donkey as dk

V = dk.vehicle.Vehicle()

cam = dk.parts.Webcam()
V.add(cam, outputs=['cam/image_array'], threaded = True)

ctr = dk.parts.LocalWebController()
V.add(ctr,
      inputs = ['cam/image_array'],
      outputs = ['user/angle', 'user/throttle', 'user/mode'],
      threaded = True)


steering_controller = dk.parts.Teensy('S')
steering = dk.parts.PWMSteering(controller = steering_controller,
                                left_pulse = 460, right_pulse = 276)

throttle_controller = dk.parts.Teensy('T')
throttle = dk.parts.PWMThrottle(controller = throttle_controller,
                                max_pulse = 460, zero_pulse = 368, min_pulse = 276)

V.add(steering, inputs=['user/angle'])
V.add(throttle, inputs=['user/throttle'])

rcin_controller = dk.parts.TeensyRCin()
V.add(rcin_controller, outputs = [ 'rcin/angle', 'rcin/throttle' ], threaded = True)

speed_controller = dk.parts.AStarSpeed()
V.add(speed_controller, outputs = [ 'odo/speed' ], threaded = True)

#add tub to save data
path = '~/mydonkey/sessions/tub1'
inputs = [ 'user/angle', 'user/throttle', 'cam/image_array', 'rcin/angle', 'rcin/throttle', 'odo/speed' ]
types = [ 'float', 'float', 'image_array', 'float', 'float', 'float' ]
tub = dk.parts.TubWriter(path, inputs=inputs, types=types)
V.add(tub, inputs=inputs)

#run the vehicle for 20 seconds
V.start(rate_hz=20, max_loop_count=1000)

#you can now go to localhost:8887 to move a square around the image
