
import io
import os
import time
import threading

from PIL import Image

from utils import image as image_utils

FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'


class Camera():
    '''
    Wrapper around PiCamera to create common convienience menthods
    '''
    img=None #last image from the stream

    def __init__(self):
        
        
        print('Loading PiCamera... ', end='')
        from picamera import PiCamera
        self.cam = PiCamera()
        time.sleep(1) #let camera warm up. 
        self.cam.resolution = (640, 480)
        print('success')

        
    def capture_img(self):
        '''return PIL image from camera'''
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg')
        stream.seek(0)
        img = Image.open(stream)
        return normalize(img)


    def capture_binary(self):
        '''return binary stream of image for webserver'''
        img = self.capture_img()
        return image_utils.img_to_binary(img)


class ThreadedCamera(Camera):
    ''' 
    This is an attempt to solve the issue of many threads accessing 
    the same stream and getting corrupt streams before they are written completely.
    
    It curretnly does not work.

    '''
    
    def __init__(self):
        Camera.__init__(self)
        self.start_stream()
        self.stream = io.BytesIO()
        print('starting camera stream')

    def start_stream(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()

    def update(self):
        lock = threading.Lock()
        
        while True:
            with lock:
                self.cam.capture(self.stream, 'jpeg')
                self.stream.seek(0)

            time.sleep(.1)

    def capture_img(self):
        img = Image.open(self.stream)
        
        return normalize(img)



class FakeCamera():
    ''' 
    Class that acts like a PiCamera but reads files from a dir.
    Used for testing on non-Pi devices.
    '''
    def __init__(self):
        print('loading FakeCamera')
        self.file_list = file_list = os.listdir(FAKE_CAMERA_IMG_DIR)
        self.counter = 0

    def capture_img(self):

        #print('capturing file: %s' % self.file_list[self.counter])

        img = Image.open("img/" + self.file_list[self.counter])
        self.counter += 1
        return normalize(img)
        
    def capture_binary(self):

        img = self.capture_img()
        return image_utils.img_to_binary(img)




def normalize(img):
    '''
    The way I've chosen to normalize all images.

    Accepts and returns PIL image.
    '''
    img = image_utils.square(img)
    img = image_utils.scale(img, 128)
    return img
