'''
file: gym_remote_tester.py
author: Tawn Kramer
date: 2019-01-25
desc: Control a remote donkey robot over network

args - pass the donkey name to connect to. ie.
python gym_remote_tester.py my_robot1234
'''
import os
import sys
import time
import math

from donkeycar.gym.gym_real import DonkeyRealEnv
from donkeycar.parts.cv import CvImageView, ImageScale

print("connecting to robot:", sys.argv[1])
os.environ['DONKEY_NAME'] = sys.argv[1]

env = DonkeyRealEnv()
action = (0., 0.)
view = CvImageView()
img_scale = ImageScale(scale = 4.0)
t = time.time()

while True:
    theta = time.time() - t
    steering = math.cos(theta)
    throttle = abs(math.sin(theta)) * 0.5
    action = (steering, throttle)
    observation, reward, done, info = env.step(action)
    img_scaled = img_scale.run(observation)
    view.run(img_scaled)
    time.sleep(0.05)
