# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.

"""
import donkey as dk 

V = dk.vehicle.Vehicle()

#initialize values
V.mem.put(['square/x', 'square/y'], (100,100))


#display square box given by cooridantes.
cam = dk.sensors.SquareBoxCamera(resolution=(200,200))
V.add(cam, 
      inputs=['square/x', 'square/y'],
      outputs=['square/image_array'])

#display the image and read user values from a local web controller
ctr = dk.controllers.LocalWebController()
V.add(ctr, 
      inputs=['square/image_array'],
      outputs=['user/angle', 'user/throttle', 'user/mode'],
      threaded=True)

#transform angle and throttle values to coordinate values
f = lambda x : int(x * 100 + 100)
l = dk.transforms.Lambda(f)
V.add(l, inputs=['user/angle'], outputs=['square/x'])
V.add(l, inputs=['user/throttle'], outputs=['square/y'])

#run the vehicle for 20 seconds
V.start(rate_hz=50, max_loop_count=1000)

#you can now go to localhost:8887 to move a square around the image