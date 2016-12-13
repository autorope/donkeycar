
import io
import os
from PIL import Image

from utils import image as image_utils

FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'


class Camera():
    '''
    Wrapper around PiCamera to create common convienience menthods
    '''

    def __init__(self):
        print('Loading PiCamera... ', end='')

        from picamera import PiCamera
        self.cam = PiCamera()
        #let camera warm up. 
        time.sleep(1)
        print('success')

    def capture_img(self):
        # Create the in-memory stream
        stream = io.BytesIO()

        self.cam.resolution = (640, 480)
        self.cam.capture(stream, format='jpeg')

        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)
        img = Image.open(stream)

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