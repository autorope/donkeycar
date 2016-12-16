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
        CAR = Car(session, model, remote_url)
        CAR.drive_loop()


    elif args['train']:
        #Read in pictures and velocities and create a predictor
        recorder = settings.recorder(session)
        predictor = settings.predictor()
        predictor.create(model)
        train(recorder, predictor)



