
import os
import configparser
config = configparser.ConfigParser()

my_path = os.path.expanduser('~/mydonkey/')
sessions_path = os.path.join(my_path, 'sessions')
models_path = os.path.join(my_path, 'models')


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