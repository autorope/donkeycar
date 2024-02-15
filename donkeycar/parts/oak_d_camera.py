import logging
import time
from collections import deque
import numpy as np
import depthai as dai
import cv2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CameraError(Exception):
    pass

class OakDCameraBuilder:
    def __init__(self):
        self.width = None
        self.height = None
        self.depth = 3
        self.isp_scale = None
        self.framerate = 30
        self.enable_depth = True #TODO
        self.enable_obstacle_dist = False
        self.rgb_resolution = "1080p"
        self.rgb_apply_cropping = False
        self.rgb_sensor_crop_x = 0.0
        self.rgb_sensor_crop_y = 0.125
        self.rgb_video_size = (1280,600)
        self.rgb_apply_manual_conf = False
        self.rgb_exposure_time = 2000
        self.rgb_sensor_iso = 1200
        self.rgb_wb_manual = 2800
        self.center_image_return = False
        self.five_channel_image_return = True
        self.depth_image_return = False

    def with_width(self, width):
        self.width = width
        return self

    def with_height(self, height):
        self.height = height
        return self

    def with_depth(self, depth):
        self.depth = depth
        return self

    def with_isp_scale(self, isp_scale):
        self.isp_scale = isp_scale
        return self

    def with_framerate(self, framerate):
        self.framerate = framerate
        return self

    def with_enable_depth(self, enable_depth):
        self.enable_depth = enable_depth
        return self

    def with_enable_obstacle_dist(self, enable_obstacle_dist):
        self.enable_obstacle_dist = enable_obstacle_dist
        return self

    def with_rgb_resolution(self, rgb_resolution):
        self.rgb_resolution = rgb_resolution
        return self

    def with_rgb_apply_cropping(self, rgb_apply_cropping):
        self.rgb_apply_cropping = rgb_apply_cropping
        return self

    def with_rgb_sensor_crop_x(self, rgb_sensor_crop_x):
        self.rgb_sensor_crop_x = rgb_sensor_crop_x
        return self

    def with_rgb_sensor_crop_y(self, rgb_sensor_crop_y):
        self.rgb_sensor_crop_y = rgb_sensor_crop_y
        return self

    def with_rgb_video_size(self, rgb_video_size):
        self.rgb_video_size = rgb_video_size
        return self

    def with_rgb_apply_manual_conf(self, rgb_apply_manual_conf):
        self.rgb_apply_manual_conf = rgb_apply_manual_conf
        return self

    def with_rgb_exposure_time(self, rgb_exposure_time):
        self.rgb_exposure_time = rgb_exposure_time
        return self

    def with_rgb_sensor_iso(self, rgb_sensor_iso):
        self.rgb_sensor_iso = rgb_sensor_iso
        return self

    def with_rgb_wb_manual(self, rgb_wb_manual):
        self.rgb_wb_manual = rgb_wb_manual
        return self
    
    def with_center_image_return(self, center_image_return):
        self.center_image_return = center_image_return
        return self
    
    def with_five_channel_image_return(self, five_channel_image_return):
        self.five_channel_image_return = five_channel_image_return
        return self
    
    def with_depth_image_return(self, depth_image_return):
        self.depth_image_return = depth_image_return
        return self

    def build(self):
        return OakDCamera(
            width=self.width, 
            height=self.height, 
            depth=self.depth, 
            isp_scale=self.isp_scale, 
            framerate=self.framerate, 
            enable_depth=self.enable_depth, 
            enable_obstacle_dist=self.enable_obstacle_dist, 
            rgb_resolution=self.rgb_resolution,
            rgb_apply_cropping=self.rgb_apply_cropping,
            rgb_sensor_crop_x=self.rgb_sensor_crop_x,
            rgb_sensor_crop_y=self.rgb_sensor_crop_y,
            rgb_video_size=self.rgb_video_size,
            rgb_apply_manual_conf=self.rgb_apply_manual_conf,
            rgb_exposure_time=self.rgb_exposure_time,
            rgb_sensor_iso=self.rgb_sensor_iso,
            rgb_wb_manual=self.rgb_wb_manual,
            center_image_return=self.center_image_return,
            five_channel_image_return = self.five_channel_image_return,
            depth_image_return=self.depth_image_return
        )

class OakDCamera:
    def __init__(self, 
                 width, 
                 height, 
                 depth=3, 
                 isp_scale=None, 
                 framerate=30, 
                 enable_depth=False, 
                 enable_obstacle_dist=False, 
                 rgb_resolution="1080p",
                 rgb_apply_cropping=False,
                 rgb_sensor_crop_x=0.0,
                 rgb_sensor_crop_y=0.125,
                 rgb_video_size=(1280,600),
                 rgb_apply_manual_conf=False,
                 rgb_exposure_time = 2000,
                 rgb_sensor_iso = 1200,
                 rgb_wb_manual= 2800,
                 center_image_return = False,
                 five_channel_image_return = True,
                 depth_image_return = False):

        
        self.on = False
        
        self.device = None
        self.frame_left = None
        self.frame_right = None

        self.center_image_return = center_image_return
        self.five_channel_return = five_channel_image_return
        self.depth_image_return = depth_image_return

        self.rgb_resolution = rgb_resolution
        
        self.queue_xout = None
        self.queue_xout_depth = None
        self.queue_xout_spatial_data = None
        self.roi_distances = []

        self.frame_xout = None
        self.frame_xout_depth = None
        
        # depth config
        # Closer-in minimum depth, disparity range is doubled (from 95 to 190):
        self.extended_disparity = True
        # Better accuracy for longer distance, fractional disparity 32-levels:
        self.subpixel = False
        # Better handling for occlusions:
        self.lr_check = True

        self.latencies = deque([], maxlen=20)
        self.enable_depth = enable_depth
        self.enable_obstacle_dist = enable_obstacle_dist

        # Create pipeline
        self.pipeline = dai.Pipeline()
        # self.pipeline.setCameraTuningBlobPath('/tuning_color_ov9782_wide_fov.bin')
        self.pipeline.setXLinkChunkSize(0) # This might improve reducing the latency on some systems

        if self.enable_depth:
            self.create_depth_pipeline()

        if self.enable_obstacle_dist:
            self.create_obstacle_dist_pipeline()

        # Define output
        xout = self.pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("xout")

        # Define a source and Link
        if depth == 3:
            # Source
            camera = self.pipeline.create(dai.node.ColorCamera)
            if self.rgb_resolution == "800p":
                camera.setResolution(dai.ColorCameraProperties.SensorResolution.THE_800_P)
            elif self.rgb_resolution == "1080p":
                camera.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
            else:
                camera.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
            camera.setInterleaved(False)
            camera.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)

            if isp_scale:
                # see https://docs.google.com/spreadsheets/d/153yTstShkJqsPbkPOQjsVRmM8ZO3A6sCqm7uayGF-EE/edit#gid=0
                camera.setIspScale(isp_scale) # "scale" sensor size, (9,19) = 910x512 ; seems very slightly faster
            
            if rgb_apply_cropping:
                camera.setSensorCrop(rgb_sensor_crop_x, rgb_sensor_crop_y) # When croping to keep only smaller video

                camera.setVideoSize(rgb_video_size) # Desired video size = ispscale result or smaller if croping


            # Resize image
            camera.setPreviewKeepAspectRatio(False)
            camera.setPreviewSize(width, height) # wich means cropping if aspect ratio kept
            
            camera.setIspNumFramesPool(1)
            camera.setVideoNumFramesPool(1)
            camera.setPreviewNumFramesPool(1)

            if rgb_apply_manual_conf:
                camera.initialControl.setManualExposure(rgb_exposure_time, rgb_sensor_iso)
                camera.initialControl.setManualWhiteBalance(rgb_wb_manual)
            
                # camRgb.initialControl.setSharpness(0) 
                # camRgb.initialControl.setLumaDenoise(0)
                # camRgb.initialControl.setChromaDenoise(4)
            else:

                camera.initialControl.SceneMode(dai.CameraControl.SceneMode.SPORTS)
                camera.initialControl.setAutoWhiteBalanceMode(dai.CameraControl.AutoWhiteBalanceMode.AUTO)
    
            # Link
            camera.preview.link(xout.input)

        elif depth == 1:
            # Source
            camera = self.pipeline.create(dai.node.MonoCamera)
            camera.setBoardSocket(dai.CameraBoardSocket.LEFT)
            camera.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

            # Resize image
            manip = self.pipeline.create(dai.node.ImageManip)
            manip.setMaxOutputFrameSize(width * height)
            manip.initialConfig.setResize(width, height)
            manip.initialConfig.setFrameType(dai.RawImgFrame.Type.GRAY8)

            # Link
            camera.out.link(manip.inputImage)
            manip.out.link(xout.input)

        else:
            raise ValueError("'depth' parameter must be either '3' (RGB) or '1' (GRAY)")

        # Common settings
        camera.initialControl.setManualFocus(0) # from calibration data
        camera.initialControl.setAutoWhiteBalanceMode(dai.CameraControl.AutoWhiteBalanceMode.FLUORESCENT) # CLOUDY_DAYLIGHT FLUORESCENT
        camera.setFps(framerate)

        try:

            # Connect to device and start pipeline
            logger.info('Starting OAK-D camera')
            self.device = dai.Device(self.pipeline)
            #self.left_device = dai.Device(self.) #TODO

            warming_time = time.time() + 5  # seconds
                
            if enable_depth:
                self.queue_xout = self.device.getOutputQueue("xout", maxSize=1, blocking=False)
                self.queue_xout_depth = self.device.getOutputQueue("xout_depth", maxSize=1, blocking=False)
                # At the end of the __init__ method, create queues for left and right camera frames
                if self.center_image_return == False:
                    self.queue_left = self.device.getOutputQueue(name="left", maxSize=1, blocking=False)
                    self.queue_right = self.device.getOutputQueue(name="right", maxSize=1, blocking=False)

                # Get the first frame or timeout
                while (self.frame_xout is None or self.frame_xout_depth is None) and time.time() < warming_time:
                    logger.info("...warming RGB and depth cameras")
                    self.run()
                    time.sleep(0.2)

                if self.frame_xout is None:
                    raise CameraError("Unable to start OAK-D RGB and Depth camera.")

            elif enable_obstacle_dist:
                self.queue_xout = self.device.getOutputQueue("xout", maxSize=1, blocking=False)
                self.queue_xout_spatial_data = self.device.getOutputQueue("spatialData", maxSize=1, blocking=False)
            
            else:
                self.queue_xout = self.device.getOutputQueue("xout", maxSize=1, blocking=False)
                self.queue_xout_depth = None

                # Get the first frame or timeout
                while self.frame_xout is None and time.time() < warming_time:
                    logger.info("...warming camera")
                    self.run()
                    time.sleep(0.2)

                if self.frame_xout is None:
                    raise CameraError("Unable to start OAK-D camera.")

            self.on = True
            logger.info("OAK-D camera ready.")
            
        except:
            self.shutdown()
            raise

    def create_depth_pipeline(self):
        
        # Create depth nodes
        monoRight = self.pipeline.create(dai.node.MonoCamera)
        monoLeft = self.pipeline.create(dai.node.MonoCamera)

        if self.center_image_return == False:
            # Create XLinkOut nodes for left and right cameras
            xout_left = self.pipeline.create(dai.node.XLinkOut)
            xout_right = self.pipeline.create(dai.node.XLinkOut)

            # Set stream names
            xout_left.setStreamName("left")
            xout_right.setStreamName("right")

            # Link MonoCamera outputs to XLinkOut inputs
            monoLeft.out.link(xout_left.input)
            monoRight.out.link(xout_right.input)

        stereo_manip = self.pipeline.create(dai.node.ImageManip)
        stereo = self.pipeline.create(dai.node.StereoDepth)

        # Better handling for occlusions:
        stereo.setLeftRightCheck(True)
        # Closer-in minimum depth, disparity range is doubled:
        stereo.setExtendedDisparity(True)
        # Better accuracy for longer distance, fractional disparity 32-levels:
        stereo.setSubpixel(False)
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        stereo.initialConfig.setConfidenceThreshold(200)

        xout_depth = self.pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName("xout_depth")

        # Crop range
        topLeft = dai.Point2f(0.1875, 0.0)
        bottomRight = dai.Point2f(0.8125, 0.25)
        #    - - > x 
        #    |
        #    y
        
        # Properties
        monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

        stereo_manip.initialConfig.setCropRect(topLeft.x, topLeft.y, bottomRight.x, bottomRight.y)
        # manip.setMaxOutputFrameSize(monoRight.getResolutionHeight()*monoRight.getResolutionWidth()*3)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)

        # Linking
        # configIn.out.link(manip.inputConfig)
        monoRight.out.link(stereo.right)
        monoLeft.out.link(stereo.left)
        stereo.depth.link(stereo_manip.inputImage)
        stereo_manip.out.link(xout_depth.input)

    def create_obstacle_dist_pipeline(self):

        # Define sources and outputs
        monoLeft = self.pipeline.create(dai.node.MonoCamera)
        monoRight = self.pipeline.create(dai.node.MonoCamera)
        stereo = self.pipeline.create(dai.node.StereoDepth)
        spatialLocationCalculator = self.pipeline.create(dai.node.SpatialLocationCalculator)

        # xoutDepth = self.pipeline.create(dai.node.XLinkOut)
        xoutSpatialData = self.pipeline.create(dai.node.XLinkOut)
        xinSpatialCalcConfig = self.pipeline.create(dai.node.XLinkIn)

        # xoutDepth.setStreamName("depth")
        xoutSpatialData.setStreamName("spatialData")
        xinSpatialCalcConfig.setStreamName("spatialCalcConfig")

        # Properties
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)

        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        stereo.setLeftRightCheck(True)
        stereo.setExtendedDisparity(True)
        spatialLocationCalculator.inputConfig.setWaitForMessage(False)

        for i in range(4):
            config = dai.SpatialLocationCalculatorConfigData()
            config.depthThresholds.lowerThreshold = 200
            config.depthThresholds.upperThreshold = 10000
            # 30 - 40 est le mieux
            config.roi = dai.Rect(dai.Point2f(i*0.1+0.3, 0.35), dai.Point2f((i+1)*0.1+0.3, 0.43))
            spatialLocationCalculator.initialConfig.addROI(config)
            # 4 zones
            # PCLL PCCL PCCR PCRR
            # -.75 -.75 +.75 +.75
            
        # Linking
        monoLeft.out.link(stereo.left)
        monoRight.out.link(stereo.right)

        # spatialLocationCalculator.passthroughDepth.link(xoutDepth.input)
        stereo.depth.link(spatialLocationCalculator.inputDepth)

        spatialLocationCalculator.out.link(xoutSpatialData.input)
        xinSpatialCalcConfig.out.link(spatialLocationCalculator.inputConfig)

    def enhance_center_with_grayscale(self, center_img, left_img, right_img):
        # Check if the images are loaded correctly
        print(left_img, right_img, "ahhh")
        if left_img is None or right_img is None or center_img is None:
            raise ValueError("One or more input images are None. Please check image loading.")

        # Adjust for channel-first format if necessary
        if center_img.shape[0] == 3:
            center_img = np.transpose(center_img, (1, 2, 0))
        
        if left_img is not None and left_img.shape[0] == 3:
            left_img = np.transpose(left_img, (1, 2, 0))
        
        if right_img is not None and right_img.shape[0] == 3:
            right_img = np.transpose(right_img, (1, 2, 0))

        # Ensure resizing happens regardless of channel condition
        if left_img is not None:
            left_resized = cv2.resize(left_img, (800, 600))
        else:
            raise ValueError("left_img is None after format adjustment.")
        
        if right_img is not None:
            right_resized = cv2.resize(right_img, (800, 600))
        else:
            raise ValueError("right_img is None after format adjustment.")

        # Continue with processing...
        left_resized_3ch = np.stack((left_resized,)*3, axis=-1)
        right_resized_3ch = np.stack((right_resized,)*3, axis=-1)
        avg_grayscale = np.mean(np.array([left_resized_3ch, right_resized_3ch]), axis=0)
        avg_grayscale_single_channel = cv2.cvtColor(avg_grayscale.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        center_YCrCb = cv2.cvtColor(center_img, cv2.COLOR_RGB2YCrCb)
        center_YCrCb[:, :, 0] = cv2.addWeighted(center_YCrCb[:, :, 0], 0.5, avg_grayscale_single_channel, 0.5, 0)
        enhanced_center_img = cv2.cvtColor(center_YCrCb, cv2.COLOR_YCrCb2RGB)

        return enhanced_center_img

    def run(self):

        depth_frame = None
        # Grab the frame from the stream 
        if self.queue_xout is not None:
            data_xout = self.queue_xout.get() # blocking
            image_data_xout = data_xout.getFrame()
            self.frame_xout = np.moveaxis(image_data_xout,0,-1)
            # Retrieve the left camera frame
            if self.queue_left.has():
                data_left = self.queue_left.get()
                self.frame_left = data_left.getCvFrame()
                # self.frame_left = np.moveaxis(image_data_xout_left,0,-1)

            # Retrieve the right camera frame
            if self.queue_right.has():
                data_right = self.queue_right.get()
                self.frame_right = data_right.getCvFrame()
                # self.frame_right = np.moveaxis(self.frame_right,0,-1)

            if logger.isEnabledFor(logging.DEBUG):
                # Latency in miliseconds 
                self.latencies.append((dai.Clock.now() - data_xout.getTimestamp()).total_seconds() * 1000)
                if len(self.latencies) >= self.latencies.maxlen:
                    logger.debug('Image latency: {:.2f} ms, Average latency: {:.2f} ms, Std: {:.2f}' \
                        .format(self.latencies[-1], np.average(self.latencies), np.std(self.latencies)))
                    self.latencies.clear()

        if self.queue_xout_depth is not None:
            data_xout_depth = self.queue_xout_depth.tryGet()
            if data_xout_depth is not None:
                depth_frame = data_xout_depth.getFrame()
                self.frame_xout_depth = depth_frame

        if self.queue_xout_spatial_data is not None:
            print("bhhhhh")
            xout_spatial_data = self.queue_xout_spatial_data.get().getSpatialLocations()
            self.roi_distances = []
            for depthData in xout_spatial_data:
                roi = depthData.config.roi
                
                # xmin = int(roi.topLeft().x)
                # ymin = int(roi.topLeft().y)
                # xmax = int(roi.bottomRight().x)
                # ymax = int(roi.bottomRight().y)

                coords = depthData.spatialCoordinates
                
                self.roi_distances.append(round(roi.topLeft().x,2)) 
                self.roi_distances.append(round(roi.topLeft().y,2))
                self.roi_distances.append(round(roi.bottomRight().x,2))
                self.roi_distances.append(round(roi.bottomRight().y,2))
                self.roi_distances.append(int(coords.x))
                self.roi_distances.append(int(coords.y))
                self.roi_distances.append(int(coords.z))
            
        print(image_data_xout.shape, "alll")
        if self.center_image_return:
            return self.frame_xout
        elif self.depth_image_return:
            return depth_frame # Pixel map of distances (in millimeters)
        elif self.five_channel_return and self.frame_left is not None and self.frame_right is not None:
            return self.enhance_center_with_grayscale(image_data_xout, self.frame_left, self.frame_right)
        else:
            return None

    def run_threaded(self):
        if self.enable_depth:
            return self.frame_xout,self.frame_xout_depth
        elif self.enable_obstacle_dist:
            return self.frame_xout, np.array(self.roi_distances)
        else:
            return self.frame_xout

    def update(self):
        # Keep looping infinitely until the thread is stopped
        while self.on:
            self.run()

    def shutdown(self):
        # Indicate that the thread should be stopped
        self.on = False
        logger.info('Stopping OAK-D camera')
        time.sleep(.5)
        if self.device is not None:
            self.device.close()
        self.device = None
        self.queue = None
        self.pipeline = None

if __name__ == "__main__":
    # Code to be executed when the script is run as the main module
    cam = OakDCameraBuilder().with_width(800).with_height(600).with_framerate(30).build()
    frame = cam.run()
    print(frame)
            