"""Records training data and / or drives the car with tensorflow.
Usage:
    drive.py [--remote=<name>] 


Options:
  --remote=<name>   recording session name
  --fake_camera=<path>    path to pictures to use as the camera
"""

import os

from donkey.sensors import PiVideoStream
from donkey.actuators import (BaseSteeringActuator,
                              BaseThrottleActuator)

from donkey.vehicles import BaseVehicle
from donkey.remotes import RemoteClient


# Get args.
args = docopt(__doc__)


if __name__ == '__main__':

    remote_url = args['--remote']

    #Create your car your car
    car = BaseVehicle()

    #add sensors
    car.camera = PiVideoStream()

    #what controls the vehicle
    car.pilot = RemoteClient(remote_url, vehicle_id='mycar')
    
    #how the you change the steering angle and throttle of your vehicle.
    car.steering_actuator = PWMSteeringActuator(channel=1)
    car.throttle_actuator = PWMSteeringActuator(channel=0)

    car.start()
