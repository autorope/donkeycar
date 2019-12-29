'''
Author: Tawn Kramer
File: realsense2.py
Date: April 14 2019
Notes: Parts to input data from Intel Realsense 2 cameras

example from https://github.com/IntelRealSense

Author: Bo Liu
'''
import time
import cv2
import logging

import numpy as np
import pyrealsense2 as rs
import math as m

"""
Returns R, T transform from src to dst
"""
def get_extrinsics(src, dst):
    extrinsics = src.get_extrinsics_to(dst)
    R = np.reshape(extrinsics.rotation, [3,3]).T
    T = np.array(extrinsics.translation)
    return (R, T)

"""
Returns a camera matrix K from librealsense intrinsics
"""
def camera_matrix(intrinsics):
    return np.array([[intrinsics.fx,             0, intrinsics.ppx],
                     [            0, intrinsics.fy, intrinsics.ppy],
                     [            0,             0,              1]])

"""
Returns the fisheye distortion from librealsense intrinsics
"""
def fisheye_distortion(intrinsics):
    return np.array(intrinsics.coeffs[:4])


class RS_T265_StereoRectified(object):
    '''
    Use t265 stereo cameras as a single 3-ch camera stream: left, right, disparity 
    The left and right images are first stereo-rectified and aligned to the left projection center,
    then, disparity is computed and put into the 3rd channel.
    image_w and image_h defines an ROI cropping region with field of view fov in degrees
    '''

    def __init__(self, image_w=240, image_h=140, fov=120):
        # T265 image is almost square: 848 x 800. image_h defines px count from the bottom (ground)
        # here we use image_w to determine crop height start px count from the top
        # crop_height will be used to crop the image for ROI selections
        self.crop_height = image_w - image_h

        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.fisheye, 1) # Left camera
        cfg.enable_stream(rs.stream.fisheye, 2) # Right camera

        # Set up a mutex to share data between threads 
        from threading import Lock
        self.frame_mutex = Lock()
        self.frame_data = {"left"  : None,
              "right" : None,
              "timestamp_ms" : None
              }

        def callback(frame):
            if frame.is_frameset():
                frameset = frame.as_frameset()
                f1 = frameset.get_fisheye_frame(1).as_video_frame()
                f2 = frameset.get_fisheye_frame(2).as_video_frame()
                left_data = np.asanyarray(f1.get_data())
                right_data = np.asanyarray(f2.get_data())
                ts = frameset.get_timestamp()
                self.frame_mutex.acquire()
                self.frame_data["left"] = left_data
                self.frame_data["right"] = right_data
                self.frame_data["timestamp_ms"] = ts
                self.frame_mutex.release()

        # Start streaming with our callback
        self.pipe.start(cfg, callback)
        time.sleep(0.5)

        profiles = self.pipe.get_active_profile()
        streams = {"left"  : profiles.get_stream(rs.stream.fisheye, 1).as_video_stream_profile(),
               "right" : profiles.get_stream(rs.stream.fisheye, 2).as_video_stream_profile()}
        intrinsics = {"left"  : streams["left"].get_intrinsics(),
                  "right" : streams["right"].get_intrinsics()}
        
        # Print information about both cameras
        print(">>>Cal::Intrinsics::Left camera:",  intrinsics["left"])
        print(">>>Cal::Intrinsics::Right camera:", intrinsics["right"])

        (R, T) = get_extrinsics(streams["left"], streams["right"])
        print(">>>Cal::relativeExtrinsics:", (R,T))

        window_size = 5
        self.min_disp = 0
        self.num_disp = 112 - self.min_disp # 112 is a magic number from RS examples...
        self.max_disp = self.min_disp + self.num_disp
        self.stereo = cv2.StereoSGBM_create(minDisparity = self.min_disp,
                                   numDisparities = self.num_disp,
                                   blockSize = 16,
                                   P1 = 8*3*window_size**2,
                                   P2 = 32*3*window_size**2,
                                   disp12MaxDiff = 1,
                                   uniquenessRatio = 10,
                                   speckleWindowSize = 100,
                                   speckleRange = 32)
        
        # Translate the intrinsics from librealsense into OpenCV
        K_left  = camera_matrix(intrinsics["left"])
        D_left  = fisheye_distortion(intrinsics["left"])
        K_right = camera_matrix(intrinsics["right"])
        D_right = fisheye_distortion(intrinsics["right"])
       
        # We calculate the undistorted focal length:
        #
        #         h
        # -----------------
        #  \      |      /
        #    \    | f  /
        #     \   |   /
        #      \ fov /
        #        \|/

        print("initializing FoV: ",fov, " Width px: ", image_w)
        stereo_fov_rad = fov * (m.pi/180)  # fov degree desired fov
        stereo_height_px = image_w # use image_w to initialize height due to square image
        stereo_focal_px = stereo_height_px/2 / m.tan(stereo_fov_rad/2)

        # We set the left rotation to identity and the right rotation
        # the rotation between the cameras
        R_left = np.eye(3)
        R_right = R

        # The stereo algorithm needs max_disp extra pixels in order to produce valid
        # disparity on the desired output region. This changes the width, but the
        # center of projection should be on the center of the cropped image
        
        stereo_width_px = stereo_height_px + self.max_disp
        stereo_size = (stereo_width_px, stereo_height_px)
        stereo_cx = (stereo_height_px - 1)/2 + self.max_disp
        stereo_cy = (stereo_height_px - 1)/2

        # Construct the left and right projection matrices, the only difference is
        # that the right projection matrix should have a shift along the x axis of
        # baseline*focal_length
        P_left = np.array([[stereo_focal_px, 0, stereo_cx, 0],
                        [0, stereo_focal_px, stereo_cy, 0],
                        [0,               0,         1, 0]])
        P_right = P_left.copy()
        P_right[0][3] = T[0]*stereo_focal_px

        # Construct Q for use with cv2.reprojectImageTo3D. Subtract max_disp from x
        # since we will crop the disparity later
        Q = np.array([[1, 0,       0, -(stereo_cx - self.max_disp)],
                      [0, 1,       0, -stereo_cy],
                      [0, 0,       0, stereo_focal_px],
                      [0, 0, -1/T[0], 0]])

        # Create an undistortion map for the left and right camera which applies the
        # rectification and undoes the camera distortion.
        print("creating StereoRectify::UndistortionMap")
        m1type = cv2.CV_32FC1
        (lm1, lm2) = cv2.fisheye.initUndistortRectifyMap(K_left, D_left, R_left, P_left, stereo_size, m1type)
        (rm1, rm2) = cv2.fisheye.initUndistortRectifyMap(K_right, D_right, R_right, P_right, stereo_size, m1type)
        self.undistort_rectify = {"left"  : (lm1, lm2),
                                  "right" : (rm1, rm2)}
        self.img = None
        self.running = True

    def poll(self):
        try:
            self.frame_mutex.acquire()
            valid = self.frame_data["timestamp_ms"] is not None
            self.frame_mutex.release()
        except Exception as e:
            logging.error(e)
            return

        # If frames are ready to process
        if valid:
            # Hold the mutex only long enough to copy the stereo frames
            self.frame_mutex.acquire()
            frame_copy = {"left"  : self.frame_data["left"].copy(),
                          "right" : self.frame_data["right"].copy()}
            self.frame_mutex.release()

            # Undistort and crop the center of the frames
            center_undistorted = {"left" : cv2.remap(src = frame_copy["left"],
                                          map1 = self.undistort_rectify["left"][0],
                                          map2 = self.undistort_rectify["left"][1],
                                          interpolation = cv2.INTER_LINEAR),
                                  "right" : cv2.remap(src = frame_copy["right"],
                                          map1 = self.undistort_rectify["right"][0],
                                          map2 = self.undistort_rectify["right"][1],
                                          interpolation = cv2.INTER_LINEAR)}
            # compute the disparity on the center of the frames and convert it to a pixel disparity (divide by DISP_SCALE=16)
            disparity = self.stereo.compute(center_undistorted["left"], center_undistorted["right"]).astype(np.float32) / 16.0
            # re-crop just the valid part of the disparity
            disparity = disparity[:,self.max_disp:]
            # scale disparity to 0-255
            disp_vis = 255*(disparity - self.min_disp)/ self.num_disp

            img_l = center_undistorted["left"][:,self.max_disp:]
            img_r = center_undistorted["right"][:,self.max_disp:]

            if img_l is not None and img_r is not None:
                width, height = img_l.shape
                grey_a = img_l[self.crop_height:height,0:width]
                grey_b = img_r[self.crop_height:height,0:width]
                grey_c = disp_vis[self.crop_height:height,0:width]
                
                stereo_image = np.zeros([height - self.crop_height, width, 3], dtype=np.dtype('B'))
                stereo_image[...,0] = np.reshape(grey_a, (height - self.crop_height, width))
                stereo_image[...,1] = np.reshape(grey_b, (height - self.crop_height, width))
                stereo_image[...,2] = np.reshape(grey_c, (height - self.crop_height, width))

                self.img = np.array(stereo_image)


    def update(self):
        while self.running:
            self.poll()

    def run_threaded(self):
        return self.img

    def run(self):
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.pipe.stop()

class RS_T265_StereoRectified_Pose(object):
    '''
    Use t265 stereo cameras as a single 3-ch camera stream: left, right, disparity 
    The left and right images are first stereo-rectified and aligned to the left projection center,
    then, disparity is computed and put into the 3rd channel.
    image_w and image_h defines an ROI cropping region with field of view fov in degrees
    '''

    def __init__(self, image_w=240, image_h=140, fov=120):
        # T265 image is almost square: 848 x 800. image_h defines px count from the bottom (ground)
        # here we use image_w to determine crop height start px count from the top
        # crop_height will be used to crop the image for ROI selections

        self.trans = None
        self.rot = {'roll': 0, 'pitch': 0, 'yaw': 0}
        self.crop_height = image_w - image_h

        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.fisheye, 1) # Left camera
        cfg.enable_stream(rs.stream.fisheye, 2) # Right camera
        cfg.enable_stream(rs.stream.pose)

        # Set up a mutex to share data between threads 
        from threading import Lock
        self.frame_mutex = Lock()
        self.pose = None

        # Start streaming with our callback
        self.pipe.start(cfg)
        time.sleep(0.5)

        profiles = self.pipe.get_active_profile()
        streams = {"left"  : profiles.get_stream(rs.stream.fisheye, 1).as_video_stream_profile(),
               "right" : profiles.get_stream(rs.stream.fisheye, 2).as_video_stream_profile()}
        intrinsics = {"left"  : streams["left"].get_intrinsics(),
                  "right" : streams["right"].get_intrinsics()}
        
        # Print information about both cameras
        print(">>>Cal::Intrinsics::Left camera:",  intrinsics["left"])
        print(">>>Cal::Intrinsics::Right camera:", intrinsics["right"])

        (R, T) = get_extrinsics(streams["left"], streams["right"])
        print(">>>Cal::relativeExtrinsics:", (R,T))

        window_size = 5
        self.min_disp = 0
        self.num_disp = 112 - self.min_disp # 112 is a magic number from RS examples...
        self.max_disp = self.min_disp + self.num_disp
        self.stereo = cv2.StereoSGBM_create(minDisparity = self.min_disp,
                                   numDisparities = self.num_disp,
                                   blockSize = 16,
                                   P1 = 8*3*window_size**2,
                                   P2 = 32*3*window_size**2,
                                   disp12MaxDiff = 1,
                                   uniquenessRatio = 10,
                                   speckleWindowSize = 100,
                                   speckleRange = 32)
        
        # Translate the intrinsics from librealsense into OpenCV
        K_left  = camera_matrix(intrinsics["left"])
        D_left  = fisheye_distortion(intrinsics["left"])
        K_right = camera_matrix(intrinsics["right"])
        D_right = fisheye_distortion(intrinsics["right"])
       
        # We calculate the undistorted focal length:
        #
        #         h
        # -----------------
        #  \      |      /
        #    \    | f  /
        #     \   |   /
        #      \ fov /
        #        \|/

        print("initializing FoV: ",fov, " Width px: ", image_w)
        stereo_fov_rad = fov * (m.pi/180)  # fov degree desired fov
        stereo_height_px = image_w # use image_w to initialize height due to square image
        stereo_focal_px = stereo_height_px/2 / m.tan(stereo_fov_rad/2)

        # We set the left rotation to identity and the right rotation
        # the rotation between the cameras
        R_left = np.eye(3)
        R_right = R

        # The stereo algorithm needs max_disp extra pixels in order to produce valid
        # disparity on the desired output region. This changes the width, but the
        # center of projection should be on the center of the cropped image
        
        stereo_width_px = stereo_height_px + self.max_disp
        stereo_size = (stereo_width_px, stereo_height_px)
        stereo_cx = (stereo_height_px - 1)/2 + self.max_disp
        stereo_cy = (stereo_height_px - 1)/2

        # Construct the left and right projection matrices, the only difference is
        # that the right projection matrix should have a shift along the x axis of
        # baseline*focal_length
        P_left = np.array([[stereo_focal_px, 0, stereo_cx, 0],
                        [0, stereo_focal_px, stereo_cy, 0],
                        [0,               0,         1, 0]])
        P_right = P_left.copy()
        P_right[0][3] = T[0]*stereo_focal_px

        # Construct Q for use with cv2.reprojectImageTo3D. Subtract max_disp from x
        # since we will crop the disparity later
        Q = np.array([[1, 0,       0, -(stereo_cx - self.max_disp)],
                      [0, 1,       0, -stereo_cy],
                      [0, 0,       0, stereo_focal_px],
                      [0, 0, -1/T[0], 0]])

        # Create an undistortion map for the left and right camera which applies the
        # rectification and undoes the camera distortion.
        print("creating StereoRectify::UndistortionMap")
        m1type = cv2.CV_32FC1
        (lm1, lm2) = cv2.fisheye.initUndistortRectifyMap(K_left, D_left, R_left, P_left, stereo_size, m1type)
        (rm1, rm2) = cv2.fisheye.initUndistortRectifyMap(K_right, D_right, R_right, P_right, stereo_size, m1type)
        self.undistort_rectify = {"left"  : (lm1, lm2),
                                  "right" : (rm1, rm2)}
        self.img = None
        self.limg = None
        self.rimg = None
        self.running = True

    def poll(self):
        try:
            # Wait for the next set of frames from the camera
            frames = self.pipe.wait_for_frames()
            # Fetch pose frame
            if frames is not None:
                self.pose = frames.get_pose_frame().get_pose_data()
                self.limg = np.asanyarray(frames.get_fisheye_frame(1).get_data())
                self.rimg = np.asanyarray(frames.get_fisheye_frame(2).get_data())
        except Exception as e:
            logging.error(e)
            return

        # Undistort and crop the center of the frames
        center_undistorted = {"left" : cv2.remap(src = self.limg,
                                        map1 = self.undistort_rectify["left"][0],
                                        map2 = self.undistort_rectify["left"][1],
                                        interpolation = cv2.INTER_LINEAR),
                                "right" : cv2.remap(src = self.rimg,
                                        map1 = self.undistort_rectify["right"][0],
                                        map2 = self.undistort_rectify["right"][1],
                                        interpolation = cv2.INTER_LINEAR)}
        # compute the disparity on the center of the frames and convert it to a pixel disparity (divide by DISP_SCALE=16)
        disparity = self.stereo.compute(center_undistorted["left"], center_undistorted["right"]).astype(np.float32) / 16.0
        # re-crop just the valid part of the disparity
        disparity = disparity[:,self.max_disp:]
        # scale disparity to 0-255
        disp_vis = 255*(disparity - self.min_disp)/ self.num_disp

        img_l = center_undistorted["left"][:,self.max_disp:]
        img_r = center_undistorted["right"][:,self.max_disp:]

        if img_l is not None and img_r is not None:
            width, height = img_l.shape
            grey_a = img_l[self.crop_height:height,0:width]
            grey_b = img_r[self.crop_height:height,0:width]
            grey_c = disp_vis[self.crop_height:height,0:width]
            
            stereo_image = np.zeros([height - self.crop_height, width, 3], dtype=np.dtype('B'))
            stereo_image[...,0] = np.reshape(grey_a, (height - self.crop_height, width))
            stereo_image[...,1] = np.reshape(grey_b, (height - self.crop_height, width))
            stereo_image[...,2] = np.reshape(grey_c, (height - self.crop_height, width))

            self.img = np.array(stereo_image)
        
        self.trans = self.pose.translation
        print(self.trans)

        w = self.pose.rotation.w
        x = -self.pose.rotation.z
        y = self.pose.rotation.x
        z = -self.pose.rotation.y

        pitch =  -m.asin(2.0 * (x*z - w*y)) * 180.0 / m.pi
        roll  =  m.atan2(2.0 * (w*x + y*z), w*w - x*x - y*y + z*z) * 180.0 / m.pi
        yaw   =  m.atan2(2.0 * (w*z + x*y), w*w + x*x - y*y - z*z) * 180.0 / m.pi
        self.rot = {'roll': roll, 'pitch': pitch, 'yaw': yaw}


    def update(self):
        while self.running:
            self.poll()

    def run_threaded(self):
        return self.img, self.trans, self.rot['yaw']

    def run(self):
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.pipe.stop()

class RS_T265(object):
    '''
    The Intel Realsense T265 camera is a device which uses an imu, twin fisheye cameras,
    and an Movidius chip to do sensor fusion and emit a world space coordinate frame that 
    is remarkably consistent.
    '''

    def __init__(self, image_output=True, stereo_output=False, imu_output=False, motion_output=False, path_output=False):
        self.stereo = stereo_output
        self.image_output = image_output
        self.imu_output = imu_output
        self.motion_output = motion_output
        self.path_output = path_output
        if self.path_output:
            print("will publish path from t265")

        if self.motion_output:
            print("will publish motion from t265")
            self.stereo = False
            self.image_output = False
            self.imu_output = False

        self.pipe = rs.pipeline()
        cfg = rs.config()
        
        if self.imu_output or self.motion_output or self.path_output:
            cfg.enable_stream(rs.stream.pose)

        if self.image_output:
            #right now it's required for both streams to be enabled
            cfg.enable_stream(rs.stream.fisheye, 1) # Left camera
            cfg.enable_stream(rs.stream.fisheye, 2) # Right camera

        # Start streaming with requested config
        self.pipe.start(cfg)
        self.running = True
        
        zero_vec = (0.0, 0.0, 0.0)
        self.trans = zero_vec
        self.vel = zero_vec
        self.acc = zero_vec
        self.rot = {}
        self.limg = None
        self.rimg = None

    def poll(self):
        try:
            frames = self.pipe.wait_for_frames()
        except Exception as e:
            logging.error(e)
            return

        if self.imu_output or self.motion_output or self.path_output:
            data = frames.get_pose_frame().get_pose_data()
            self.trans = data.translation
            self.vel = data.velocity
            self.acc = data.acceleration
            w = data.rotation.w
            x = -data.rotation.z
            y = data.rotation.x
            z = -data.rotation.y

            pitch =  -m.asin(2.0 * (x*z - w*y)) * 180.0 / m.pi
            roll  =  m.atan2(2.0 * (w*x + y*z), w*w - x*x - y*y + z*z) * 180.0 / m.pi
            yaw   =  m.atan2(2.0 * (w*z + x*y), w*w + x*x - y*y - z*z) * 180.0 / m.pi
            self.rot = {'roll': roll, 'pitch': pitch, 'yaw': yaw}

        if self.image_output:
            self.limg = np.asanyarray(frames.get_fisheye_frame(1).get_data())
            if self.stereo:
                self.rimg = np.asanyarray(frames.get_fisheye_frame(2).get_data())

    def update(self):
        while self.running:
            self.poll()

    def run_threaded(self):
        if self.motion_output:
            return self.vel.x, self.vel.y, self.vel.z, self.acc.x, self.acc.y, self.acc.z, self.rot['roll'], self.rot['pitch'], self.rot['yaw']
        elif self.path_output:
            return self.trans, self.rot['yaw']

        if self.stereo:
            if self.imu_output:
                return self.limg, self.rimg, self.acc.x, self.acc.y, self.acc.z, self.rot['roll'], self.rot['pitch'], self.rot['yaw']
            elif self.image_output:
                return self.limg, self.rimg
        else:
            if self.imu_output:
                return self.limg, self.acc.x, self.acc.y, self.acc.z, self.rot['roll'], self.rot['pitch'], self.rot['yaw']
            else:
                return self.limg

    def run(self):
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.pipe.stop()


class RS_D435i(object):
    '''
    The Intel Realsense D435i camera is a RGBD camera with imu
    '''

    def __init__(self, image_w=424, image_h=240, frame_rate=15, img_type='color'):
        self.pipe = rs.pipeline()
        cfg = rs.config()
        self.img_type = img_type

        # please refer to README.md for available resolutions and frame rates
        self.init_img_w = 424
        self.init_img_h = 240
        self.crop_h = self.init_img_h - image_h

        if self.img_type == 'color':
            cfg.enable_stream(rs.stream.color, self.init_img_w, self.init_img_h, rs.format.rgb8, frame_rate)
        elif self.img_type == 'depth':
            cfg.enable_stream(rs.stream.depth, self.init_img_w, self.init_img_h, rs.format.z16, frame_rate)
        else:
            raise Exception("img_type >", img_type, "< not supported.")

        self.pipe.start(cfg)
        self.running = True
        
        self.img = None

    def poll(self):
        try:
            frames = self.pipe.wait_for_frames()
        except Exception as e:
            logging.error(e)
            return

        if self.img_type is 'color':
            data = np.asanyarray(frames.get_color_frame().get_data())
            self.img = data[self.crop_h:self.init_img_h,0:self.init_img_w]
        elif self.img_type is 'depth':
            data = np.asanyarray(frames.get_depth_frame().get_data())
            self.img = data[self.crop_h:self.init_img_h,0:self.init_img_w]
        else:
            raise Exception("img_type >", self.img_type, "< not supported.")

    def update(self):
        while self.running:
            self.poll()

    def run_threaded(self):
        return self.img

    def run(self):
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.pipe.stop()

if __name__ == "__main__":
    iter = 0
    cam = RS_T265_StereoRectified()
    WINDOW_TITLE = 'Realsense'
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    while True:
        img = cam.run()
        origin = img.copy()
        origin[:,:,1] = img[:,:,0]
        origin[:,:,2] = img[:,:,0]
        
        disparity = cv2.cvtColor(img[:,:,2], cv2.COLOR_GRAY2RGB)
        disparity = cv2.applyColorMap(cv2.convertScaleAbs(disparity,1), cv2.COLORMAP_JET)
        
        cv2.imshow(WINDOW_TITLE,np.hstack([origin, disparity]))
        key = cv2.waitKey(2)
