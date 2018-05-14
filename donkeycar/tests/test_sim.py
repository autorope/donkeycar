#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 12 2017

@author: tawnkramer
"""


import unittest
from donkeycar.parts.simulation import SteeringServer, FPSTimer
from donkeycar.parts.keras import KerasCategorical

class TestSimServer(unittest.TestCase):

    def test_create_sim_server(self):
        import socketio
        kc = KerasCategorical()
        sio = socketio.Server()
        assert sio is not None
        ss = SteeringServer(_sio=sio, kpart=kc)
        assert ss is not None

    def test_timer(self):
        tm = FPSTimer()
        assert tm is not None
        tm.reset()
        tm.on_frame()
        tm.on_frame()
        assert tm.iter == 2
        tm.iter = 100
        tm.on_frame()


