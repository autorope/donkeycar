"""
Author: Ed Murphy
File: realsense435i.py
Date: April 14 2019
Notes: Donkeycar part for the Intel Realsense depth cameras D435 and D435i.
"""
import time
import logging

import numpy as np
import pyrealsense2 as rs


class RealSense435i(object):
    """
    Donkeycar part for the Intel Realsense depth cameras D435 and D435i.
    The Intel Realsense D435i camera is a device which uses an imu, twin fisheye cameras,
    and an Movidius chip to stream a depth map along with an rgb image and optionally,
    accelerometer and gyro data (the 'i' variant has an IMU, the non-i variant does not)
    """

    def __init__(self, enable_rgb=True, enable_depth=True, enable_imu=False, device_id = None):
        self.device_id = device_id  # "923322071108" # serial number of device to use or None to use default
        self.enable_imu = enable_imu
        self.enable_rgb = enable_rgb
        self.enable_depth = enable_depth

        # Configure streams
        if self.enable_imu:
            self.imu_pipeline = rs.pipeline()
            imu_config = rs.config()
            if None != self.device_id:
                imu_config.enable_device(self.device_id)
            imu_config.enable_stream(rs.stream.accel, rs.format.motion_xyz32f, 63)  # acceleration
            imu_config.enable_stream(rs.stream.gyro, rs.format.motion_xyz32f, 200)  # gyroscope
            imu_profile = self.imu_pipeline.start(imu_config)

        if self.enable_depth or self.enable_rgb:
            self.pipeline = rs.pipeline()
            config = rs.config()

            # if we are provided with a specific device, then enable it
            if None != self.device_id:
                config.enable_device(self.device_id)

            if self.enable_depth:
                config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 60)  # depth

            if self.enable_rgb:
                config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 60)  # rgb

            # Start streaming
            profile = self.pipeline.start(config)

            # Getting the depth sensor's depth scale (see rs-align example for explanation)
            if self.enable_depth:
                depth_sensor = profile.get_device().first_depth_sensor()
                depth_scale = depth_sensor.get_depth_scale()
                print("Depth Scale is: ", depth_scale)
                if self.enable_rgb:
                    # Create an align object
                    # rs.align allows us to perform alignment of depth frames to others frames
                    # The "align_to" is the stream type to which we plan to align depth frames.
                    align_to = rs.stream.color
                    self.align = rs.align(align_to)

        time.sleep(1)   # let camera warm up

        # initialize frame state
        self.color_image = None
        self.depth_image = None
        self.acceleration = None
        self.gyroscope = None
        self.frame_count = 0
        self.start_time = time.time()
        self.frame_time = self.start_time

    def _poll(self):
        last_time = self.frame_time
        self.frame_time = time.time() - self.start_time
        self.frame_count += 1

        #
        # get the frames
        #
        try:
            if self.enable_rgb or self.enable_depth:
                frames = self.pipeline.wait_for_frames(200 if (self.frame_count > 1) else 10000) # wait 10 seconds for first frame

            if self.enable_imu:
                imu_frames = self.imu_pipeline.wait_for_frames(200 if (self.frame_count > 1) else 10000)
        except Exception as e:
            logging.error(e)
            return

        #
        # convert camera frames to images
        #
        if self.enable_rgb or self.enable_depth:
            # Align the depth frame to color frame
            aligned_frames = self.align.process(frames) if self.enable_depth and self.enable_rgb else None
            depth_frame = aligned_frames.get_depth_frame() if aligned_frames is not None else frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame() if aligned_frames is not None else frames.get_color_frame()

            # Convert images to numpy arrays
            self.depth_image = np.asanyarray(depth_frame.get_data()) if self.enable_depth else None
            self.color_image = np.asanyarray(color_frame.get_data()) if self.enable_rgb else None

        if self.enable_imu:
            self.acceleration = imu_frames.first_or_default(rs.stream.accel, rs.format.motion_xyz32f).as_motion_frame().get_motion_data()
            self.gyroscope = imu_frames.first_or_default(rs.stream.gyro, rs.format.motion_xyz32f).as_motion_frame().get_motion_data()
            logging.debug("imu frame {} in {} seconds: \n\taccel = {}, \n\tgyro = {}".format(str(self.frame_count), str(self.frame_time - last_time), str(self.acceleration), str(self.gyroscope)))

    def update(self):
        """
        When running threaded, update() is called from the background thread
        to update the state.  run_threaded() is called to return the latest state.
        """
        while self.running:
            self._poll()

    def run_threaded(self):
        """
        Return the lastest state read by update().  This will not block.
        All 4 states are returned, but may be None if the feature is not enabled when the camera part is constructed.
        For gyroscope, x is pitch, y is yaw and z is roll.
        :return: (rbg_image: nparray, depth_image: nparray, acceleration: (x:float, y:float, z:float), gyroscope: (x:float, y:float, z:float))
        """
        return self.color_image, self.depth_image, self.acceleration, self.gyroscope

    def run(self):
        """
        Read and return frame from camera.  This will block while reading the frame.
        see run_threaded() for return types.
        """
        self._poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        if self.imu_pipeline is not None:
            self.imu_pipeline.stop()
        if self.pipeline is not None:
            self.pipeline.stop()


#
# self test
#
if __name__ == "__main__":
    frame_count = 0
    start_time = time.time()
    frame_time = start_time

    try:
        #
        # for D435i, enable_imu can be True, for D435 enable_imu should be false
        #
        camera = RealSense435i(enable_rgb=True, enable_depth=True, enable_imu=True)
        while True:
            rgb, depth, acceleration, gyroscope = camera.run()
            last_time = frame_time
            frame_time = time.time()
            print("imu frame {} in {} seconds: \n\taccel = {}, \n\tgyro = {}".format(str(frame_count), str(
                frame_time - last_time), str(acceleration), str(gyroscope)))
            time.sleep(0.05)
    finally:
        camera.shutdown()
