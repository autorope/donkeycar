import unittest

import donkey as dk

class TestBaseCamera(unittest.TestCase):

    def setUp(self):
        self.camera = dk.sensors.BaseCamera()
        

    def test_capture_arr(self):
        arr = self.camera.capture_arr()
        assert arr.shape[2] == 3 #3 RGB channels

    def test_capture_img(self):
        img = self.camera.capture_img()
        print(type(img))



if __name__ == '__main__':
    unittest.main()