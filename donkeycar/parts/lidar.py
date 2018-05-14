"""
Lidar
"""

import time
import numpy as np


class RPLidar():
    def __init__(self, port='/dev/ttyUSB0'):
        from rplidar import RPLidar
        self.port = port
        self.frame = np.zeros(shape=365)
        self.lidar = RPLidar(self.port)
        self.lidar.clear_input()
        time.sleep(1)
        self.on = True


    def update(self):
        self.measurements = self.lidar.iter_measurments(500)
        for new_scan, quality, angle, distance in self.measurements:
            angle = int(angle)
            self.frame[angle] = 2*distance/3 + self.frame[angle]/3
            if not self.on:
                break

    def run_threaded(self):
        return self.frame
