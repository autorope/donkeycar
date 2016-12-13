
import io
import os
from PIL import Image

from utils import image as image_utils

FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'


class Camera():
    '''
    Wrapper around PiCamera to create common convienience menthods
    '''
    self.img #last image from the stream

    def __init__(self):
        print('Loading PiCamera... ', end='')

        from picamera import PiCamera
        self.cam = PiCamera()
        #let camera warm up. 
        time.sleep(1)
        self.cam.resolution = (640, 480)
        print('success')

        print('starting camera stream')
        self.start_stream()


    def start_stream(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()

    def update(self):
        
        stream = io.BytesIO()
        for foo in self.cam.capture_continuous(stream, format='jpeg'):
            # Truncate the stream to the current position (in case
            # prior iterations output a longer image)
            stream.truncate()
            stream.seek(0)
            self.img = Image.open(stream)


    def capture_img(self):
        img = self.img
        return normalize(img)


    def capture_binary(self):
        img = self.capture_img()
        return image_utils.img_to_binary(img)



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
