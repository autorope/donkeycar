import unittest

import donkeycar as dk

class TestBaseCamera(unittest.TestCase):

    def setUp(self):
        self.camera = dk.sensors.BaseCamera()
        



if __name__ == '__main__':
    unittest.main()