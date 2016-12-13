import argparse
from time import sleep
import os 
import threading

import tornado

from whipclient import Whip
from utils import image as image_utils

import settings

from server import app


cam = settings.cam


BASE_URL = 'http://localhost:8000/'
IMG_DIR =  os.path.expanduser("~") + '/donkey_imgs/'

 
def setup():
    ''' Create necessary directories '''
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)
 
def drive():
    whip = Whip(BASE_URL)
 

def record():
    ''' record pictures on an interval '''
    file_num = 0

    while True:

        print('capturing picture' + str(file_num))
        print('angle: %s   speed: %s' %(settings.angle, settings.speed))
        file_name = 'donkey_' + str(file_num) + '.jpg'
        file_num += 1

        #get PIL image from PiCamera
        img = cam.capture()
        img = image_utils.binary_to_img(img)
        img.save(IMG_DIR + file_name, 'jpeg')
        sleep(.5)


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help', dest="subparser_name")

parser_drive = subparsers.add_parser('drive', help='drive help')
parser_record = subparsers.add_parser('record', help='record help')
parser_setup = subparsers.add_parser('setup', help='record help')

args = parser.parse_args()


def start_webserver():
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':

    t = threading.Thread(target=start_webserver)
    t.daemon = True #to close thread on Ctrl-c
    t.start()


    if 'subparser_name' in args:
        if args.subparser_name == 'drive':
            print('starting donkey in drive mode') 
            drive()
        elif args.subparser_name == 'record':
            print('starting donkey in record mode') 
            record()
        elif args.subparser_name == 'setup':
            print('setting up donkey') 
            setup()


