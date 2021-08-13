"""
Author: Manav Gagvani
File: realsensel515.py
Date: August 11th, 2021
Notes: Donkeycar part for the Intel Realsense LIDAR L515
"""
import time
import numpy as np
import pyrealsense2.pyrealsense2 as rs


import cv2

class RealSensel515(object):
    """
    Donkeycar part for the Intel Realsense depth camera L515.
    """

    def __init__(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30) # will need to downscale later
        self.config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30) # will need to downscale later
        self.pipeline.start(self.config)

        align_to = rs.stream.depth
        self.align = rs.align(align_to)

        # time.sleep(1)
        self.running = True
        
        self.depth_image = None # init 
        self.color_image = None



    def _poll(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)

        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not depth_frame or color_frame:
            print("Error in frame.")
            
        print(type(depth_frame.get_data()))
        depth_image = np.asarray(depth_frame.get_data())
        color_image = np.asarray(color_frame.get_data())
        self.depth_image = cv2.resize(depth_image, dsize=(160,120), interpolation=cv2.INTER_NEAREST)
        self.color_image = cv2.resize(color_image, dsize=(160,120), interpolation=cv2.INTER_NEAREST)


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
        return self.color_image, self.depth_image

    def run(self):
        """
        Read and return frame from camera.  This will block while reading the frame.
        see run_threaded() for return types.
        """
        self._poll()
        return self.run_threaded()

    def _stop_pipeline(self):
        self.pipeline.stop()

    def shutdown(self):
        self.running = False
        time.sleep(2) # give thread enough time to shutdown

        # done running
        self._stop_pipeline()

