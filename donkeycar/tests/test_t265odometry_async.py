#!/usr/bin/env python
# -*- coding: utf-8 -*-
## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2019 Intel Corporation. All Rights Reserved.
from __future__ import print_function

from numpy.core.shape_base import block

"""
Must install pyserial-asyncio via "pip install pyserial-asyncio" first

This example shows how to fuse wheel odometry measurements (in the form of 3D translational velocity measurements) on the T265 tracking camera to use them together with the (internal) visual and intertial measurements.
This functionality makes use of two API calls:
1. Configuring the wheel odometry by providing a json calibration file (in the format of the accompanying calibration file)
Please refer to the description of the calibration file format here: https://github.com/IntelRealSense/librealsense/blob/master/doc/t265.md#wheel-odometry-calibration-file-format.
2. Sending wheel odometry measurements (for every measurement) to the camera

Expected output:
For a static camera, the pose output is expected to move in the direction of the (artificial) wheel odometry measurements (taking into account the extrinsics in the calibration file).
The measurements are given a high weight/confidence, i.e. low measurement noise covariance, in the calibration file to make the effect visible.
If the camera is partially occluded the effect will be even more visible (also for a smaller wheel odometry confidence / higher measurement noise covariance) because of the lack of visual feedback. Please note that if the camera is *fully* occluded the pose estimation will switch to 3DOF, estimate only orientation, and prevent any changes in the position.
"""

import pyrealsense2.pyrealsense2 as rs
import serial
import serial.tools.list_ports
import asyncio
from serial_asyncio import open_serial_connection
import time
import numpy as np
import matplotlib.pyplot as plt
import pyformulas as pf
import time



mm_per_tick = 0.0605 
m_per_tick = mm_per_tick / 1000.0
prev_distance = 0
distance = 0
delta_distance = 0
last_time = time.time()
velocity = 0
ticks = 0
x = 0
y = 0


PORT_NAME = '/dev/ttyACM0' # this is for the Arduino

stop = False
lasttime = time.time()
lasttime2 = time.time()
lasttime3 = time.time()

ave_velocity = []
for i in range(10):
    ave_velocity.append(0)

for item in serial.tools.list_ports.comports():
    print(item)  # list all the serial ports

# load wheel odometry config before pipe.start(...)
# get profile/device/ wheel odometry sensor by profile = cfg.resolve(pipe)
pipe = rs.pipeline()
cfg = rs.config()
profile = cfg.resolve(pipe)
dev = profile.get_device()
tm2 = dev.as_tm2()

fig = plt.figure()

canvas = np.zeros((480,640))
screen = pf.screen(canvas, 'Position')

def parse_serial(ticks):
    global lasttime, prev_distance, ave_velocity
    start_time = lasttime
    end_time = time.time()
    lasttime = end_time
    #calculate elapsed time and distance traveled
    seconds = end_time - start_time
    distance = ticks * m_per_tick
    delta_distance = distance - prev_distance
    prev_distance = distance
    instant_velocity = delta_distance/seconds
    for i in range(9):  # do a moving average over a 1/2 second window (10 readings of a 20Hz feed)
        ave_velocity[9-i] = ave_velocity[8-i]  # move the time window down one
    ave_velocity[0] = instant_velocity  # stick the latest reading at the start
    velocity = sum(ave_velocity)/10  # moving average
    # velocity = instant_velocity
    print("Total distance", distance, "Delta distance", delta_distance)
    print("Velocity", velocity)
    return velocity

async def encoder():
    global lasttime, lasttime3, ticks, velocity

    print("Opened", reader)
    writer.write(str.encode('reset'))  # restart the encoder to zero
    while True:
        if stop == True:
            ioloop.stop
            task.cancel(encoder())
        if time.time() > (lasttime + 0.001):  # read the serial port a thousand time a second
            #calculate elapsed time and distance traveled
            print("Checking serial")
            input = await reader.readline()
            print("Serial output", input)
            temp = input.strip()  # remove any whitespace
            if (temp.isnumeric()):
                ticks = int(temp)
            lasttime = time.time()  # reset 10Hz time
        if time.time() > (lasttime3 + 0.01):  # report the velocity a hundred times a second
            print("parsing")
            lasttime3 = time.time()
            velocity = parse_serial(ticks)
        await asyncio.sleep(0)  # go back to running other threads

async def realsense():
    global lasttime2, x, y
    if(tm2):
        # tm2.first_wheel_odometer()?
        pose_sensor = tm2.first_pose_sensor()
        wheel_odometer = pose_sensor.as_wheel_odometer()

        # calibration to list of uint8
        f = open("calibration_odometry.json")
        chars = []
        for line in f:
            for c in line:
                chars.append(ord(c))  # char to uint8

        # load/configure wheel odometer
        wheel_odometer.load_wheel_odometery_config(chars)
        pipe.start(cfg)
        while True:
            if stop == True:
                task.cancel(realsense())
                ioloop.stop
            if time.time() > lasttime2 + 0.1: # run this ten times a second 
                frames = pipe.wait_for_frames()
                pose = frames.get_pose_frame()
                if pose:
                    data = pose.get_pose_data()
                    print("Position: {}".format(data.translation))
                    pos = data.translation
                    x = pos.x
                    y = pos.y
                    # provide wheel odometry as vecocity measurement
                    wo_sensor_id = 0  # indexed from 0, match to order in calibration file
                    frame_num = 0  # not used
                    v = rs.vector()
                    v.z = velocity  # m/s
                    wheel_odometer.send_wheel_odometry(wo_sensor_id, frame_num, v)
                lasttime2 = time.time()
            await asyncio.sleep(0)  # go back to running other threads

async def plot():
    global lasttime3
    while True:
        if stop == True:
            task.cancel(plot())
            ioloop.stop
        if time.time() > lasttime3 + 1.0: # run this once per second
            lasttime3 = time.time()
            print("this is a plot")
        await asyncio.sleep(0)  # go back to running other threads

def run():
    '''Main function'''
    global stop
    print("Starting program")
    if stop == False:
        ioloop = asyncio.get_event_loop()
        coro = serial_asyncio.create_serial_connection(ioloop, Output, PORT_NAME, baudrate=9600)
        tasks = [
                ioloop.create_task(coro()),
                ioloop.create_task(realsense()),
                ioloop.create_task(plot())
                ]
        try:
            ioloop.run_until_complete(asyncio.wait(tasks))
            while True:
                realsense()
        except KeyboardInterrupt:
            print('Stopping.')
            stop = True
            ioloop.close()
        
 
if __name__ == '__main__':
    run()