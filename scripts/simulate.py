"""
Run a fake car on the same machine as your server. Fake images are 
created for the camera.

"""


import os

import donkey as dk


X, Y = dk.datasets.moving_square(n_frames=1000)

#sh = dk.sessions.SessionHandler('/home/wroscoe/donkey_data/sessions')
#s = sh.load('test')
#X, Y = s.load_dataset()


camera_sim = dk.sensors.ImgArrayCamera(X) #For testing

mixer = dk.mixers.BaseMixer()

remote_pilot = dk.remotes.RemoteClient('http://localhost:8887', vehicle_id='mycar2')


car = dk.vehicles.BaseVehicle(drive_loop_delay=.5,
                              camera=camera_sim,
							  actuator_mixer=mixer,
                              pilot=remote_pilot)

#start the drive loop
car.start()
