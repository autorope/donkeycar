"""
Script to start server to drive your car.
"""

import donkey as dk 


#setup how server will save files and which pilot to use
pilot = dk.pilots.BasePilot()

sessions_path = '~/donkey_data/sessions'
sh = dk.sessions.SessionHandler(sessions_path=sessions_path)
session = sh.new()

#start server
w = dk.remotes.RemoteServer(session, pilot, port=8886)
w.start()

#in a browser go to localhost:8887 to drive your car
