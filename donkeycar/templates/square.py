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

from donkeycar.parts.datastore import TubGroup, TubWriter
from donkeycar.parts.transform import Lambda
from donkeycar.parts.simulation import SquareBoxCamera
from controller import LocalWebController
from donkeycar.parts.keras import KerasCategorical
from donkeycar.parts.clock import Timestamp

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sq.log')
dk.log.setup(log_path)
logger = dk.log.get_logger(__name__)
logger.info('Loading manage.py')


def drive(cfg, model_path=None):

    V = dk.vehicle.Vehicle()
    V.mem.put(['square/angle', 'square/throttle'], (100, 100))

    # display square box given by cooridantes.
    cam = SquareBoxCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam,
          inputs=['square/angle', 'square/throttle'],
          outputs=['cam/image_array'])

    # display the image and read user values from a local web controller
    ctr = LocalWebController()
    V.add(ctr,
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle',
                   'user/mode', 'recording'],
          threaded=True)

    # See if we should even run the pilot module.
    # This is only needed because the part run_contion only accepts boolean
    def pilot_condition(mode):
        if mode == 'user':
            return False
        else:
            return True

    pilot_condition_part = Lambda(pilot_condition)
    V.add(pilot_condition_part, inputs=['user/mode'], outputs=['run_pilot'])

    # Run the pilot if the mode is not user.
    kl = KerasCategorical()
    if model_path:
        kl.load(model_path)

    V.add(kl, inputs=['cam/image_array'],
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot')

    # See if we should even run the pilot module.
    def drive_mode(mode,
                   user_angle, user_throttle,
                   pilot_angle, pilot_throttle):
        if mode == 'user':
            return user_angle, user_throttle

        elif mode == 'pilot_angle':
            return pilot_angle, user_throttle

        else:
            return pilot_angle, pilot_throttle

    drive_mode_part = Lambda(drive_mode)
    V.add(drive_mode_part,
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'],
          outputs=['angle', 'throttle'])

    clock = Timestamp()
    V.add(clock, outputs=['timestamp'])

    # transform angle and throttle values to coordinate values
    def f(x):
        return int(x * 100 + 100)
    l = Lambda(f)
    V.add(l, inputs=['user/angle'], outputs=['square/angle'])
    V.add(l, inputs=['user/throttle'], outputs=['square/throttle'])

    # add tub to save data
    inputs=['cam/image_array',
            'user/angle', 'user/throttle',
            'pilot/angle', 'pilot/throttle',
            'square/angle', 'square/throttle',
            'user/mode',
            'timestamp']
    types=['image_array',
           'float', 'float',
           'float', 'float',
           'float', 'float',
           'str',
           'str']

    #multiple tubs
    #th = TubHandler(path=cfg.DATA_PATH)
    #tub = th.new_tub_writer(inputs=inputs, types=types)

    # single tub
    tub = TubWriter(path=cfg.TUB_PATH, inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')


    # run the vehicle for 20 seconds
    V.start(rate_hz=50, max_loop_count=10000)


def train(cfg, tub_names, model_name):

    X_keys = ['cam/image_array']
    y_keys = ['user/angle', 'user/throttle']


    def rt(record):
        record['user/angle'] = donkeycar.utils.utils.linear_bin(record['user/angle'])
        return record

    def combined_gen(gens):
        import itertools
        combined_gen = itertools.chain()
        for gen in gens:
            combined_gen = itertools.chain(combined_gen, gen)
        return combined_gen

    kl = KerasCategorical()
    logger.info('tub_names', tub_names)
    if not tub_names:
        tub_names = os.path.join(cfg.DATA_PATH, '*')
    tubgroup = TubGroup(tub_names)
    train_gen, val_gen = tubgroup.get_train_val_gen(X_keys, y_keys, record_transform=rt,
                                                    batch_size=cfg.BATCH_SIZE,
                                                    train_frac=cfg.TRAIN_TEST_SPLIT)

    model_path = os.path.expanduser(model_name)

    total_records = len(tubgroup.df)
    total_train = int(total_records * cfg.TRAIN_TEST_SPLIT)
    total_val = total_records - total_train
    logger.info('train: %d, validation: %d' % (total_train, total_val))
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    logger.ino('steps_per_epoch', steps_per_epoch)

    kl.train(train_gen,
             val_gen,
             saved_model_path=model_path,
             steps=steps_per_epoch,
             train_split=cfg.TRAIN_TEST_SPLIT)



if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    if args['drive']:
        drive(cfg, args['--model'])

    elif args['train']:
        tub = args['--tub']
        model = args['--model']
        train(cfg, tub, model)
