import os
import sys
import requests

print(sys.version)

image_dir = os.getcwd()

path = image_dir + '/donkey.jpg'

from io import BytesIO
from time import sleep
from picamera import PiCamera


camera = PiCamera()

# Create an in-memory stream

camera.start_preview(alpha=200)
# Camera warm-up time
sleep(2)
camera.stop_preview()

my_stream = BytesIO()
camera.capture(my_stream, 'jpeg')



def get_picture():
    pass
if __name__ == "__main__":
        pass
