"""
Example to simulate a vehicle using images from a directory.
"""


import os

from donkey import datasets

from donkey.sensors import FakeCamera
from donkey.actuators import (BaseSteeringActuator,
                              BaseThrottleActuator)

from donkey.vehicles import BaseVehicle

from donkey.remotes import RemoteClient




car = BaseVehicle()

img_paths = datasets.load_file_paths('sidewalk')
car.camera = FakeCamera(img_paths) #For testing

car.steering_actuator = BaseSteeringActuator()
car.throttle_actuator = BaseSteeringActuator()

car.pilot = RemoteClient('http://localhost:8887', vehicle_id='mycar')

car.start()
