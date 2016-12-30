"""
Script to start server to drive your car.
"""


from donkey.remotes import RemoteClient, RemoteServer
from donkey.pilots.base import BasePilot

from donkey.recorders import FileRecorder

#setup how server will save files and which pilot to use
pilot = BasePilot()
recorder = FileRecorder(sessions_dir='~/donkey_data/sesions')

#start server
w = RemoteServer(recorder, pilot)
w.start()