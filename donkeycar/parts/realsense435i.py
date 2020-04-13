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

#
# NOTE: Jetson Nano users should clone the Jetson Hacks project
#       https://github.com/JetsonHacksNano/installLibrealsense
#       and _build librealsense from source_ in order to get the python bindings.
#       ./buildLibrealsense.sh
#

#
# The Realsense D435 will not output images with arbitrarily chosen dimensions.
# The dimensions must be from the allowed list.  I've chosen a reasonable
# resolution that I know is supported by the camera.
# If the part is initialized with different sizes, then opencv
# will be used to resize the image before it is returned.
#
WIDTH = 424
HEIGHT = 240
CHANNELS = 3

class RealSense435i(object):
    """
    Donkeycar part for the Intel Realsense depth cameras D435 and D435i.
    The Intel Realsense D435i camera is a device which uses an imu, twin fisheye cameras,
    and an Movidius chip to stream a depth map along with an rgb image and optionally,
    accelerometer and gyro data (the 'i' variant has an IMU, the non-i variant does not)
    NOTE: this ALWAYS captures 424 pixels wide x 240 pixels high x RGB at 60fps.
          If an image width, height or depth are passed with different values,
          the the outputs will be scaled to the requested size on the way out.
    """

    def __init__(self, width = WIDTH, height = HEIGHT, channels = CHANNELS, enable_rgb=True, enable_depth=True, enable_imu=False, device_id = None):
        self.device_id = device_id  # "923322071108" # serial number of device to use or None to use default
        self.enable_imu = enable_imu
        self.enable_rgb = enable_rgb
        self.enable_depth = enable_depth

        self.width = width
        self.height = height
        self.channels = channels
        self.resize = (width != WIDTH) or (height != height) or (channels != CHANNELS)
        if self.resize:
            print("The output images will be resized from {} to {}.  This requires opencv.".format((WIDTH, HEIGHT, CHANNELS), (self.width, self.height, self.channels)))

        # Configure streams
        self.imu_pipeline = None
        if self.enable_imu:
            self.imu_pipeline = rs.pipeline()
            imu_config = rs.config()
            if None != self.device_id:
                imu_config.enable_device(self.device_id)
            imu_config.enable_stream(rs.stream.accel, rs.format.motion_xyz32f, 63)  # acceleration
            imu_config.enable_stream(rs.stream.gyro, rs.format.motion_xyz32f, 200)  # gyroscope
            imu_profile = self.imu_pipeline.start(imu_config)
            # eat some frames to allow imu to settle
            for i in range(0, 5):
                self.imu_pipeline.wait_for_frames()

        self.pipeline = None
        if self.enable_depth or self.enable_rgb:
            self.pipeline = rs.pipeline()
            config = rs.config()

            # if we are provided with a specific device, then enable it
            if None != self.device_id:
                config.enable_device(self.device_id)

            if self.enable_depth:
                config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 60)  # depth

            if self.enable_rgb:
                config.enable_stream(rs.stream.color, 424, 240, rs.format.rgb8, 60)  # rgb

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

            # eat some frames to allow auto-exposure to settle
            for i in range(0, 5):
                self.pipeline.wait_for_frames()

        time.sleep(2)   # let camera warm up

        # initialize frame state
        self.color_image = None
        self.depth_image = None
        self.acceleration_x = None
        self.acceleration_y = None
        self.acceleration_z = None
        self.gyroscope_x = None
        self.gyroscope_y = None
        self.gyroscope_z = None
        self.frame_count = 0
        self.start_time = time.time()
        self.frame_time = self.start_time

        self.running = True

    def _stop_pipeline(self):
        if self.imu_pipeline is not None:
            self.imu_pipeline.stop()
            self.imu_pipeline = None
        if self.pipeline is not None:
            self.pipeline.stop()
            self.pipeline = None

    def _poll(self):
        last_time = self.frame_time
        self.frame_time = time.time() - self.start_time
        self.frame_count += 1

        #
        # get the frames
        #
        try:
            if self.enable_imu:
                imu_frames = self.imu_pipeline.wait_for_frames()

            if self.enable_rgb or self.enable_depth:
                frames = self.pipeline.wait_for_frames()
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

            # Convert depth to 16bit array, RGB into 8bit planar array
            self.depth_image = np.asanyarray(depth_frame.get_data(), dtype=np.uint16) if self.enable_depth else None
            self.color_image = np.asanyarray(color_frame.get_data(), dtype=np.uint8) if self.enable_rgb else None

            if self.resize:
                import cv2
                if self.width != WIDTH or self.height != HEIGHT:
                    self.color_image = cv2.resize(self.color_image, (self.width, self.height), cv2.INTER_NEAREST) if self.enable_rgb else None
                    self.depth_image = cv2.resize(self.depth_image, (self.width, self.height), cv2.INTER_NEAREST) if self.enable_depth else None
                if self.channels != CHANNELS:
                    self.color_image = cv2.cvtColor(self.color_image, cv2.COLOR_RGB2GRAY) if self.enable_rgb else None

        #
        # output imu data as discrete values in the same order as the Mpu6050 code
        # so we can be compatible with any other parts that consume imu data.
        #
        if self.enable_imu:
            acceleration = imu_frames.first_or_default(rs.stream.accel, rs.format.motion_xyz32f).as_motion_frame().get_motion_data()
            self.acceleration_x = acceleration.x
            self.acceleration_y = acceleration.y
            self.acceleration_z = acceleration.z
            gyroscope = imu_frames.first_or_default(rs.stream.gyro, rs.format.motion_xyz32f).as_motion_frame().get_motion_data()
            self.gyroscope_x = gyroscope.x
            self.gyroscope_y = gyroscope.y
            self.gyroscope_z = gyroscope.z
            logging.debug("imu frame {} in {} seconds: \n\taccel = {}, \n\tgyro = {}".format(
                str(self.frame_count),
                str(self.frame_time - last_time),
                str((self.acceleration_x, self.acceleration_y, self.acceleration_z)),
                str((self.gyroscope_x, self.gyroscope_y, self.gyroscope_z))))

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
        return self.color_image, self.depth_image, self.acceleration_x, self.acceleration_y, self.acceleration_z, self.gyroscope_x, self.gyroscope_y, self.gyroscope_z

    def run(self):
        """
        Read and return frame from camera.  This will block while reading the frame.
        see run_threaded() for return types.
        """
        self._poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(2) # give thread enough time to shutdown

        # done running
        self._stop_pipeline()


#
# self test
#
if __name__ == "__main__":

    show_opencv_window = False # True to show images in opencv window: note that default donkeycar environment is not configured for this.
    if show_opencv_window:
        import cv2

    enable_rgb = True
    enable_depth = True
    enable_imu = True
    device_id = None

    width = 212
    height = 120
    channels = 3

    profile_frames = 0 # set to non-zero to calculate the max frame rate using given number of frames

    try:
        #
        # for D435i, enable_imu can be True, for D435 enable_imu should be false
        #
        camera = RealSense435i(
            width=width, height=height, channels=channels,
            enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)

        frame_count = 0
        start_time = time.time()
        frame_time = start_time
        while True:
            #
            # read data from camera
            #
            color_image, depth_image, acceleration_x, acceleration_y, acceleration_z, gyroscope_x, gyroscope_y, gyroscope_z = camera.run()

            # maintain frame timing
            frame_count += 1
            last_time = frame_time
            frame_time = time.time()

            if enable_imu and not profile_frames:
                print("imu frame {} in {} seconds: \n\taccel = {}, \n\tgyro = {}".format(
                    str(frame_count),
                    str(frame_time - last_time),
                    str((acceleration_x, acceleration_y, acceleration_z)),
                    str((gyroscope_x, gyroscope_y, gyroscope_z))))

            # Show images
            if show_opencv_window and not profile_frames:
                cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
                if enable_rgb or enable_depth:
                    # make sure depth and color images have same number of channels so we can show them together in the window
                    if 3 == channels:
                        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET) if enable_depth else None
                    else:
                        depth_colormap = cv2.cvtColor(cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET), cv2.COLOR_RGB2GRAY) if enable_depth else None


                    # Stack both images horizontally
                    images = None
                    if enable_rgb:
                        images = np.hstack((color_image, depth_colormap)) if enable_depth else color_image
                    elif enable_depth:
                        images = depth_colormap

                    if images is not None:
                        cv2.imshow('RealSense', images)

                # Press esc or 'q' to close the image window
                key = cv2.waitKey(1)
                if key & 0xFF == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    break
            if profile_frames > 0:
                if frame_count == profile_frames:
                    print("Aquired {} frames in {} seconds for {} fps".format(str(frame_count), str(frame_time - start_time), str(frame_count / (frame_time - start_time))))
                    break
            else:
                time.sleep(0.05)
    finally:
        camera.shutdown()
