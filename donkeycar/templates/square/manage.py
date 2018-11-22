# -*- coding: utf-8 -*-

"""
Web controller.

This example shows how a user use a web controller to controll
a square that move around the image frame.


Usage:
    manage.py (drive) [--model=<model>]
    manage.py (train) [--tub=<tub1,tub2,..tubn>] (--model=<model>)

"""

import os
from docopt import docopt
import donkeycar as dk

from donkeypart_tub import TubWriter
from donkeypart_moving_square_sim import ControllerSquareBoxCamera
from donkeypart_web_controller import LocalWebController
#from donkeypart_keras_behavioral_cloning import KerasLinear

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sq.log')
dk.log.setup(log_path)
logger = dk.log.get_logger(__name__)
logger.info('Loading manage.py')


def drive(cfg, model_path=None):

    V = dk.vehicle.Vehicle()
    V.mem.put(['user/angle', 'user/throttle'], (0, 0))

    # display square box given by cooridantes.
    cam = ControllerSquareBoxCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam,
          inputs=['user/angle', 'user/throttle'],
          outputs=['cam/image_array'])

    # display the image and read user values from a local web controller
    ctr = LocalWebController()
    V.add(ctr,
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle',
                   'user/mode', 'recording'],
          threaded=True)

    # add tub to save data
    inputs=['cam/image_array',
            'user/angle', 'user/throttle',
            'user/mode',
            'timestamp']
    types=['image_array',
           'float', 'float',
           'str',
           'str']

    # single tub
    tub = TubWriter(path=cfg.TUB_PATH, inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')

    # run the vehicle for 20 seconds
    V.start(rate_hz=20)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    if args['drive']:
        drive(cfg, args['--model'])

    elif args['train']:
        tub = args['--tub']
