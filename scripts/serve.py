"""
Script to start the server to controll your car remotely via on Raspberry Pi that 
constantly requests directions from a remote server.

Usage:
    serve.py [--model=<name>] 


Options:
  --model=<name>   path to model file
"""

import os
from docopt import docopt

import donkey as dk



# Get args.
args = docopt(__doc__)

"""
model_path = args['--model']

if model_path is None: 
    #setup how server will save files and which pilot to use
    print('Starting servier without a pilot.')
    pilot = dk.pilots.BasePilot()

else:
    import keras
    #Load a trained keras model and use it in the KerasAngle pilot
    #model_file = '/home/wroscoe/code/donkey/whiteline_model.hdf5'
    model_file = model_path

    model = keras.models.load_model(model_file)
    pilot = dk.pilots.KerasAngle(model=model, throttle=20)


sessions_path = '~/donkey_data/sessions'
sh = dk.sessions.SessionHandler(sessions_path=sessions_path)
session = sh.new()

#start server
w = dk.remotes.RemoteServer(session, pilot)
w.start()

#in a browser go to localhost:8887 to drive your car


"""

#start server
w = dk.remotes.DonkeyPilotApplication()
w.start()