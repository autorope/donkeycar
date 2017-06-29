"""
Cameras
"""


import time

import numpy as np


class BaseCamera:
    
    def run_threaded(self):
        return self.frame


class PiCamera(BaseCamera):
    def __init__(self, resolution=(160, 120), framerate=20):
        from picamera.array import PiRGBArray
        from picamera import PiCamera

        # initialize the camera and stream
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
            format="rgb", use_video_port=True)
 
        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.on = True
        
        print('PiCamera loaded.. .warming camera')
        time.sleep(2)

 
    def update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)
 
            # if the thread indicator variable is set, stop the thread
            if not self.on: 
                break


    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stoping PiCamera')
        time.sleep(.5)
        self.stream.close()
        self.rawCapture.close()
        self.camera.close()



class RPLidar():
    def __init__(self, port='/dev/ttyUSB0'):
        from rplidar import RPLidar
        self.port = port
        self.frame = np.zeros(shape=365)
        self.lidar = RPLidar(self.port)
        self.lidar.clear_input()
        time.sleep(1)
        self.on = True


    def update(self):
        self.measurements = self.lidar.iter_measurments(500)
        for new_scan, quality, angle, distance in self.measurements:
            angle = int(angle)
            self.frame[angle] = 2*distance/3 + self.frame[angle]/3
            if not self.on: 
                break
            


class SquareBoxCamera:
    """
    Fake camera that returns an image with a square box.
    
    This can be used to test if a learning algorithm can learn.
    """

    def __init__(self, resolution=(120,160), box_size=4, color=(255, 0, 0)):
        self.resolution = resolution
        self.box_size = box_size
        self.color = color
        
        
    def run(self, x,y, box_size=None, color=None):
        """
        Create an image of a square box at a given coordinates.
        """
        radius = int((box_size or self.box_size)/2)
        color = color or self.color      
        frame = np.zeros(shape=self.resolution + (3,))
        frame[y - radius: y + radius,
              x - radius: x + radius,  :] = color
        return frame




