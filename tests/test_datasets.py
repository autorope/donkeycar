import unittest

import donkey as dk 


class TestSessions(unittest.TestCase):

    def test_load_data(self):
        ds = dk.datasets.load_session('sidewalk')
        ds.load_data()

