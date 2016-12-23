"""Records training data and / or drives the car with tensorflow.
Usage:
    manage.py drive [--session=<name>] [--model=<name>] [--remote=<name>] [--fake_camera=<path>]
    manage.py train [--session=<name>] [--model=<name>]
    manage.py serve [--model=<name>]

Options:
  --model=<name>     model name for predictor to use 
  --session=<name>   recording session name
  --remote=<name>   recording session name
  --fake_camera=<path>    path to pictures to use as the camera
"""

import settings
from car import Car

import time
import os 
import threading

from docopt import docopt
import tornado

from utils import image as image_utils
from utils import file as file_utils

# Get args.
args = docopt(__doc__)


#Make sure folder structure exists. 
folders = [settings.DATA_DIR, 
            settings.RECORDS_DIR, 
            settings.MODELS_DIR]

for f in folders:
    file_utils.make_dir(f)


if __name__ == '__main__':

    session = args['--session'] or None
    model = args['--model'] or None
    remote_url = args['--remote'] or None
    fake_camera_img_dir = args['--fake_camera'] or None

    print('session name: %s,  model name: %s ' %(session, model))


    if args['drive']:
        #Start your car
        CAR = Car(session = session, 
                  model = model, 
                  remote_url = remote_url, 
                  fake_camera_img_dir = fake_camera_img_dir)
        
        CAR.drive_loop()


    elif args['train']:
        #Read in pictures and velocities and create a predictor
        recorder = settings.recorder()
        recorder.load(session)
        
        predictor = settings.predictor()

        print('getting arrays')
        x, y = recorder.get_arrays()
        print('fitting model')
        predictor.fit(x, y)
        predictor.save()


    elif args['serve']:
        #set predictor and recorder for drive server to use
        predictor = settings.predictor()
        predictor.load(model)

        recorder = settings.recorder()
        recorder.load(session)
        
        #start webserver to act as the remote for a car.
        server = settings.drive_server(recorder, predictor)
        server.start()