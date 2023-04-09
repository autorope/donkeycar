"""
Lidar
"""
#
# requies glob to be installed: "pip3 install glob2"
# requires Adafruit RPLidar driver to be installed:
#   pip install Adafruit_CircuitPython_RPLIDAR
#
import logging
import sys
import time
import math
import pickle
import serial
import numpy as np
from donkeycar.utils import norm_deg, dist, deg2rad, arr_to_img
from PIL import Image, ImageDraw

logger = logging.getLogger("donkeycar.parts.lidar")

CLOCKWISE = 1
COUNTER_CLOCKWISE = -1


def limit_angle(angle):
    """
    make sure angle is 0 <= angle <= 360
    """
    while angle < 0:
        angle += 360
    while angle > 360:
        angle -= 360
    return angle


def angle_in_bounds(angle, min_angle, max_angle):
    """
    Determine if an angle is between two other angles.
    """
    if min_angle <= max_angle:
        return min_angle <= angle <= max_angle
    else:
        # If min_angle < max_angle then range crosses
        # zero degrees, so break up test
        # into two ranges
        return (min_angle <= angle <= 360) or (max_angle >= angle >= 0)


class RPLidar2(object):
    '''
    Adapted from https://github.com/Ezward/rplidar
    NOTES
    - empirical measurements show
      scan rate is 7 scans per second
      and 1846 measurements per second.
    '''
    def __init__(self,
                 min_angle = 0.0, max_angle = 360.0,
                 min_distance = sys.float_info.min,
                 max_distance = sys.float_info.max,
                 forward_angle = 0.0,
                 angle_direction=CLOCKWISE,
                 batch_ms=50,  # how long to loop in run()
                 debug=False):
        
        self.lidar = None
        self.port = None
        self.on = False

        help = []
        if min_distance < 0:
            help.append("min_distance must be >= 0")

        if max_distance <= 0:
            help.append("max_distance must be > 0")
            
        if min_angle < 0 or min_angle > 360:
            help.append("min_angle must be 0 <= min_angle <= 360")

        if max_angle <= 0 or max_angle > 360:
            help.append("max_angle must be 0 < max_angle <= 360")
          
        if forward_angle < 0 or forward_angle > 360:
            help.append("forward_angle must be 0 <= forward_angle <= 360")
            
        if angle_direction != CLOCKWISE and \
           angle_direction != COUNTER_CLOCKWISE:
            help.append("angle-direction must be 1 (clockwise) or -1 (counter-clockwise)")  # noqa

        if len(help) > 0:
            msg = "Could not start RPLidar; bad parameters passed to constructor"
            raise ValueError(msg + ": ".join(help))

        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.forward_angle = forward_angle
        self.spin_reverse = (args.angle_direction != CLOCKWISE)
        self.measurements = [] # list of (distance, angle, time, scan, index) 

        from adafruit_rplidar import RPLidar
        import glob
        
        #
        # find the serial port where the lidar is connected
        #
        port_found = False
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
        if not port_found:
            raise RuntimeError("No RPLidar is connected.")

        # initialize
        self.port = result[0]
        self.lidar = RPLidar(None, self.port, timeout=3)
        self.lidar.clear_input()
        time.sleep(1)

        self.measurement_count = 0  # number of measurements in the scan
        self.measurement_index = 0  # index of next measurement in the scan
        self.full_scan_count = 0
        self.full_scan_index = 0
        self.total_measurements = 0
        self.iter_measurements = self.lidar.iter_measurements()
        self.measurement_batch_ms = batch_ms

        self.running = True

    def poll(self):
        if self.running:
            try:
                #
                # read one measurement
                #
                new_scan, quality, angle, distance = next(self.iter_measurements)  # noqa
                                        
                now = time.time()
                self.total_measurements += 1

                # check for start of new scan
                if new_scan:
                    self.full_scan_count += 1
                    self.full_scan_index = 0
                    self.measurement_count = self.measurement_index  # this full scan
                    self.measurement_index = 0   # start filling in next scan
                    
                #
                # rplidar spins clockwise,
                # but we want angles to increase counter-clockwise
                #
                if self.spin_reverse:
                    angle = (360.0 - (angle % 360.0)) % 360.0
                
                # adjust so zero degrees is 'forward'
                angle = (angle - self.forward_angle + 360.0) % 360.0
            
                # filter the measurement by angle and distance
                if angle_in_bounds(angle, self.min_angle, self.max_angle):
                    if distance >= self.min_distance and distance <= self.max_distance:
                        #
                        # A measurement is a tuple of
                        #    (angle, distance, time, scan, index).
                        #
                        # distance = distance in millimeters as a float;
                        #            zero indicates invalid measurement
                        # angle: angle of measurement as a float
                        # time: time in seconds as a float
                        # scan:  full scan this measurement belongs to
                        #        as an integer
                        # index: index within full scan as an integer
                        #
                        # Note: The scan:index pair represents a natural key
                        #       identifying the measurement. This driver
                        #       maintains a circular buffer of measurements
                        #       that represent the most recent 360 degrees
                        #       of measurements.  This list may include
                        #       measurements from the current full scan and
                        #       from the previous full scan.  So if
                        #       run_threaded() is called rapidly
                        #       (faster than the scan rate of the lidar),
                        #       then the returned scans will have some new
                        #       values and some values that may have been
                        #       seen in the previous scan.  The scan:index
                        #       pair can be used to
                        #       to 'diff' scans to see which measurements
                        #       are are 'new' and which measurements are
                        #       shared between scans.
                        #
                        #       The time at which the measurement was
                        #       aquired is also included. In a moving
                        #       vehicle older measurements are less
                        #       relevant; the time field can be used to
                        #       filter out older measurements or to
                        #       visualize them differently (fading them out
                        #       perhaps). It may also help when using a
                        #       kinematic model to adjust for movement
                        #       of the lidar when attached to a vehicle.
                        #
                        measurement = (distance, angle, now,
                                        self.full_scan_count, self.full_scan_index)
                        
                        # grow buffer if necessary, otherwise overwrite
                        if self.measurement_index >= len(self.measurements):
                            self.measurements.append(measurement)
                            self.measurement_count = self.measurement_index + 1
                        else:
                            self.measurements[self.measurement_index] = measurement  # noqa
                        self.measurement_index += 1
                        self.full_scan_index += 1
                            
            except serial.serialutil.SerialException:
                logger.error('SerialException from RPLidar.')

    def update(self):
        start_time = time.time()
        while self.running:
            self.poll()
            time.sleep(0)  # yield time to other threads
        total_time = time.time() - start_time
        scan_rate = self.full_scan_count / total_time
        measurement_rate = self.total_measurements / total_time
        logger.info("RPLidar total scan time = {time} seconds".format(time=total_time))
        logger.info("RPLidar total scan count = {count} scans".format(count=self.full_scan_count))
        logger.info("RPLidar total measurement count = {count} measurements".format(count=self.total_measurements))
        logger.info("RPLidar rate = {rate} scans per second".format(rate=scan_rate))
        logger.info("RPLidar rate = {rate} measurements per second".format(rate=measurement_rate))

    def run_threaded(self):
        if self.running:
            return self.measurements
        return []
    
    def run(self):
        if not self.running:
            return []
        #
        # poll for 'batch' and return it
        # poll for time provided in constructor
        #
        batch_time = time.time() + self.measurement_batch_ms / 1000.0
        while True:
            self.poll()
            time.sleep(0)  # yield time to other threads
            if time.time() >= batch_time:
                break
        return self.measurements

    def shutdown(self):
        self.running = False
        time.sleep(2)
        if self.lidar is not None:
            self.lidar.stop()
            self.lidar.stop_motor()
            self.lidar.disconnect()
            self.lidar = None


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
        else:
            logger.error("No RPLidar connected")
            raise RuntimeError("No RPLidar connected")

    def update(self):
        scans = self.lidar.iter_scans(550)
        while self.on:
            try:
                for scan in scans:
                    self.distances = [item[2] for item in scan]
                    self.angles = [item[1] for item in scan]
            except serial.serialutil.SerialException:
                logger.error('SerialException from Lidar')

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
            logger.debug(self.lidar.GetDeviceInfo())
            self.gen = self.lidar.StartScanning()
        else:
            logger.error("Error connecting to YDLidar")
            raise RuntimeError("Error connecting to YDLidar")
        self.on = True


    def init(self, port='/dev/ttyUSB0'):
        import PyLidar3
        logger.debug("Starting lidar...")
        self.port = port
        self.distances = [] #a list of distance measurements
        self.angles = [] # a list of angles corresponding to dist meas above
        self.lidar = PyLidar3.YdLidarX4(port)
        if(self.lidar.Connect()):
            logger.debug(self.lidar.GetDeviceInfo())
            gen = self.lidar.StartScanning()
            return gen
        else:
            logger.error("Error connecting to YDLidar")
            raise RuntimeError("Error connecting to YDLidar")
        self.on = True

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
                logger.error('SerialException from Lidar.')

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

        draw.ellipse((min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)),
                     fill=(fill, fill, fill))

    def plot_scan(self, img, distances, angles, max_dist, draw):
        for dist, angle in zip(distances, angles):
            self.plot_fn(img, dist, angle, max_dist, draw)
            
    def run(self, distances, angles):
        '''
        takes two lists of equal length, one of distance values,
        the other of angles corresponding to the dist meas 
        '''
        self.frame = Image.new('RGB', self.resolution, (255, 255, 255))
        draw = ImageDraw.Draw(self.frame)
        self.plot_scan(self.frame, distances, angles, self.max_dist, draw)
        return self.frame

    def shutdown(self):
        pass


def mark_line(draw_context, cx, cy,
              distance_px, theta_degrees,
              mark_color, mark_px):
    theta = np.radians(theta_degrees)
    sx = cx + math.cos(theta) * distance_px
    sy = cy - math.sin(theta) * distance_px
    ex = cx + math.cos(theta) * (distance_px + mark_px)
    ey = cy - math.sin(theta) * (distance_px + mark_px)
    draw_context.line((sx, sy, ex, ey), fill=mark_color, width=1)


def mark_circle(draw_context, cx, cy,
                distance_px, theta_degrees,
                mark_color, mark_px):
    theta = np.radians(theta_degrees)
    sx = int(cx + math.cos(theta) * (distance_px + mark_px))
    sy = int(cy - math.sin(theta) * (distance_px + mark_px))
    draw_context.ellipse(
        (sx - mark_px, sy - mark_px, sx + mark_px, sy + mark_px),
        fill=mark_color)


def plot_polar_point(draw_context, bounds, mark_fn, mark_color, mark_px,
                     distance, theta, max_distance,
                     angle_direction=COUNTER_CLOCKWISE, rotate_plot=0):
    '''
    draw a 2d polar point to the given PIL image
    assuming the polar origin is at the center of bounding box
    
    draw_context: PIL draw context
    bounds: tuple (left, top, right, bottom) indicating bounds within which the
            plot should be drawn.
    mark_fn: mark drawing function
             func(draw_context, cx, cy, distance, theta_degrees, mark_px)
    mark_color: PIL color; scalar for monochrome, RGB tuplet for color.
    mark_px: size of mark in pixels
    distance: distance in mm
    theta: angle in degrees
    max_distance: largest distance that we will plot,
                  outside of this bound will be clipped
    angle_direction: direction in which angles increase;
                     CLOCKWISE or COUNTER_CLOCKWISE
    rotate_plot: degrees to rotate the plot (zero degrees is on positive x axis)
    '''

    if distance < 0 or distance > max_distance:
        return  # don't print out of range pixels

    left, top, right, bottom = bounds
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    max_pixel = min(cx, cy)
    distance_px = distance / max_distance * max_pixel
    
    theta = (theta + rotate_plot) % 360.0
        
    if angle_direction != COUNTER_CLOCKWISE:
        theta = (360.0 - (theta % 360.0)) % 360.0
        
    mark_fn(draw_context, cx, cy, distance_px, theta, mark_color, mark_px)


def plot_polar_points(draw_context, bounds, mark_fn, mark_color, mark_px,
                    measurements, max_distance,
                    angle_direction=COUNTER_CLOCKWISE, rotate_plot=0):
    """
    draw list of 2d polar points to given PIL image
    assuming the polar origin is at the center of bounding box
    
    draw_context: PIL draw context
    bounds: tuple (left, top, right, bottom) indicating bounds within which the
            plot should be drawn.
    mark_fn: function to draw point
             func(draw_context, cx, cy, distance_px, theta_degrees, mark_px)
    mark_color: PIL color; scalar for monochrome, RGB tuplet for color.
    mark_px: size of mark in pixels
    measurements: list of polar coordinates as (distance, angle) tuples
    max_distance: largest distance that we will plot,
                  outside of this bound will be clipped
    angle_direction: direction of increasing angles in the data;
                     CLOCKWISE or COUNTER_CLOCKWISE
    rotate_plot: angle in positive degrees to rotate the measurement mark.
                 this can be used to match the direction of the robot
                 when it is plotted in world coordinates.
    """    
    # plot each measurement
    for distance, angle in measurements:
        plot_polar_point(draw_context, bounds, mark_fn, mark_color, mark_px,
                              distance, angle, max_distance,
                              angle_direction, rotate_plot)


def plot_polar_bounds(draw_context, bounds, color,
                      angle_direction=COUNTER_CLOCKWISE, rotate_plot=0):
    """
    draw 2d polar bounds to given PIL image
    assuming the polar origin is at the center of bounding box
    and the bounding distance is the minimum of the
    width and height of the bounding box
    
    draw_context: PIL draw context
    bounds: tuple (left, top, right, bottom) indicating bounds within which the
            plot should be drawn.
    color: PIL color; scalar for monochrome, RGB tuplet for color.
    angle_direction: direction of increasing angles in the data;
                     CLOCKWISE or COUNTER_CLOCKWISE
    rotate_plot: angle in positive degrees to rotate the measurement mark.
                 this can be used to match the direction of the robot
                 when it is plotted in world coordinates.
    """

    left, top, right, bottom = bounds
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    max_pixel = min(cx, cy)
    
    #
    # draw the zero heading axis
    #
    # correct the angle for direction of scan
    theta = rotate_plot
    if angle_direction != COUNTER_CLOCKWISE:
        theta = (360.0 - (theta % 360.0)) % 360.0
    # draw the axis line
    theta = np.radians(theta)
    sx = cx + math.cos(theta) * max_pixel
    sy = cy - math.sin(theta) * max_pixel
    draw_context.ellipse(
        (cx - max_pixel, cy - max_pixel, cx + max_pixel, cy + max_pixel),
        outline=color)


def plot_polar_angle(draw_context, bounds, color, theta,
                     angle_direction=COUNTER_CLOCKWISE, rotate_plot=0):
    """
    draw 2d polar bounds to given PIL image
    assuming the polar origin is at the center of bounding box
    and the bounding distance is the minimum of the
    width and height of the bounding box
    
    draw_context: PIL draw context
    bounds: tuple (left, top, right, bottom) indicating bounds within which the
            plot should be drawn.
    color: PIL color; scalar for monochrome, RGB tuplet for color.
    angle_direction: direction of increasing angles in the data;
                     CLOCKWISE or COUNTER_CLOCKWISE
    rotate_plot: angle in positive degrees to rotate the measurement mark.
                 this can be used to match the direction of the robot
                 when it is plotted in world coordinates.
    """

    left, top, right, bottom = bounds
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    max_pixel = min(cx, cy)
    
    #
    # draw the zero heading axis
    #
    # correct the angle for direction of scan
    theta += rotate_plot
    if angle_direction != COUNTER_CLOCKWISE:
        theta = (360.0 - (theta % 360.0)) % 360.0
        
    # draw the angle line
    theta = np.radians(theta)
    sx = cx + math.cos(theta) * max_pixel
    sy = cy - math.sin(theta) * max_pixel
    draw_context.line((cx, cy, sx, sy), fill=color, width=1)


class LidarPlot2(object):
    '''
    takes the lidar measurements as a list of (distance, angle) tuples
    and plots them to a PIL image which it outputs
    
    resolution: dimensions of image in pixels as tuple (width, height)
    plot_type: PLOT_TYPE_CIRC or PLOT_TYPE_LINE
    mark_px: size of data measurement marks in pixels
    max_dist: polar bounds; clip measures whose distance > max_dist
    angle_direction: direction of increasing angles in the data;
                     CLOCKWISE or COUNTER_CLOCKWISE
    rotate_plot: angle in positive degrees to rotate the measurement mark.
                 this can be used to match the direction of the robot
                 when it is plotted in world coordinates.
    '''
    PLOT_TYPE_LINE = 0
    PLOT_TYPE_CIRCLE = 1
    def __init__(self,
                 resolution=(500,500),
                 plot_type=PLOT_TYPE_CIRCLE,
                 mark_px=3,
                 max_dist=4000, #mm
                 angle_direction=COUNTER_CLOCKWISE, 
                 rotate_plot=0,
                 background_color=(224, 224, 224),
                 border_color=(128, 128, 128),
                 point_color=(255, 64, 64)):
        
        self.frame = Image.new('RGB', resolution)
        self.mark_px = mark_px
        self.max_distance = max_dist
        self.resolution = resolution
        if plot_type == self.PLOT_TYPE_CIRCLE:
            self.mark_fn = mark_circle
        else:
            self.mark_fn = mark_line
        self.angle_direction = angle_direction
        self.rotate_plot = rotate_plot
        
        self.background_color = background_color
        self.border_color = border_color
        self.point_color = point_color

    def run(self, measurements):
        '''
        draw measurements to a PIL image and output the pil image
        measurements: list of polar coordinates as (distance, angle) tuples
        '''
            
        self.frame = Image.new('RGB', self.resolution, (255, 255, 255))
        bounds = (0, 0, self.frame.width, self.frame.height)
        draw = ImageDraw.Draw(self.frame)
        
        # background
        draw.rectangle(bounds, fill=self.background_color)

        # bounding perimeter and zero heading
        plot_polar_bounds(draw, bounds, self.border_color,
                          self.angle_direction, self.rotate_plot)
        plot_polar_angle(draw, bounds, self.border_color, 0,
                         self.angle_direction, self.rotate_plot)
        
        # data points
        plot_polar_points(
            draw, bounds, self.mark_fn, self.point_color, self.mark_px,
            [(distance, angle) for distance, angle, _, _, _ in measurements],
            self.max_distance, self.angle_direction, self.rotate_plot)
        
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

        laser_model = Laser(scan_size=360, scan_rate_hz=10.,
                            detection_angle_degrees=360,
                            distance_no_detection_mm=12000)
        MAP_QUALITY=5
        self.slam = RMHC_SLAM(laser_model,
                              MAP_SIZE_PIXELS, MAP_SIZE_METERS, MAP_QUALITY)
    
    def run(self, distances, angles, map_bytes):
        
        self.slam.update(distances, scan_angles_degrees=angles)
        x, y, theta = self.slam.getpos()

        if map_bytes is not None:
            self.slam.getmap(map_bytes)

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


if __name__ == "__main__":
    import argparse
    import cv2
    import json
    from threading import Thread
    
    def convert_from_image_to_cv2(img: Image) -> np.ndarray:
        # return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return np.asarray(img)
    
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rate", type=float, default=20,
                        help = "Number of scans per second")
    parser.add_argument("-n", "--number", type=int, default=40,
                        help = "Number of scans to collect")
    parser.add_argument("-a", "--min-angle", type=float, default=0,
                        help="Minimum angle in degress (inclusive) to save")
    parser.add_argument("-A", "--max-angle", type=float, default=360,
                        help="Maximum angle in degrees (inclusive) to save")
    parser.add_argument("-d", "--min-distance", type=float, default=sys.float_info.min,  # noqa
                        help="Minimum distance (inclusive) to save")
    parser.add_argument("-D", "--max-distance", type=float, default=4000,
                        help="Maximum distance (inclusive) to save")
    parser.add_argument("-f", "--forward-angle", type=float, default=0.0,
                        help="Forward angle - the angle facing 'forward'")
    parser.add_argument("-s", "--angle-direction", type=int, default=COUNTER_CLOCKWISE,  # noqa
                        help="direction of increasing angles (1 is clockwise, -1 is counter-clockwise)")  # noqa
    parser.add_argument("-p", "--rotate-plot", type=float, default=0.0,
                        help="Angle in degrees to rotate plot on cartesian plane")  # noqa
    parser.add_argument("-t", "--threaded", action='store_true', help = "run in threaded mode")

    # Read arguments from command line
    args = parser.parse_args()
    
    help = []
    if args.rate < 1:
        help.append("-r/--rate: must be >= 1.")
        
    if args.number < 1:
        help.append("-n/--number: must be >= 1.")
        
    if args.min_distance < 0:
        help.append("-d/--min-distance must be >= 0")

    if args.max_distance <= 0:
        help.append("-D/--max-distance must be > 0")
        
    if args.min_angle < 0 or args.min_angle > 360:
        help.append("-a/--min-angle must be 0 <= min-angle <= 360")

    if args.max_angle <= 0 or args.max_angle > 360:
        help.append("-A/--max-angle must be 0 < max-angle <= 360")
      
    if args.forward_angle < 0 or args.forward_angle > 360:
        help.append("-f/--forward-angle must be 0 <= forward-angle <= 360")
        
    if args.angle_direction != CLOCKWISE and \
       args.angle_direction != COUNTER_CLOCKWISE:
        help.append("-s/--angle-direction must be 1 (clockwise) or -1 (counter-clockwise)")  # noqa
        
    if args.rotate_plot < 0 or args.rotate_plot > 360:
        help.append("-p/--rotate-plot must be 0 <= min-angle <= 360")
        
    if len(help) > 0:
        parser.print_help()
        for h in help:
            print("  " + h)
        sys.exit(1)
        
    lidar_thread = None
    lidar = None
    
    try:
        scan_count = 0
        seconds_per_scan = 1.0 / args.rate
        scan_time = time.time() + seconds_per_scan

        #
        # construct a lidar part
        #
        lidar = RPLidar2(
            min_angle=args.min_angle, max_angle=args.max_angle,
            min_distance=args.min_distance, max_distance=args.max_distance,
            forward_angle=args.forward_angle,
            angle_direction=args.angle_direction,
            batch_ms=1000.0/args.rate)
        
        #
        # construct a lidar plotter
        #
        plotter = LidarPlot2(plot_type=LidarPlot2.PLOT_TYPE_CIRCLE,
                             max_dist=args.max_distance,
                             angle_direction=args.angle_direction,
                             rotate_plot=args.rotate_plot,
                             background_color=(32, 32, 32),
                             border_color=(128, 128, 128),
                             point_color=(64, 255, 64))        
        #
        # start the threaded part
        # and a threaded window to show plot
        #
        cv2.namedWindow("lidar")
        if args.threaded:
            lidar_thread = Thread(target=lidar.update, args=())
            lidar_thread.start()
            cv2.startWindowThread()
        
        while scan_count < args.number:
            start_time = time.time()

            # emit the scan
            scan_count += 1

            # get most recent scan and plot it
            if args.threaded:
                measurements = lidar.run_threaded()
            else:
                measurements = lidar.run()
            
            img = plotter.run(measurements)
            
            # show the image in the window
            cv2img = convert_from_image_to_cv2(img)
            cv2.imshow("lidar", cv2img)
            
            if not args.threaded:
                key = cv2.waitKey(1) & 0xFF
                if 27 == key or key == ord('q') or key == ord('Q'):
                    break

            # yield time to background threads
            sleep_time = seconds_per_scan - (time.time() - start_time)
            if sleep_time > 0.0:
                time.sleep(sleep_time)
            else:
                time.sleep(0)  # yield time to other threads

    except KeyboardInterrupt:
        print('Stopping early.')
    except Exception as e:
        print(e)
        exit(1)
    finally:
        if lidar is not None:
            lidar.shutdown()
            plotter.shutdown()
            cv2.destroyAllWindows()
        if lidar_thread is not None:
            lidar_thread.join()  # wait for thread to end
