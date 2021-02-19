#!/usr/bin/env python
# -*- coding: utf-8 -*-
## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2019 Intel Corporation. All Rights Reserved.
from __future__ import print_function

"""
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
import time
import numpy as np
import matplotlib.pyplot as plt
import threading
#import pyformulas as pf

mm_per_tick = 0.0605 
m_per_tick = mm_per_tick / 1000.0
prev_distance = 0
distance = 0
delta_distance = 0
last_time = time.time()
velocity = 0
ticks = 0
lasttick = 0
xlist = np.array([0]) 
ylist = np.array([0])
dotcolor = np.array(['black'])
area = np.array([25]) 
counter = 1
x = 0
y = 0

lasttime = time.time()
lasttime2 = time.time()
lasttime3 = time.time()

# fig = plt.figure()
# canvas = np.zeros((480,640))
# screen = pf.screen(canvas, 'Position')
# # plt.xlim(-0.1, 0.1)
# # plt.ylim(-0.1, 0.1)

plt.ion()
plt.show(block=False)


ave_velocity = []
for i in range(10):
    ave_velocity.append(0)
port = '/dev/ttyACM0'
baud = 9600

for item in serial.tools.list_ports.comports():
    print(item)  # list all the serial ports
ser = serial.Serial(port, baud, timeout = 0.1)
# initialize the odometer values
ser.write(str.encode('reset'))  # restart the encoder to zero
# load wheel odometry config before pipe.start(...)
# get profile/device/ wheel odometry sensor by profile = cfg.resolve(pipe)
pipe = rs.pipeline()
cfg = rs.config()
profile = cfg.resolve(pipe)
dev = profile.get_device()
tm2 = dev.as_tm2()

def parse_serial(ticks):
    global lasttime, prev_distance
    start_time = lasttime
    end_time = time.time()
    lasttime = end_time
    #calculate elapsed time and distance traveled
    seconds = end_time - start_time
    distance = ticks * m_per_tick
    delta_distance = distance - prev_distance
    prev_distance = distance
    instant_velocity = delta_distance/seconds
    # for i in range(9):  # do a moving average over a 1/2 second window (10 readings of a 20Hz feed)
    #     ave_velocity[9-i] = ave_velocity[8-i]  # move the time window down one
    # ave_velocity[0] = instant_velocity  # stick the latest reading at the start
    # velocity = sum(ave_velocity)/10  # moving average
    velocity = instant_velocity
    print("Total distance", distance, "Delta distance", delta_distance)
    print("Velocity", velocity)
    return velocity

def read_serial(ser):
    global lasttime2, lasttick
    newdata = False
    input = ''
    lasttime2 = time.time()
    while (ser.in_waiting > 0) and (time.time() < lasttime2 + 0.1):   # read the serial port for a millisecond
        buffer = ser.readline()
        input = buffer.decode('ascii')
    if input != '':
        temp = input.strip()  # remove any whitespace
        if (temp.isnumeric()):
            ticks = int(temp)
            newdata = True
            lasttick = ticks
    if newdata:
        return ticks
    else:
        return lasttick

def plot(x,y):
    global counter, xlist, ylist, dotcolor, area, lasttime3
    plt.pause(0.0001)
    if time.time() > lasttime3 + 0.5:  # plot twice per second
        lasttime3 = time.time()
        for i in range(counter):   # make all older points smaller and black
            dotcolor[i] = 'black'
            area[i] = 6
        xlist = np.append(xlist, x)
        ylist = np.append(ylist, y)
        dotcolor = np.append(dotcolor,'red')
        area = np.append(area, 25)
        counter += 1
        plt.cla()
        plt.xlim(-0.1, 0.1)
        plt.ylim(-0.1, 0.1)
    #   plt.autoscale(False)
        plt.scatter(xlist, ylist, s=area, c=dotcolor)
        plt.pause(0.0001)
        # fig.canvas.draw()
        # image = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
        # image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        # screen.update(image)

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
    try:
        while True:
#            ticks = read_serial(ser)
#            velocity = parse_serial(ticks)
            if velocity != 0:
                v = rs.vector()
                wo_sensor_id = 0  # indexed from 0, match to order in calibration file
                frame_num = 0  # not used
                v.z = velocity  # m/s
                wheel_odometer.send_wheel_odometry(wo_sensor_id, frame_num, v)
            frames = pipe.wait_for_frames()
            pose = frames.get_pose_frame()
            if pose:
                data = pose.get_pose_data()
                print("Position: {}".format(data.translation))
                pos = data.translation
                x = pos.x
                y = pos.y
#                plot(x,y)

            else:
                print("no pose?")
    except KeyboardInterrupt:
        print("stopping...")
        pipe.stop()