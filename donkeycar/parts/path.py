import pickle
import math
import logging

from PIL import Image, ImageDraw

from donkeycar.utils import norm_deg, dist, deg2rad, arr_to_img


class Path(object):
    def __init__(self, min_dist = 1.):
        self.path = []
        self.min_dist = min_dist
        self.x = math.inf
        self.y = math.inf

    def run(self, x, y):
        d = dist(x, y, self.x, self.y)
        if d > self.min_dist:
            self.path.append((x, y))
            logging.info("path point (%f, %f)" % ( x, y))
            self.x = x
            self.y = y
        return self.path

    def save(self, filename):
        outfile = open(filename, 'wb')
        pickle.dump(self.path, outfile)
    
    def load(self, filename):
        infile = open(filename, 'rb')
        self.path = pickle.load(infile)


class PathPlot(object):
    '''
    draw a path plot to an image
    '''
    def __init__(self, resolution=(500, 500), scale=1.0, offset=(0., 0.0)):
        self.scale = scale
        self.offset = offset
        self.img = Image.new('RGB', resolution, color="white")

    def plot_line(self, sx, sy, ex, ey, draw, color):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the line using the draw ImageDraw object
        '''
        draw.line((sx,sy, ex, ey), fill=color, width=1)

    def run(self, path):
        draw = ImageDraw.Draw(self.img)
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

        return self.img


