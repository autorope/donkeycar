"""
Lidar
"""

# requies glob to be installed: "pip3 install glob2"
# requires Adafruit RPLidar driver to be installed: pip install Adafruit_CircuitPython_RPLIDAR

import time
import math
import pickle
import serial
import numpy as np
from donkeycar.utils import norm_deg, dist, deg2rad, arr_to_img
from PIL import Image, ImageDraw

class RPLidar(object):
    '''
    https://github.com/adafruit/Adafruit_CircuitPython_RPLIDAR
    '''
    def __init__(self, lower_limit = 0, upper_limit = 360, debug=False):
        from adafruit_rplidar import RPLidar

        # Setup the RPLidar
        PORT_NAME = "/dev/ttyUSB0"

        import glob
        port_found = False
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        temp_list = glob.glob ('/dev/ttyUSB*')
        result = []
        for a_port in temp_list:
            try:
                s = serial.Serial(a_port)
                s.close()
                result.append(a_port)
                port_found = True
            except serial.SerialException:
                pass
        if port_found:
            self.port = result[0]
            self.distances = [] #a list of distance measurements
            self.angles = [] # a list of angles corresponding to dist meas above
            self.lidar = RPLidar(None, self.port, timeout=3)
            self.lidar.clear_input()
            time.sleep(1)
            self.on = True
            #print(self.lidar.get_info())
            #print(self.lidar.get_health())
        else:
            print("No Lidar found")



    def update(self):
        scans = self.lidar.iter_scans(550)
        while self.on:
            try:
                for scan in scans:
                    self.distances = [item[2] for item in scan]
                    self.angles = [item[1] for item in scan]
            except serial.serialutil.SerialException:
                print('serial.serialutil.SerialException from Lidar. common when shutting down.')

    def run_threaded(self):
        sorted_distances = []
        if (self.angles != []) and (self.distances != []):
            angs = np.copy(self.angles)
            dists = np.copy(self.distances)

            filter_angs = angs[(angs > self.lower_limit) & (angs < self.upper_limit)]
            filter_dist = dists[(angs > self.lower_limit) & (angs < self.upper_limit)] #sorts distances based on angle values

            angles_ind = np.argsort(filter_angs)         # returns the indexes that sorts filter_angs
            if angles_ind != []:
                sorted_distances = np.argsort(filter_dist) # sorts distances based on angle indexes
        return sorted_distances


    def shutdown(self):
        self.on = False
        time.sleep(2)
        self.lidar.stop()
        self.lidar.stop_motor()
        self.lidar.disconnect()

class YDLidar(object):
    '''
    https://pypi.org/project/PyLidar3/
    '''
    def __init__(self, port='/dev/ttyUSB0'):
        import PyLidar3
        self.port = port
        self.distances = [] #a list of distance measurements
        self.angles = [] # a list of angles corresponding to dist meas above
        self.lidar = PyLidar3.YdLidarX4(port)
        if(self.lidar.Connect()):
            print(self.lidar.GetDeviceInfo())
            self.gen = self.lidar.StartScanning()
        else:
            print("Error connecting to lidar")
        self.on = True


    def init(self, port='/dev/ttyUSB0'):
        import PyLidar3
        print("Starting lidar...")
        self.port = port
        self.distances = [] #a list of distance measurements
        self.angles = [] # a list of angles corresponding to dist meas above
        self.lidar = PyLidar3.YdLidarX4(port)
        if(self.lidar.Connect()):
            print(self.lidar.GetDeviceInfo())
            gen = self.lidar.StartScanning()
            return gen
        else:
            print("Error connecting to lidar")
        self.on = True
        #print(self.lidar.get_info())
        #print(self.lidar.get_health())

    def update(self, lidar, debug = False):
        while self.on:
            try:
                self.data = next(lidar)
                for angle in range(0,360):
                    if(self.data[angle]>1000):
                        self.angles = [angle]
                        self.distances = [self.data[angle]]
                if debug:
                    return self.distances, self.angles
            except serial.serialutil.SerialException:
                print('serial.serialutil.SerialException from Lidar. common when shutting down.')

    def run_threaded(self):
        return self.distances, self.angles

    def shutdown(self):
        self.on = False
        time.sleep(2)
        self.lidar.StopScanning()
        self.lidar.Disconnect()

class LidarPlot(object):
    '''
    takes the raw lidar measurements and plots it to an image
    '''
    PLOT_TYPE_LINE = 0
    PLOT_TYPE_CIRC = 1
    def __init__(self, resolution=(500,500),
        max_dist=1000, #mm
        radius_plot=3,
        plot_type=PLOT_TYPE_CIRC):
        self.frame = Image.new('RGB', resolution)
        self.max_dist = max_dist
        self.rad = radius_plot
        self.resolution = resolution
        if plot_type == self.PLOT_TYPE_CIRC:
            self.plot_fn = self.plot_circ
        else:
            self.plot_fn = self.plot_line
            

    def plot_line(self, img, dist, theta, max_dist, draw):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the line using the draw ImageDraw object
        '''
        center = (img.width / 2, img.height / 2)
        max_pixel = min(center[0], center[1])
        dist = dist / max_dist * max_pixel
        if dist < 0 :
            dist = 0
        elif dist > max_pixel:
            dist = max_pixel
        theta = np.radians(theta)
        sx = math.cos(theta) * dist + center[0]
        sy = math.sin(theta) * dist + center[1]
        ex = math.cos(theta) * (dist + self.rad) + center[0]
        ey = math.sin(theta) * (dist + self.rad) + center[1]
        fill = 128
        draw.line((sx,sy, ex, ey), fill=(fill, fill, fill), width=1)
        
    def plot_circ(self, img, dist, theta, max_dist, draw):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the circle using the draw ImageDraw object
        '''
        center = (img.width / 2, img.height / 2)
        max_pixel = min(center[0], center[1])
        dist = dist / max_dist * max_pixel
        if dist < 0 :
            dist = 0
        elif dist > max_pixel:
            dist = max_pixel
        theta = np.radians(theta)
        sx = int(math.cos(theta) * dist + center[0])
        sy = int(math.sin(theta) * dist + center[1])
        ex = int(math.cos(theta) * (dist + 2 * self.rad) + center[0])
        ey = int(math.sin(theta) * (dist + 2 * self.rad) + center[1])
        fill = 128

        draw.ellipse((min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)), fill=(fill, fill, fill))

    def plot_scan(self, img, distances, angles, max_dist, draw):
        for dist, angle in zip(distances, angles):
            self.plot_fn(img, dist, angle, max_dist, draw)
            
    def run(self, distances, angles):
        '''
        takes two lists of equal length, one of distance values, the other of angles corresponding to the dist meas 
        '''
        self.frame = Image.new('RGB', self.resolution, (255, 255, 255))
        draw = ImageDraw.Draw(self.frame)
        self.plot_scan(self.frame, distances, angles, self.max_dist, draw)
        return self.frame

    def shutdown(self):
        pass


class BreezySLAM(object):
    '''
    https://github.com/simondlevy/BreezySLAM
    '''
    def __init__(self, MAP_SIZE_PIXELS=500, MAP_SIZE_METERS=10):
        from breezyslam.algorithms import RMHC_SLAM
        from breezyslam.sensors import Laser

        laser_model = Laser(scan_size=360, scan_rate_hz=10., detection_angle_degrees=360, distance_no_detection_mm=12000)
        MAP_QUALITY=5
        self.slam = RMHC_SLAM(laser_model, MAP_SIZE_PIXELS, MAP_SIZE_METERS, MAP_QUALITY)
    
    def run(self, distances, angles, map_bytes):
        
        self.slam.update(distances, scan_angles_degrees=angles)
        x, y, theta = self.slam.getpos()

        if map_bytes is not None:
            self.slam.getmap(map_bytes)

        #print('x', x, 'y', y, 'theta', norm_deg(theta))
        return x, y, deg2rad(norm_deg(theta))

    def shutdown(self):
        pass



class BreezyMap(object):
    '''
    bitmap that may optionally be constructed by BreezySLAM
    '''
    def __init__(self, MAP_SIZE_PIXELS=500):
        self.mapbytes = bytearray(MAP_SIZE_PIXELS * MAP_SIZE_PIXELS)

    def run(self):
        return self.mapbytes

    def shutdown(self):
        pass

class MapToImage(object):

    def __init__(self, resolution=(500, 500)):
        self.resolution = resolution

    def run(self, map_bytes):
        np_arr = np.array(map_bytes).reshape(self.resolution)
        return arr_to_img(np_arr)

    def shutdown(self):
        pass
