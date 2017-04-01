"""
Run a fake car on the same machine as your server. Fake images are 
created for the camera.

Usage:
    simulate.py [--remote=<name>] 


Options:
  --remote=<name>   remote url

"""


import os

import donkey as dk
from docopt import docopt
from os.path import expanduser

args = docopt(__doc__)  

X, Y = dk.datasets.moving_square(n_frames=3000)

camera_sim = dk.sensors.ImgArrayCamera(X) #For testing

mixer = dk.mixers.BaseMixer()

if args['--remote'] is not None:
    remote_url = args['--remote']
else:
    remote_url = 'http://localhost:8887'

model_path = expanduser("~") + '/mydonkey/models/default.h5'
remote = dk.remotes.RemoteClient(remote_url, vehicle_id='mysim')
pilot = dk.pilots.KerasCategorical(model_path=model_path)
pilot.load()

car = dk.vehicles.BaseVehicle(drive_loop_delay=.05,
                              camera=camera_sim,
							  actuator_mixer=mixer,
                              remote=remote,
                              pilot=pilot)

#start the drive loop
car.start()
