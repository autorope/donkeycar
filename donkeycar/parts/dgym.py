import os
import time
import gym
import gym_donkeycar

class DonkeyGymEnv(object):

    def __init__(self, sim_path, port=9090, headless=0, env_name="donkey-generated-track-v0", sync="asynchronous"):
        os.environ['DONKEY_SIM_PATH'] = sim_path
        os.environ['DONKEY_SIM_PORT'] = str(port)
        os.environ['DONKEY_SIM_HEADLESS'] = str(headless)
        os.environ['DONKEY_SIM_SYNC'] = str(sync)

        self.env = gym.make(env_name)
        self.frame = self.env.reset()
        self.action = [0.0, 0.0]
        self.running = True
        self.info = { 'pos' : (0., 0., 0.)}

    def update(self):
        while self.running:
            self.frame, _, _, self.info = self.env.step(self.action)

    def run_threaded(self, steering, throttle):
        if steering is None or throttle is None:
            steering = 0.0
            throttle = 0.0
        self.action = [steering, throttle]
        return self.frame

    def shutdown(self):
        self.running = False
        time.sleep(0.2)
        self.env.close()


    
