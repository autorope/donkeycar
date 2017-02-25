"""
Script to start the server to controll your car remotely via on Raspberry Pi that 
constantly requests directions from a remote server.

"""


import donkey as dk

#start server
w = dk.remotes.DonkeyPilotApplication()
w.start()