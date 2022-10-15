import pickle
import math
import logging
import pathlib
import numpy
from PIL import Image, ImageDraw

from donkeycar.utils import norm_deg, dist, deg2rad, arr_to_img, is_number_type


class AbstractPath:
    def __init__(self, min_dist=1.):
        self.path = []
        self.min_dist = min_dist
        self.x = math.inf
        self.y = math.inf

    def run(self, recording, x, y):
        if recording:
            d = dist(x, y, self.x, self.y)
            if d > self.min_dist:
                logging.info(f"path point ({x},{y})")
                self.path.append((x, y))
                self.x = x
                self.y = y
        return self.path

    def length(self):
        return len(self.path)

    def is_empty(self):
        return 0 == self.length()

    def is_loaded(self):
        return not self.is_empty()

    def get_xy(self):
        return self.path

    def reset(self):
        self.path = []
        return True

    def save(self, filename):
        return False

    def load(self, filename):
        return False


class CsvPath(AbstractPath):
    def __init__(self, min_dist=1.):
        super().__init__(min_dist)

    def save(self, filename):
        if self.length() > 0:
            with open(filename, 'w') as outfile:
                for (x, y) in self.path:
                    outfile.write(f"{x}, {y}\n")
            return True
        else:
            return False

    def load(self, filename):
        path = pathlib.Path(filename)
        if path.is_file():
            with open(filename, "r") as infile:
                self.path = []
                for line in infile:
                    xy = [float(i.strip()) for i in line.strip().split(sep=",")]
                    self.path.append((xy[0], xy[1]))
            return True
        else:
            logging.info(f"File '{filename}' does not exist")
            return False

        self.recording = False


class RosPath(AbstractPath):
    def __init__(self, min_dist=1.):
        super().__init__(self, min_dist)

    def save(self, filename):
        outfile = open(filename, 'wb')
        pickle.dump(self.path, outfile)
        return True

    def load(self, filename):
        infile = open(filename, 'rb')
        self.path = pickle.load(infile)
        self.recording = False
        return True

class PImage(object):
    def __init__(self, resolution=(500, 500), color="white", clear_each_frame=False):
        self.resolution = resolution
        self.color = color
        self.img = Image.new('RGB', resolution, color=color)
        self.clear_each_frame = clear_each_frame

    def run(self):
        if self.clear_each_frame:
            self.img = Image.new('RGB', self.resolution, color=self.color)

        return self.img


class OriginOffset(object):
    '''
    Use this to set the car back to the origin without restarting it.
    '''

    def __init__(self, debug=False):
        self.debug = debug
        self.ox = None
        self.oy = None
        self.last_x = 0.0
        self.last_y = 0.0

    def run(self, x, y):
        if is_number_type(x) and is_number_type(y):
            # if origin is None, set it to current position
            if self.ox is None and self.oy is None:
                self.ox = x
                self.oy = y

            self.last_x = x
            self.last_y = y
        else:
            logging.debug("OriginOffset ignoring non-number")

        # translate the given position by the origin
        pos = (0, 0)
        if self.last_x is not None and self.last_y is not None and self.ox is not None and self.oy is not None:
            pos = (self.last_x - self.ox, self.last_y - self.oy)
        if self.debug:
            print(f"pos/x = {pos[0]}, pos/y = {pos[1]}")
        return pos

    def set_origin(self, x, y):
        logging.info(f"Resetting origin to ({x}, {y})")
        self.ox = x
        self.oy = y

    def reset_origin(self):
        """
        Reset the origin with the next value that comes in
        """
        self.ox = None
        self.oy = None

    def init_to_last(self):
        self.set_origin(self.last_x, self.last_y)


class PathPlot(object):
    '''
    draw a path plot to an image
    '''
    def __init__(self, scale=1.0, offset=(0., 0.0)):
        self.scale = scale
        self.offset = offset

    def plot_line(self, sx, sy, ex, ey, draw, color):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the line using the draw ImageDraw object
        '''
        draw.line((sx,sy, ex, ey), fill=color, width=1)

    def run(self, img, path):
        
        if type(img) is numpy.ndarray:
            stacked_img = numpy.stack((img,)*3, axis=-1)
            img = arr_to_img(stacked_img)

        if path:
            draw = ImageDraw.Draw(img)
            color = (255, 0, 0)
            for iP in range(0, len(path) - 1):
                ax, ay = path[iP]
                bx, by = path[iP + 1]
                self.plot_line(ax * self.scale + self.offset[0],
                            ay * self.scale + self.offset[1],
                            bx * self.scale + self.offset[0],
                            by * self.scale + self.offset[1],
                            draw,
                            color)
        return img


class PlotCircle(object):
    '''
    draw a circle plot to an image
    '''
    def __init__(self,  scale=1.0, offset=(0., 0.0), radius=4, color = (0, 255, 0)):
        self.scale = scale
        self.offset = offset
        self.radius = radius
        self.color = color

    def plot_circle(self, x, y, rad, draw, color, width=1):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the circle using the draw ImageDraw object
        '''
        sx = x - rad
        sy = y - rad
        ex = x + rad
        ey = y + rad

        draw.ellipse([(sx, sy), (ex, ey)], fill=color)


    def run(self, img, x, y):
        draw = ImageDraw.Draw(img)
        self.plot_circle(x * self.scale + self.offset[0],
                        y * self.scale + self.offset[1], 
                        self.radius,
                        draw, 
                        self.color)

        return img

from donkeycar.la import Line3D, Vec3

class CTE(object):

    # TODO: update so that we look for nearest two points starting from a given point
    #       and up to a given number of points.  This will speed things up
    #       but more importantly it can be used to handle crossing paths.
    def nearest_two_pts(self, path, x, y):
        if path is None or len(path) < 2:
            logging.error("path is none; cannot calculate nearest points")
            return None, None

        distances = []
        for iP, p in enumerate(path):
            d = dist(p[0], p[1], x, y)
            distances.append((d, iP, p))
        distances.sort(key=lambda elem : elem[0])
        iA = (distances[0][1] - 1) % len(path)
        a = path[iA]
        #iB is the next element in the path, wrapping around..
        iB = (iA + 2) % len(path)
        b = path[iB]
        
        return a, b

    def run(self, path, x, y):
        cte = 0.

        a, b = self.nearest_two_pts(path, x, y)
        
        if a and b:
            logging.info(f"nearest: ({a[0]}, {a[1]}) to ({x}, {y})")
            a_v = Vec3(a[0], 0., a[1])
            b_v = Vec3(b[0], 0., b[1])
            p_v = Vec3(x, 0., y)
            line = Line3D(a_v, b_v)
            err = line.vector_to(p_v)
            sign = 1.0
            cp = line.dir.cross(err.normalized())
            if cp.y > 0.0 :
                sign = -1.0
            cte = err.mag() * sign            
        else:
            logging.info(f"no nearest point to ({x},{y}))")
        return cte


class PID_Pilot(object):

    def __init__(self, pid, throttle):
        self.pid = pid
        self.throttle = throttle

    def run(self, cte):
        steer = self.pid.run(cte)
        logging.info("CTE: %f steer: %f" % (cte, steer))
        return steer, self.throttle
