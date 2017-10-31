import unittest

import donkeycar as dk
from donkeycar.parts.cameras import BaseCamera

class TestBaseCamera(unittest.TestCase):

    def setUp(self):
        self.camera = BaseCamera()
        



if __name__ == '__main__':
    unittest.main()