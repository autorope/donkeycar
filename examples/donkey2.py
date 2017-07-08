# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.

"""
import donkey as dk 

V = dk.vehicle.Vehicle()

cam = dk.parts.PiCamera()
V.add(cam, outputs=['cam/image_array'])

ctr = dk.parts.LocalWebController()
V.add(ctr, 
      inputs=['square/image_array'],
      outputs=['user/angle', 'user/throttle', 'user/mode'],
      threaded=True)


#initialize values


steering_controller = dk.parts.PCA9685(1)
steering = dk.parts.PWMSteering(controller=steering_controller)

throttle_controller = dk.parts.PCA9685(0)
throttle = dk.parts.PWMThrottle(controller=throttle_controller)

V.add(steering, inputs=['user/angle'])
V.add(throttle, inputs=['user/throttle'])

#run the vehicle for 20 seconds
V.start(rate_hz=50, max_loop_count=1000)

#you can now go to localhost:8887 to move a square around the image