"""
Script to start server to drive your car.
"""


from donkey.remotes import RemoteClient, RemoteServer
from donkey.pilots.base import BasePilot

from donkey.sessions import SessionHandler

#setup how server will save files and which pilot to use
pilot = BasePilot()

sh = SessionHandler(sessions_path='~/donkey_data/sesions')
session = sh.new()

#start server
w = RemoteServer(session, pilot)
w.start()