
import unittest
import time

from donkeycar.parts.odometer import Odometer

class TestOdometer(unittest.TestCase):
    
    def test_odometer(self):
        odometer = Odometer(0.2)         # 0.2 meters per revolution

        ts = time.time()                                     # initial time
        distance, velocity, timestamp = odometer.run(1, ts)  # first reading is one revolution
        self.assertEqual(ts, timestamp)
        self.assertEqual(0.2, distance)                      # distance travelled is 0.2 meters
        self.assertEqual(0, velocity)                        # zero velocity until we get two distances

        ts += 1                                              # add one second
        distance, velocity, timestamp = odometer.run(2, ts)  # total of 2 revolutions
        self.assertEqual(ts, timestamp)
        self.assertEqual(0.4, distance)                      # 0.4 meters travelled
        self.assertEqual(0.2, velocity)                      # 0.2 meters per second since last update

        ts += 1                                              # add one second
        distance, velocity, timestamp = odometer.run(2, ts)  # don't move
        self.assertEqual(ts, timestamp)
        self.assertEqual(0.4, distance)                      # still at 0.4 meters travelled
        self.assertEqual(0, velocity)                        # 0 meter per second in last interval

