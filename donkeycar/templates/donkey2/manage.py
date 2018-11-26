#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it.

Usage:
    manage.py (drive) [--model=<model>] [--js] [--chaos]
    manage.py (train) [--tub=<tub1,tub2,..tubn>]  (--model=<model>) [--base_model=<base_model>] [--no_cache]

Options:
    -h --help        Show this screen.
    --tub TUBPATHS   List of paths to tubs. Comma separated. Use quotes to use wildcards. ie "~/tubs/*"
    --chaos          Add periodic random steering when manually driving
"""
import os
from docopt import docopt

import donkeycar as dk
from donkeypart_picamera import PiCamera
from donkeypart_keras_behavior_cloning import KerasLinear
from donkeypart_PCA9685_actuators import PCA9685, PWMSteering, PWMThrottle
from donkeypart_tub import TubGroup, TubWriter
from donkeypart_web_controller import LocalWebController
from donkeypart_common import Timestamp


def drive(cfg, model_path=None, use_chaos=False):
    """
    """

    V = dk.vehicle.Vehicle()

    clock = Timestamp()
    V.add(clock, outputs=['timestamp'])

    cam = PiCamera(resolution=cfg.CAMERA_RESOLUTION)
    V.add(cam, outputs=['cam/image_array'], threaded=True)

    ctr = LocalWebController(use_chaos=use_chaos)
    V.add(ctr,
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)

    state_controller = StateController()
    V.add(state_controller,
          inputs=['user/mode',
                  'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'],
          outputs=['angle', 'throttle', 'run_pilot_condition'])

    # Run the pilot if the mode is not user.
    kl = KerasLinear()
    if model_path:
        kl.load(model_path)

    V.add(kl,
          inputs=['cam/image_array'],
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot_condition')

    steering_controller = PCA9685(cfg.STEERING_CHANNEL)
    steering = PWMSteering(controller=steering_controller,
                           left_pulse=cfg.STEERING_LEFT_PWM,
                           right_pulse=cfg.STEERING_RIGHT_PWM) 

    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL)
    throttle = PWMThrottle(controller=throttle_controller,
                           max_pulse=cfg.THROTTLE_FORWARD_PWM,
                           zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                           min_pulse=cfg.THROTTLE_REVERSE_PWM)

    V.add(steering, inputs=['angle'])
    V.add(throttle, inputs=['throttle'])

    # add tub to save data
    inputs = ['cam/image_array', 'user/angle', 'user/throttle', 'user/mode', 'timestamp']
    types = ['image_array', 'float', 'float',  'str', 'str']

    # single tub
    tub = TubWriter(path=cfg.TUB_PATH, inputs=inputs, types=types)
    V.add(tub, inputs=inputs, run_condition='recording')

    # run the vehicle
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ,
            max_loop_count=cfg.MAX_LOOPS)


def train(cfg, tub_names, new_model_path, base_model_path=None):
    """
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    """
    X_keys = ['cam/image_array']
    y_keys = ['user/angle', 'user/throttle']

    new_model_path = os.path.expanduser(new_model_path)

    kl = KerasLinear()
    if base_model_path is not None:
        base_model_path = os.path.expanduser(base_model_path)
        kl.load(base_model_path)

    print('tub_names', tub_names)
    if not tub_names:
        tub_names = os.path.join(cfg.DATA_PATH, '*')
    tubgroup = TubGroup(tub_names)
    train_gen, val_gen = tubgroup.get_train_val_gen(X_keys, y_keys,
                                                    batch_size=cfg.BATCH_SIZE,
                                                    train_frac=cfg.TRAIN_TEST_SPLIT)

    total_records = len(tubgroup.df)
    total_train = int(total_records * cfg.TRAIN_TEST_SPLIT)
    total_val = total_records - total_train
    print('train: %d, validation: %d' % (total_train, total_val))
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    print('steps_per_epoch', steps_per_epoch)

    kl.train(train_gen,
             val_gen,
             saved_model_path=new_model_path,
             steps=steps_per_epoch,
             train_split=cfg.TRAIN_TEST_SPLIT)


class StateController:
    """
    Wraps a function into a donkey part.
    """

    def __init__(self):
        pass

    def run(self, mode,
            user_angle, user_throttle,
            pilot_angle, pilot_throttle):

        """

        Returns the angle, throttle and boolean if autopilot should be run.
        The angle and throttles returned are the ones given to the steering and
        throttle actuators.

        """

        if mode == 'user':
            return user_angle, user_throttle, False

        elif mode == 'local_angle':
            return pilot_angle, user_throttle, True

        else:
            return pilot_angle, pilot_throttle, True


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    if args['drive']:
        drive(cfg, model_path=args['--model'], use_chaos=args['--chaos'])

    elif args['train']:
        tub = args['--tub']
        new_model_path = args['--model']
        base_model_path = args['--base_model']
        cache = not args['--no_cache']
        train(cfg, tub, new_model_path, base_model_path)





