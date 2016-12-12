
import os
from PIL import Image
import io

FAKE_CAMERA_IMG_DIR = os.path.dirname(os.path.realpath(__file__))+'/img/'



class Camera():
    def __init__(self):
        print('Loading PiCamera')
        from picamera import PiCamera
        self.cam = PiCamera()

    def capture(self, capture_resolution = (640, 480), square_size = 128):
        # Create the in-memory stream
        stream = io.BytesIO()


        self.cam.resolution = capture_resolution
        self.cam.capture(stream, format='jpeg')

        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)
        img = Image.open(stream)
        img = image_utils.square(img)
        img = image_utils.scale(img, square_size)
        return img


class FakeCamera():
    ''' 
    Class that acts like a PiCamera but reads files from a dir.
    Used for testing on non-Pi devices.
    '''
    def __init__(self):
        print('loading FakeCamera')
        self.file_list = file_list = os.listdir(FAKE_CAMERA_IMG_DIR)
        self.counter = 0

    def capture(self):

        #print('capturing file: %s' % self.file_list[self.counter])

        img = Image.open("img/" + self.file_list[self.counter])
        stream = io.BytesIO()
        img.save(stream, format="JPEG")

        self.counter = (self.counter + 1) % len(self.file_list)
        return  stream.getvalue()