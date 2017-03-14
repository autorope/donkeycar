
import os
import configparser

import donkey as dk

import keras

if int(keras.__version__.split('.')[0]) < 3:
    raise ImportError('You need keras version 2.0.0 or higher. Run "pip install keras --upgrade"')

config = configparser.ConfigParser()

my_path = os.path.expanduser('~/mydonkey/')
sessions_path = os.path.join(my_path, 'sessions')
models_path = os.path.join(my_path, 'models')
datasets_path = os.path.join(my_path, 'datasets')
results_path = os.path.join(my_path, 'results')


def setup_paths():
    dk.utils.make_dir(my_path)

    paths = [sessions_path, models_path, 
             datasets_path, results_path]

    for p in paths:
        dk.utils.make_dir(p)


def parse_config(config_path):
    config_path = os.path.expanduser(config_path)
    config.read(config_path)

    cfg={}

    vehicle = config['vehicle']
    cfg['vehicle_id'] = vehicle.get('id')
    cfg['vehicle_loop_delay'] = vehicle.getfloat('loop_delay')

    camera = config['camera']
    cfg['camera_loop_delay'] = camera.getfloat('loop_delay')

    t_act = config['throttle_actuator']
    cfg['throttle_actuator_channel'] = t_act.getint('channel')
    cfg['throttle_actuator_min_pulse'] = t_act.getint('min_pulse')
    cfg['throttle_actuator_max_pulse'] = t_act.getint('max_pulse')
    cfg['throttle_actuator_zero_pulse'] = t_act.getint('zero_pulse')

    s_act = config['steering_actuator']
    cfg['steering_actuator_channel'] = s_act.getint('channel')
    cfg['steering_actuator_min_pulse'] = s_act.getint('left_pulse')
    cfg['steering_actuator_max_pulse'] = s_act.getint('right_pulse')

    return cfg