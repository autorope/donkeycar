"""Records training data and / or drives the car with tensorflow.
Usage:
    manage.py drive [--session=<name>] [--model=<name>]
    manage.py train [--session=<name>] [--model=<name>]
    manage.py serve [--model=<name>]

Options:
  --model=<name>     model name for predictor to use 
  --session=<name>   recording session name
"""

import settings
from globalvars import GLB

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



def drive_loop():
    ''' 
    The main driving loop controls the car.
    The GLB global variable is used to access objects with threaded processes. 
    '''
    start_time = time.time()

    while True:
        now = time.time()
        milliseconds = int( (now - start_time) * 1000)

        #get PIL image from camera
        img = GLB.camera.capture_img()

        arr = image_utils.img_to_greyarr(img)

        p_angle, p_speed = GLB.predictor.predict(arr)

        print('A/P: >(%s, %s)  speed(%s/%s)' %(GLB.controller.angle, 
                                p_angle, 
                                GLB.controller.speed,
                                p_speed))


        #update vehicle with given velocity vars (not working)
        GLB.vehicle.update(GLB.controller.angle, 
                            GLB.controller.speed)

        #record image and velocity vars
        GLB.recorder.record(img, 
                            GLB.controller.angle,
                            GLB.controller.speed, 
                            milliseconds)

        time.sleep(settings.DRIVE_LOOP_DELAY)



def train(recorder, predictor):
    x, y = recorder.get_arrays()
    predictor.fit(x, y)
    predictor.save()



if __name__ == '__main__':

    session = args['--session'] or None
    model = args['--model'] or None

    print('session name: %s,  model name: %s ' %(session, model))


    if args['drive']:

        GLB.camera = settings.camera()
        GLB.controller = settings.controller()
        GLB.vehicle = settings.vehicle()
        
        GLB.recorder = settings.recorder(session)
        #GLB.recorder.create(session)

        if model is not None:
            print('Loading predictor model: %s' %model)
            GLB.predictor = settings.predictor()
            GLB.predictor.load(model)
        else:
            print('No model given. Auto mode will not work.')
            GLB.predictor = settings.predictor()
        drive_loop()


    elif args['train']:
        #Read in pictures and velocities and create a predictor
        recorder = settings.recorder(session)
        predictor = settings.predictor()
        predictor.create(model)
        train(recorder, predictor)



