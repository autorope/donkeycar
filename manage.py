
import argparse
from time import sleep
import os 
from PIL import Image
import io

from whip import Whip
from utils import image as image_utils

from picamera import PiCamera
camera = PiCamera()


BASE_URL = 'http://localhost:8000/'
IMG_DIR =  os.path.expanduser("~") + '/donkey_imgs/'


def setup():
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)

def drive():
    whip = Whip(BASE_URL)


def record():
    ''' record pictures on an interval '''

    file_num = 0

    while True:

        sleep(3)
        print('capturing picture' + str(file_num))
        file_name = 'donkey_' + str(file_num) + '.jpg'
        file_num += 1

        # Create the in-memory stream
        stream = io.BytesIO()

        camera =  picamera.PiCamera()
        camera.resolution = (640, 480)
        camera.capture(stream, format='jpeg', resize=(320, 240))

        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)
        img = Image.open(stream)
        img = image_utils.square(img)
        img = image_utils.scale(img, 128)

        img.save(file_name, 'jpeg')





parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help', dest="subparser_name")

parser_drive = subparsers.add_parser('drive', help='drive help')
parser_record = subparsers.add_parser('record', help='record help')
parser_setup = subparsers.add_parser('setup', help='record help')

args = parser.parse_args()


if __name__ == '__main__':
    if 'subparser_name' in args:
        if args.subparser_name == 'drive':
            print('starting donkey in drive mode') 
            drive()
        elif args.subparser_name == 'record':
            print('starting donkey in drive mode') 
            record()
        elif args.subparser_name == 'setup':
            print('starting donkey in drive mode') 
            setup()
