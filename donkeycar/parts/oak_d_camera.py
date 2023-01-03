import logging
import time
from collections import deque
import numpy as np
import depthai as dai

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CameraError(Exception):
    pass

class OakDCamera:
    def __init__(self, width, height, depth=3, isp_scale=None, framerate=30, enable_depth=False):
        
        self.on = False
        
        self.device = None
        
        self.queue_xout = None
        self.queue_xout_depth = None
        
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

        # Create pipeline
        self.pipeline = dai.Pipeline()
        self.pipeline.setXLinkChunkSize(0) # This might improve reducing the latency on some systems

        if self.enable_depth:
            self.create_depth_pipeline()

        # Define output
        xout = self.pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("xout")

        # Define a source and Link
        if depth == 3:
            # Source
            camera = self.pipeline.create(dai.node.ColorCamera)
            camera.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
            camera.setInterleaved(False)
            camera.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)

            # Resize image
            camera.setPreviewKeepAspectRatio(False)
            camera.setPreviewSize(width, height) # wich means cropping if aspect ratio kept
            if isp_scale:
                # see https://docs.google.com/spreadsheets/d/153yTstShkJqsPbkPOQjsVRmM8ZO3A6sCqm7uayGF-EE/edit#gid=0
                camera.setIspScale(isp_scale) # "scale" sensor size, (9,19) = 910x512 ; seems very slightly faster
            
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

            warming_time = time.time() + 5  # seconds
                
            if enable_depth:
                self.queue_xout = self.device.getOutputQueue("xout", maxSize=1, blocking=False)
                self.queue_xout_depth = self.device.getOutputQueue("xout_depth", maxSize=1, blocking=False)
            
                # Get the first frame or timeout
                while (self.frame_xout is None or self.frame_xout_depth is None) and time.time() < warming_time:
                    logger.info("...warming RGB and depth cameras")
                    self.run()
                    time.sleep(0.2)

                if self.frame_xout is None:
                    raise CameraError("Unable to start OAK-D RGB and Depth camera.")

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
        topLeft = dai.Point2f(0.1875, 0.05)
        bottomRight = dai.Point2f(0.8125, 0.3)

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

    def run(self):

        # Grab the frame from the stream 
        if self.queue_xout is not None:
            data_xout = self.queue_xout.get() # blocking
            image_data_xout = data_xout.getFrame()
            self.frame_xout = np.moveaxis(image_data_xout,0,-1)

            if logger.isEnabledFor(logging.DEBUG):
                # Latency in miliseconds 
                self.latencies.append((dai.Clock.now() - data_xout.getTimestamp()).total_seconds() * 1000)
                if len(self.latencies) >= self.latencies.maxlen:
                    logger.debug('Image latency: {:.2f} ms, Average latency: {:.2f} ms, Std: {:.2f}' \
                        .format(self.latencies[-1], np.average(self.latencies), np.std(self.latencies)))
                    self.latencies.clear()

        if self.queue_xout_depth is not None:
            data_xout_depth = self.queue_xout_depth.get()
            self.frame_xout_depth = data_xout_depth.getFrame()


        # return self.frame

    def run_threaded(self):
        if self.enable_depth:
            return self.frame_xout,self.frame_xout_depth
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
        