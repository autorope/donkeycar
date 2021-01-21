import os
import os
import time
import gym
import gym_donkeycar

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

class DonkeyGymEnv(object):

    def __init__(self, sim_path, host="127.0.0.1", port=9091, headless=0, env_name="donkey-generated-track-v0", sync="asynchronous", conf={}, delay=0):

        if sim_path != "remote":
            if not os.path.exists(sim_path):
                raise Exception("The path you provided for the sim does not exist.") 

            if not is_exe(sim_path):
                raise Exception("The path you provided is not an executable.") 

        conf["exe_path"] = sim_path
        conf["host"] = host
        conf["port"] = port
        conf['guid'] = 0
        self.env = gym.make(env_name, conf=conf)
        self.frame = self.env.reset()
        self.action = [0.0, 0.0, 0.0]
        self.running = True
        self.info = { 'pos' : (0., 0., 0.)}
        self.delay = float(delay)
        
    def update(self):
        while self.running:
            self.frame, _, _, self.info = self.env.step(self.action)

    def run_threaded(self, steering, throttle, brake=None):
        if steering is None or throttle is None:
            steering = 0.0
            throttle = 0.0
        if brake is None:
            brake = 0.0
        if self.delay > 0.0:
            time.sleep(self.delay / 1000.0)
        self.action = [steering, throttle, brake]
        return self.frame

    def shutdown(self):
        self.running = False
        time.sleep(0.2)
        self.env.close()


    
