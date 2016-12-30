
import os

from donkey.datasets import images

from donkey.sensors import FakeCamera
from donkey.actuators import (BaseSteeringActuator,
                              BaseThrottleActuator)

from donkey.vehicles import BaseVehicle

from donkey.remotes import RemoteClient




car = BaseVehicle()

img_paths = images.load_file_paths('sidewalk')
car.camera = FakeCamera(img_paths) #For testing

car.steering_actuator = BaseSteeringActuator()
car.throttle_actuator = BaseSteeringActuator()

car.pilot = RemoteClient('http://localhost:8887', vehicle_id='mycar')

car.start()
