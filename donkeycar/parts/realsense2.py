'''
Author: Tawn Kramer
File: realsense2.py
Date: April 14 2019
Notes: Parts to input data from Intel Realsense 2 cameras
'''
import time
import logging

import numpy as np
import pyrealsense2 as rs

class RS_T265(object):
    '''
    The Intel Realsense T265 camera is a device which uses an imu, twin fisheye cameras,
    and an Movidius chip to do sensor fusion and emit a world space coordinate frame that 
    is remarkably consistent.
    '''

    def __init__(self, image_output=False, calib_filename=None):
        # Using the image_output will grab two image streams from the fisheye cameras but return only one.
        # This can be a bit much for USB2, but you can try it. Docs recommend USB3 connection for this.
        self.image_output = image_output

        # When we have and encoder, this will be the last vel measured. 
        self.enc_vel_ms = 0.0
        self.wheel_odometer = None

        # Declare RealSense pipeline, encapsulating the actual device and sensors
        print("starting T265")
        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.pose)
        profile = cfg.resolve(self.pipe)
        dev = profile.get_device()
        tm2 = dev.as_tm2()
        

        if self.image_output:
            #right now it's required for both streams to be enabled
            cfg.enable_stream(rs.stream.fisheye, 1) # Left camera
            cfg.enable_stream(rs.stream.fisheye, 2) # Right camera

        if calib_filename is not None:
            pose_sensor = tm2.first_pose_sensor()
            self.wheel_odometer = pose_sensor.as_wheel_odometer() 

            # calibration to list of uint8
            f = open(calib_filename)
            chars = []
            for line in f:
                for c in line:
                    chars.append(ord(c))  # char to uint8

            # load/configure wheel odometer
            print("loading wheel config", calib_filename)
            self.wheel_odometer.load_wheel_odometery_config(chars)   


        # Start streaming with requested config
        self.pipe.start(cfg)
        self.running = True
        print("Warning: T265 needs a warmup period of a few seconds before it will emit tracking data.")
        
        zero_vec = (0.0, 0.0, 0.0)
        self.pos = zero_vec
        self.vel = zero_vec
        self.acc = zero_vec
        self.img = None

    def poll(self):

        if self.wheel_odometer:
            wo_sensor_id = 0  # indexed from 0, match to order in calibration file
            frame_num = 0  # not used
            v = rs.vector()
            v.x = -1.0 * self.enc_vel_ms  # m/s
            #v.z = -1.0 * self.enc_vel_ms  # m/s
            self.wheel_odometer.send_wheel_odometry(wo_sensor_id, frame_num, v)

        try:
            frames = self.pipe.wait_for_frames()
        except Exception as e:
            logging.error(e)
            return

        if self.image_output:
            #We will just get one image for now.
            # Left fisheye camera frame
            left = frames.get_fisheye_frame(1)
            self.img = np.asanyarray(left.get_data())


        # Fetch pose frame
        pose = frames.get_pose_frame()

        if pose:
            data = pose.get_pose_data()
            self.pos = data.translation
            self.vel = data.velocity
            self.acc = data.acceleration
            logging.debug('realsense pos(%f, %f, %f)' % (self.pos.x, self.pos.y, self.pos.z))


    def update(self):
        while self.running:
            self.poll()

    def run_threaded(self, enc_vel_ms):
        self.enc_vel_ms = enc_vel_ms
        return self.pos, self.vel, self.acc, self.img

    def run(self, enc_vel_ms):
        self.enc_vel_ms = enc_vel_ms
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.pipe.stop()



if __name__ == "__main__":
    c = RS_T265()
    while True:
        pos, vel, acc = c.run()
        print(pos)
        time.sleep(0.1)
    c.shutdown()
