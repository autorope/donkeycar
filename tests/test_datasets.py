import unittest

import donkey as dk 


class TestDatasets(unittest.TestCase):

    def test_moving_square(self):
        X, Y = dk.datasets.moving_square()
        

