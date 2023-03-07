import os
import time
import gym
import gym_donkeycar


def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


class DonkeyGymEnv(object):
    def __init__(self, cfg, outputs):
        sim_path = cfg.DONKEY_SIM_PATH
        sim_host = cfg.SIM_HOST
        if sim_path != "remote":
            if not os.path.exists(sim_path):
                raise Exception(
                    "The path you provided for the sim does not exist.")

            if not is_exe(sim_path):
                raise Exception("The path you provided is not an executable.")

        gym_conf = cfg.GYM_CONF
        gym_conf["exe_path"] = sim_path
        gym_conf["host"] = sim_host
        gym_conf["port"] = 9091
        gym_conf["frame_skip"] = 1

        self.env = gym.make(cfg.DONKEY_GYM_ENV_NAME, conf=gym_conf)
        self.frame = self.env.reset()
        self.action = [0.0, 0.0, 0.0]
        self.running = True
        self.info = {
            'pos': (0., 0., 0.),
            'cte': 0.0,
            'speed': 0.0,
            'forward_vel': 0.0,
            'hit': False,
            'gyro': (0., 0., 0.),
            'accel': (0., 0., 0.),
            'vel': (0., 0., 0.),
            'odom': (0., 0., 0., 0.),
            'lidar': [],
            'orientation': (0., 0., 0.),
            'last_lap_time': 0.0,
            'lap_count': 0,
        }

        # output keys corresponding to info dict values
        self.info_keys = {
            'pos': 'pos',  # [x, y, z]
            'cte': 'cte',
            'speed': 'speed',
            'forward_vel': 'forward_vel',
            'hit': 'hit',
            'gyro': 'gyro',  # [x, y, z]
            'accel': 'accel',  # [x, y, z]
            'vel': 'vel',  # [x, y, z]
            'odom': 'odom',  # [fl, fr, rl, rr]
            'lidar': 'lidar',
            'orientation': "orientation",  # [roll, pitch, yaw]
            'last_lap_time': 'last_lap_time',
            'lap_count': 'lap_count',
        }

        self.output_keys = {}
        
        # fill in the output list according to the config
        try:
            for key, val in cfg.SIM_RECORD.items():
                if cfg.SIM_RECORD[key]:
                    outputs_key = self.info_keys[key]
                    outputs.append(outputs_key)
                    self.output_keys[key] = outputs_key
        except:
            raise Exception(
                "SIM_RECORD could not be found in config.py. Please add it to your config.py file.")

        self.delay = float(cfg.SIM_ARTIFICIAL_LATENCY) / 1000.0
        self.buffer = []

    def delay_buffer(self, frame, info):
        now = time.time()
        buffer_tuple = (now, frame, info)
        self.buffer.append(buffer_tuple)

        # go through the buffer
        num_to_remove = 0
        for buf in self.buffer:
            if now - buf[0] >= self.delay:
                num_to_remove += 1
                self.frame = buf[1]
            else:
                break

        # clear the buffer
        del self.buffer[:num_to_remove]

    def update(self):
        while self.running:
            if self.delay > 0.0:
                current_frame, _, _, current_info = self.env.step(self.action)
                self.delay_buffer(current_frame, current_info)
            else:
                self.frame, _, _, self.info = self.env.step(self.action)

    def run_threaded(self, steering, throttle, brake=None):
        if steering is None or throttle is None:
            steering = 0.0
            throttle = 0.0
        if brake is None:
            brake = 0.0

        self.action = [steering, throttle, brake]
        outputs = [self.frame]

        # fill in outputs according to required info
        for key, val in self.output_keys.items():
            if isinstance(val, list):
                outputs += self.info[key]
            else:
                outputs += [self.info[key]]

        if len(outputs) == 1:
            return self.frame
        else:
            return outputs

    def shutdown(self):
        self.running = False
        self.env.close()
