import logging
import cv2
import depthai as dai
from donkeycar.parts.camera import BaseCamera

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class OakDLiteCamera(BaseCamera):
    '''
    Camera for Oak-D-Lite based camera
    '''
    def __init__(self, image_w=160, image_h=120):
    
        self.w = image_w
        self.h = image_h
        self.framerate = framerate
        self.frame = None
        self.qRgb = None
        self.init_camera()
        self.running = True

    def init_camera(self):
        # Create pipeline
        pipeline = dai.Pipeline()

        # Define source and output
        camRgb = pipeline.create(dai.node.ColorCamera)
        xoutRgb = pipeline.create(dai.node.XLinkOut)

        xoutRgb.setStreamName("rgb")

        # Properties
        camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        camRgb.setInterleaved(False)
        camRgb.setFps(35)
        camRgb.setIspScale(1,8)
        camRgb.setPreviewSize(240, 135) # 1/8
        
        # Linking
        camRgb.preview.link(xoutRgb.input)

        # Connect to device and start pipeline
        with dai.Device(pipeline) as device:

            print('Connected cameras:', device.getConnectedCameras())
            # Print out usb speed
            print('Usb speed:', device.getUsbSpeed().name)
            # Bootloader version
            if device.getBootloaderVersion() is not None:
                print('Bootloader version:', device.getBootloaderVersion())
            # Device name
            print('Device name:', device.getDeviceName())

            # Output queue will be used to get the rgb frames from the output defined above
            self.qRgb = device.getOutputQueue(name="rgb", maxSize=1, blocking=False)


        logger.info("OakDLiteCamera ready.")

    def update(self):
        while self.running:
            self.poll_camera()

    def poll_camera(self):
        self.frame = self.qRgb.get()  # blocking call, will wait until a new data has arrived

    def run(self):
        self.poll_camera()
        return self.frame

    def run_threaded(self):
        return self.frame
    
    def shutdown(self):
        self.running = False
        logger.info('Stopping OakDLiteCamera')