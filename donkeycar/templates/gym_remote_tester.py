import os
import sys
import time
import math

from donkeycar.gym.gym_real import DonkeyRealEnv
from donkeycar.parts.cv import CvImageView, ImageScale

print("connecting to host", sys.argv[1])
os.environ['DONKEY_REMOTE_HOST'] = sys.argv[1]

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
