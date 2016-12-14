"""Records training data and / or drives the car with tensorflow.
Usage:
    manage.py record
    manage.py auto
    manage.py train [--indir=<path>] [--outdir=<path>]

Options:
  --indir=<path>   path to input npy files [default: ~/training-data]
  --outdir=<path>  [default: ~/training-results]

"""

import settings

import time
import os 
import threading

from docopt import docopt
import tornado

from whipclient import Whip
from utils import image as image_utils
from webserver import app


cam = settings.cam  #camera 
vehicle = settings.vehicle
recorder = settings.recorder
predictor = settings.predictor



# Get args.
args = docopt(__doc__)


# Check the mode: recording vs TF driving vs TF driving + recording.
if args['record']:
    we_are_autonomous = False
    we_are_recording = True
    print("\n------ Ready to record training data ------\n")


if args['auto']:
    we_are_autonomous = True
    we_are_recording = True
    print("\n****** READY TO DRIVE BY NEURAL NET and record data ******\n")




def drive_loop():
    ''' record pictures on an interval '''
    start_time = time.time()

    while True:
        now = time.time()
        milliseconds = int( (now - start_time) * 1000)

        #get global values manually controlled from the webserver
        angle = settings.angle_manual
        speed = settings.speed_manual

        print('angle: %s   speed: %s' %(angle, speed))

        #get PIL image from PiCamera
        img = cam.capture_img()

        if we_are_autonomous:
            #get predicted angles (not working)
            angle_predicted, speed_predicted = tf_driver.predict(img)

        if settings.car_connected:
            #update vehicle with given velocity vars (not working)
            angle_vehicle, speed_vehicle = vehicle.update(angle, speed)

        if we_are_recording:
            #record img and velocity vars
            recorder.record(img, angle, speed, milliseconds)

        time.sleep(settings.LOOP_DELAY)


def train(indir):
    if indir is not None:
        recorder.session_dir = indir
    else:
        recorder.use_last_session()

    recorder.create_array_files()


def start_webserver():
    app.listen(8889)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':

    
    if args['record'] or args['auto']:
        #Start the main driving loop.

        if settings.use_webserver == True:
            #Start webserver http://localhost:8888
            #Used to view camera stream and control c ar. 
            print('Starting webserver at <ip_address>:8888')
            t = threading.Thread(target=start_webserver)
            t.daemon = True #to close thread on Ctrl-c
            t.start()

        drive_loop()


    if args['train']:
        #Read in pictures and velocities and create a predictor
        if 'indir' in args: indir = args['indir']
        else: indir = None

        train(indir)



