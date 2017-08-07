# -*- coding: utf-8 -*-
"""
Record a moving square example.

This example simulates a square that bounces around a frame
and records the frames and coordinates to disk.

"""
import donkeycar as dk 
import os

CAR_PATH = PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(CAR_PATH, 'data')

#make the membory 
V = dk.Vehicle()

#telemetry simulator to make box bounce off walls
tel = dk.parts.MovingSquareTelemetry(max_velocity=5)
V.add(tel, 
      outputs=['square/x', 'square/y'])

#fake camera that shows a square at specific coordinates
cam = dk.parts.SquareBoxCamera(resolution=(120,160), 
                                 box_size=10, 
                                 color=[33,200,2])
V.add(cam, 
      inputs=['square/x', 'square/y'], 
      outputs=['square/image_array'])

#Add a datastore to record the images.
inputs = ['square/x', 'square/y', 'square/image_array']
types = ['float', 'float', 'image_array']
#add tub to save data
th = dk.parts.TubHandler(path=DATA_PATH)
tub = th.new_tub_writer(inputs=inputs, types=types)
V.add(tub, inputs=inputs)


#Run vehicel for 10 loops
V.start(max_loop_count=100, rate_hz=1000)