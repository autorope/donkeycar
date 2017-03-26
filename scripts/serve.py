"""
serve.py

Script to start the remote server to controll your car.

"""


import donkey as dk

#start server
w = dk.remotes.DonkeyPilotApplication()
w.start()