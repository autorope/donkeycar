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

args = docopt(__doc__)  

X, Y = dk.datasets.moving_square(n_frames=1000)

#sh = dk.sessions.SessionHandler('/home/wroscoe/donkey_data/sessions')
#s = sh.load('test')
#X, Y = s.load_dataset()


camera_sim = dk.sensors.ImgArrayCamera(X) #For testing

mixer = dk.mixers.BaseMixer()

if args['--remote'] is not None:
    remote_url = args['--remote']
else:
    remote_url = 'http://localhost:8887'

remote_pilot = dk.remotes.RemoteClient(remote_url, vehicle_id='mysim')


car = dk.vehicles.BaseVehicle(drive_loop_delay=.5,
                              camera=camera_sim,
							  actuator_mixer=mixer,
                              pilot=remote_pilot)

#start the drive loop
car.start()
