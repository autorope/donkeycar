# -*- coding: utf-8 -*-
import unittest
import numpy as np
from donkeycar.parts import autorope
from donkeycar.parts.autorope import AutoropeSession
import responses

class TestAutorope(unittest.TestCase):
    def setUp(self):
        token = '2f558f99180c070d1fbb2bd0dde1a871a8e5ef89'
        car_name = 'my car'
        api_base = 'http://localhost:8000/api/'
        self.autorope = AutoropeSession(token, car_name, api_base=api_base)

    @responses.activate
    def test_create_session_request(self):
        responses.add(responses.POST, self.autorope.api_base + 'sessions/',
                      json={'id': 123}, status=200)

        resp = self.autorope.post_request('sessions/',
                                          {'bot': 1, 'controller_url': 'http://192.2.2.1:8000'})
        js = resp.json()
        assert js.get('id') is not None



