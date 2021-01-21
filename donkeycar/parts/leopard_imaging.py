import cv2
from donkeycar.parts.camera import BaseCamera
from donkeycar.parts.fast_stretch import fast_stretch
import time


class LICamera(BaseCamera):
    '''
    The Leopard Imaging Camera with Fast-Stretch built in.
    '''
    def __init__(self, width=224, height=224, capture_width=1280, capture_height=720, fps=60):
        super(LICamera, self).__init__()
        self.width = width
        self.height = height
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.fps = fps
        self.camera_id = LICamera.camera_id(self.capture_width, self.capture_height, self.width, self.height, self.fps)
        self.frame = None
        print('Connecting to Leopard Imaging Camera')
        self.capture = cv2.VideoCapture(self.camera_id)
        time.sleep(2)
        if self.capture.isOpened():
            print('Leopard Imaging Camera Connected.')
            self.on = True
        else:
            self.on = False
            print('Unable to connect. Are you sure you are using the right camera parameters ?')

    def read_frame(self):
        success, frame = self.capture.read()
        if success:
            # returns an RGB frame.
            frame = fast_stretch(frame)
            self.frame = frame

    def run(self):
        self.read_frame()
        return self.frame

    def update(self):
        # keep looping infinitely until the thread is stopped
        # if the thread indicator variable is set, stop the thread
        while self.on:
            self.read_frame()

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('Stopping Leopard Imaging Camera')
        self.capture.release()
        time.sleep(.5)

    @classmethod
    def camera_id(cls, capture_width, capture_height, width, height, fps):
        return 'nvarguscamerasrc ! video/x-raw(memory:NVMM), width=%d, height=%d, format=(string)NV12, framerate=(fraction)%d/1 ! nvvidconv ! video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! videoconvert ! appsink' % (
                capture_width, capture_height, fps, width, height)