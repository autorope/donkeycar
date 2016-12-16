"""Records training data and / or drives the car with tensorflow.
Usage:
    manage.py drive [--session=<name>] [--model=<name>] [--remote=<name>]
    manage.py train [--session=<name>] [--model=<name>]
    manage.py serve [--model=<name>]

Options:
  --model=<name>     model name for predictor to use 
  --session=<name>   recording session name
  --remote=<name>   recording session name
"""

import settings

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

class Car():
    def __init__(self):
        pass

CAR = Car()

def local_drive_loop():
    ''' 
    The main driving loop controls the car.
    The CAR global variable is used to access objects with threaded processes. 
    '''
    start_time = time.time()

    while True:
        now = time.time()
        milliseconds = int( (now - start_time) * 1000)

        #get PIL image from camera
        img = CAR.camera.capture_img()

        #read values from controller
        c_angle = CAR.controller.angle
        c_speed = CAR.controller.speed
        drive_mode = CAR.controller.drive_mode


        if remote_url is None:
            #record and predict locally
            CAR.recorder.record(img, 
                                c_angle,
                                c_speed, 
                                milliseconds)

            #send image and data to predictor to get estimates
            arr = image_utils.img_to_greyarr(img)
            p_angle, p_speed = CAR.predictor.predict(arr)

        else:
            p_angle, p_speed = CAR.remote_driver(remote_url,
                                                 img,
                                                 c_angle, 
                                                 c_speed,
                                                 milliseconds)






        if CAR.controller.drive_mode == 'manual':
            #update vehicle with given velocity vars (not working)
            CAR.vehicle.update(c_angle, c_speed)
        else:
            CAR.vehicle.update(p_angle, p_speed)



        #print current car state
        print('A/P: >(%s, %s)  speed(%s/%s)  drive_mode: %s' %(CAR.controller.angle, 
                                p_angle, 
                                CAR.controller.speed,
                                p_speed,
                                CAR.controller.drive_mode))

        time.sleep(settings.DRIVE_LOOP_DELAY)



def train(recorder, predictor):
    x, y = recorder.get_arrays()
    predictor.fit(x, y)
    predictor.save()



if __name__ == '__main__':

    session = args['--session'] or None
    model = args['--model'] or None
    remote_url = args['--remote'] or None

    print('session name: %s,  model name: %s ' %(session, model))


    if args['drive']:

        CAR.camera = settings.camera()
        CAR.controller = settings.controller()
        CAR.vehicle = settings.vehicle()
        
        CAR.recorder = settings.recorder(session)

        if model is not None:
            print('Loading predictor model: %s' %model)
            CAR.predictor = settings.predictor()
            CAR.predictor.load(model)
        else:
            print('No model given. Auto mode will not work.')
            CAR.predictor = settings.predictor()
        local_drive_loop()


    elif args['train']:
        #Read in pictures and velocities and create a predictor
        recorder = settings.recorder(session)
        predictor = settings.predictor()
        predictor.create(model)
        train(recorder, predictor)



