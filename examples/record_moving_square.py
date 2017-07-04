# -*- coding: utf-8 -*-

import donkey as dk 

#make the membory 
V = dk.vehicle.Vehicle()

#telemetry simulator to make box bounce off walls
tel = dk.simulations.MovingSquareTelemetry(max_velocity=5)
V.add(tel, 
      outputs=['square/x', 'square/y'])

#fake camera that shows a square at specific coordinates
cam = dk.sensors.SquareBoxCamera(resolution=(120,160), 
                                 box_size=10, 
                                 color=[33,200,2])
V.add(cam, 
      inputs=['square/x', 'square/y'], 
      outputs=['square/image_array'])

#Add a datastore to record the images.
inputs = ['square/x', 'square/y', 'square/image_array']
types = ['float', 'float', 'image_array']
path='~/mydonkey/sessions/tub_test'
tub = dk.datastores.Tub(path, inputs, types)
V.add(tub, inputs=inputs)


#Run vehicel for 10 loops
V.start(max_loop_count=100, rate_hz=1000)