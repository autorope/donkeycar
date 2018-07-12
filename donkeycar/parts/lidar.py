"""
Lidar
"""

import time
import pickle
import numpy as np
from donkeycar.utils import norm_deg, dist

class RPLidar():
    '''
    https://github.com/SkoltechRobotics/rplidar
    '''
    def __init__(self, port='/dev/ttyUSB0'):
        from rplidar import RPLidar
        self.port = port
        self.distances = [] #a list of distance measurements 
        self.angles = [] # a list of angles corresponding to dist meas above
        self.lidar = RPLidar(self.port)
        self.lidar.clear_input()
        time.sleep(1)
        self.on = True


    def update(self):
        measurements = self.lidar.iter_measurments()
        while self.on:
            for quality, angles, distances in measurements:
                self.distances = distances.copy()
                self.angles = angles.copy()

    def run_threaded(self):
        return self.distances, self.angles

    def shutdown(self):
        self.on = False
        time.sleep(2)
        self.lidar.stop()
        self.lidar.stop_motor()
        self.lidar.disconnect()



class BreezySLAM(object):
    '''
    https://github.com/simondlevy/BreezySLAM
    '''
    def __init__(self, MAP_SIZE_PIXELS=500, MAP_SIZE_METERS=10):
        from breezyslam.algorithms import RMHC_SLAM
        from breezyslam.sensors import Laser

        laser_model = Laser(scan_size=360, scan_rate_hz=10., detection_angle_degrees=360, distance_no_detection_mm=12000)
        self.slam = RMHC_SLAM(laser_model, MAP_SIZE_PIXELS, MAP_SIZE_METERS)
    
    def run(self, distances, angles, map_bytes):
        
        self.slam.update(distances, scan_angles_degrees=angles)
        x, y, theta = self.slam.getpos()

        if map_bytes is not None:
            self.slam.getmap(map_bytes)

        return x, y, norm_deg(theta)

    def shutdown(self):
        pass



class BreezyMap(object):
    def __init__(self, MAP_SIZE_PIXELS=500):
        self.mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)

    def run(self):
        return self.mapbytes

    def shutdown(self):
        pass


class Path(object):
    def __init__(self, min_dist_rec = 10.):
        self.path = []
        self.min_dist = min_dist_rec
        self.x = 0.
        self.y = 0.

    def run(self, x, y):
        d = dist(x, y, self.x, self.y)
        if d > self.min_dist:
            self.path.append((x, y))
            self.x = x
            self.y = y

    def save(self, filename):
        outfile = open(filename, 'wb')
        pickle.dump(self.path, outfile)
    
    def load(self, filename):
        infile = open(filename, 'rb')
        self.path = pickle.load(infile)


class PathCTE(object):
    def __init__(self, path):
        self.path = path
        self.i_span = 0

    def run(self, x, y):
        cte = 0.
        closest_dist = 1000000.
        iClosest = 0
        for iPath, pos in enumerate(self.path.path):
            xp, yp = pos
            d = dist(x, y, xp, yp)
            if d < closest_dist:
                closest_dist = d
                iClosest = iPath

        #check if next or prev is closer
        iNext = (iClosest + 1) % len(self.path.path)
        iPrev = (iClosest - 1) % len(self.path.path)
        npx, npy = self.path.path[iNext]
        dist_next = dist(x, y, npx, npy)
        ppx, ppy = self.path.path[iPrev]
        dist_prev = dist(x, y, ppx, ppy)
        if dist_next < dist_prev:
            iB = iNext
        else:
            iB = iPrev

        ax, ay = self.path.path[iClosest]
        bx, by = self.path.path[iB]

        cx, cy = closest_pt_on_line(ax, ay, bx, by, x, y)


        return cte