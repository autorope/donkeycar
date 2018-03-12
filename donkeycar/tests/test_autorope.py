# -*- coding: utf-8 -*-
import unittest
import numpy as np
from donkeycar.parts import autorope
from donkeycar.parts.autorope import Autorope_Connection


class TestAutorope(unittest.TestCase):
    def setUp(self):
        token = '2f558f99180c070d1fbb2bd0dde1a871a8e5ef89'
        car_name = 'my car'
        self.autorope = Autorope_Connection(token, car_name)
        self.autorope.api_base = 'http://localhost:8000/api/'


    def test_create_session_request(self):
        resp = self.autorope.post_request('sessions/',
                                          {'bot': 1, 'controller_url': 'http://192.2.2.1:8000'} )
        js = resp.json()
        assert js.get('id') is not None



