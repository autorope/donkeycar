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
    def __init__(self, width, height, depth=3, isp_scale=None, framerate=30):
        self.frame = None
        self.on = False
        self.device = None
        self.queue = None
        self.latencies = deque([], maxlen=20)

        # Create pipeline
        self.pipeline = dai.Pipeline()
        self.pipeline.setXLinkChunkSize(0) # This might improve reducing the latency on some systems

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
            self.queue = self.device.getOutputQueue(name="xout", maxSize=1, blocking=False)

            # Get the first frame or timeout
            warming_time = time.time() + 5  # seconds
            while self.frame is None and time.time() < warming_time:
                logger.info("...warming camera")
                self.run()
                time.sleep(0.2)

            if self.frame is None:
                raise CameraError("Unable to start OAK-D camera.")

            logger.info("OAK-D camera ready.")
            self.on = True
        except:
            self.shutdown()
            raise
        
    def run(self):
        # Grab the frame from the stream 
        if self.queue is not None:
            data = self.queue.get() # blocking
            image_data = data.getFrame()
            self.frame = np.moveaxis(image_data, 0, -1)

            if logger.isEnabledFor(logging.DEBUG):
                # Latency in miliseconds 
                self.latencies.append((dai.Clock.now() - data.getTimestamp()).total_seconds() * 1000)
                if len(self.latencies) >= self.latencies.maxlen:
                    logger.debug('Image latency: {:.2f} ms, Average latency: {:.2f} ms, Std: {:.2f}' \
                        .format(self.latencies[-1], np.average(self.latencies), np.std(self.latencies)))
                    self.latencies.clear()

        return self.frame

    def run_threaded(self):
        return self.frame

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
        