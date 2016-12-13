"""Records training data and / or drives the car with tensorflow.
Usage:
    manage.py record
    manage.py autopilot


Options:
    -h --help    show this

"""


import argparse
from time import sleep
import os 
import threading

from docopt import docopt
import tornado

from whipclient import Whip
from utils import image as image_utils

import settings

from server import app


cam = settings.cam



# Get args.
args = docopt(__doc__)


# Check the mode: recording vs TF driving vs TF driving + recording.
if args['record']:
    we_are_autonomous = False
    we_are_recording = True
    print("\n------ Ready to record training data ------\n")
elif args['auto']:
    we_are_autonomous = True
    we_are_recording = True
    print("\n****** READY TO DRIVE BY NEURAL NET and record data ******\n")



 
def setup():
    ''' Create necessary directories '''
    if not os.path.exists(settings.IMG_DIR):
        os.makedirs(settings.IMG_DIR)
 
def drive():
    whip = Whip(settings.BASE_URL)
 

def main_loop():
    ''' record pictures on an interval '''
    file_num = 0

    while True:
        #get global values
        angle = settings.angle
        speed = settings.speed


        adjust_car(settings,angle, settings.speed)

        record_state(img, settings.angle, settings.speed)

        predict_velocity(img)

        file_name = "donkey_{:0>5}.jpg".format(file_num)
        

        print('capturing: ' + str(file_name))
        print('angle: %s   speed: %s' %(settings.angle, settings.speed))

        file_num += 1

        #get PIL image from PiCamera
        img = cam.capture()
        img = image_utils.binary_to_img(img)
        img.save(IMG_DIR + file_name, 'jpeg')
        sleep(.5)





def start_webserver():
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':

    #Start webserver http://localhost:8888
    #Used to view camera stream and control c ar. 
    t = threading.Thread(target=start_webserver)
    t.daemon = True #to close thread on Ctrl-c
    t.start()


