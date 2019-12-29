import pickle
import math
import logging
import cv2

import numpy
from PIL import Image, ImageDraw

from donkeycar.utils import norm_deg, dist, deg2rad, arr_to_img


class Path(object):
    def __init__(self, min_dist = 1.):
        self.path = []
        self.min_dist = min_dist
        self.x = math.inf
        self.y = math.inf
        self.recording = True

    def run(self, x, y):
        d = dist(x, y, self.x, self.y)
        if self.recording and d > self.min_dist:
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
        self.recording = False
    
    def clear(self):
        self.path = []
        self.recording = True

from collections import deque as Deque
class Route(object):
    def __init__(self, min_dist = 1., num_path_tracking=15):
        self.path = Deque(maxlen=num_path_tracking)
        self.waypoints = []
        self.min_dist = min_dist
        self.x = math.inf
        self.y = math.inf
        self.lastx = 0
        self.lasty = 0

    def run(self, x, y):
        self.x = x
        self.y = y
        d = dist(x, y, self.lastx, self.lasty)
        if d > self.min_dist:
            self.path.append((x, y))
            self.lastx = x
            self.lasty = y
        
        return self.path, self.waypoints

    def save_route(self, filename):
        outfile = open(filename, 'wb')
        pickle.dump(self.waypoints, outfile)
        print("saved route (waypoints) to file: ", filename)
    
    def save_waypoint(self):
        self.waypoints.append({"idx" : len(self.waypoints), "position" : (self.x, self.y)})
        print("saved waypoint")
    
    def load(self, filename):
        infile = open(filename, 'rb')
        self.waypoints = pickle.load(infile)
        print("loaded waypoints from file: ", filename)
    
    def clear(self):
        self.waypoints = []
        print("cleared all waypoints.")

    def update(self):
        pass

    def run_threaded(self, x, y):
        return self.run(x, y)

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

    def __init__(self):
        self.ox = 0.0
        self.oy = 0.0
        self.last_x = 0.
        self.last_y = 0.

    def run(self, x, y):
        self.last_x = x
        self.last_y = y

        return x + self.ox, y + self.oy

    def init_to_last(self):
        self.ox = -self.last_x
        self.oy = -self.last_y

class PathPlot(object):
    '''
    draw past path to an image
    '''
    def __init__(self, scale=1.0, offset=(0., 0.0), color=(255, 0, 0)):
        self.scale = scale
        self.offset = offset
        self.color = color

    def plot_path(self, path, draw):
        for iP in range(0, len(path)):
            ax, ay = path[iP]
            # flip y because on image y increases downwards
            draw.point((ax * self.scale + self.offset[0],
                      -ay * self.scale + self.offset[1]),
                      fill=self.color)

    def run(self, img, path):
        if type(img) is numpy.ndarray:
            stacked_img = numpy.stack((img,)*3, axis=-1)
            img = arr_to_img(stacked_img)

        draw = ImageDraw.Draw(img)
        self.plot_path(path, draw)

        return img

    def update(self):
        pass

    def run_threaded(self, img, path):
        return self.run(img, path)

class WaypointPlot(object):
    '''
    draw way points to an image
    '''
    def __init__(self, scale=1.0, offset=(0., 0.0), color=(255, 0, 0)):
        self.scale = scale
        self.offset = offset
        self.color = color

    def plot_wp(self, wpt, draw, color, width=1):
        sx = wpt['position'][0]
        sy = wpt['position'][1]
        idx = wpt['idx']
        draw.rectangle((sx * self.scale + self.offset[0] - 0.25 * self.scale,
                        -sy * self.scale + self.offset[1] - 0.25 * self.scale, 
                        sx * self.scale + self.offset[0] + 0.25 * self.scale, 
                        -sy * self.scale + self.offset[1] + 0.25 * self.scale), 
                        outline=color, width=width)
        draw.text((sx * self.scale + self.offset[0], -sy * self.scale + self.offset[1] - 0.25 * self.scale), 
                    str(idx), color=color, fill=color)

    def run(self, img, waypoints):
        if type(img) is numpy.ndarray:
            stacked_img = numpy.stack((img,)*3, axis=-1)
            img = arr_to_img(stacked_img)

        draw = ImageDraw.Draw(img)
        for waypt in waypoints:
            self.plot_wp(waypt, draw, color=self.color)

        return img

    def update(self):
        pass

    def run_threaded(self, img, waypoints):
        return self.run(img, waypoints)


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
    
class PlotPose(object):
    '''
    draw an arrow plot to an image
    '''
    def __init__(self,  scale=1.0, offset=(0., 0.), radius=8, color = (0, 255, 0)):
        self.scale = scale
        self.offset = offset
        self.radius = radius
        self.color = color
        self.origin_draw = True
        self.origin = offset

    def plot_pose(self, x, y, rad, yaw, draw, color, width=1):
        '''
        scale dist so that max_dist is edge of img (mm)
        and img is PIL Image, draw the circle using the draw ImageDraw object
        '''

        if self.origin_draw:
            draw.line((self.origin[0], self.origin[1], self.origin[0] + self.scale, self.origin[1]), fill=(255,0,0), width=1)
            draw.line((self.origin[0], self.origin[1], self.origin[0], self.origin[1] - self.scale), fill=(0,255,0), width=2)

        sx = x - rad
        sy = y - rad
        ex = x + rad
        ey = y + rad

        draw.ellipse([(sx, sy), (ex, ey)], fill=(0,255,0), width=3)
        dx = self.radius * 3. * math.cos(math.radians(yaw))
        dy = self.radius * 3. * math.sin(math.radians(yaw))
        draw.line([(x,y),(x+dx, y+dy)], fill=(255,0,0), width=3)


    def run(self, img, x, y, yaw):
        draw = ImageDraw.Draw(img)
        # flip y because on image y increases from top to bottom
        self.plot_pose(x * self.scale + self.offset[0],
                        -y * self.scale + self.offset[1], 
                        self.radius,
                        yaw,
                        draw, 
                        self.color)

        return img

from donkeycar.la import Line3D, Vec3

class CTE(object):

    def nearest_two_pts(self, path, x, y):
        if len(path) < 2:
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
            #logging.info("nearest: (%f, %f) to (%f, %f)" % ( a[0], a[1], x, y))
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

        return cte

class CTE2(object):

    def __init__(self):
        self.counter = 0
        self.cte = 0.

    def nearest_two_pts(self, path, x, y):
        if len(path) < 2:
            return None, None

        min_dist = 1000000
        min_idx = 0
        for i, p in enumerate(path):
            d = dist(p[0], p[1], x, y)
            if d < min_dist:
                min_dist = d
                min_idx = i
        iA = min_idx % len(path)
        a = path[iA]
        #iB is the next element in the path, wrapping around..
        iB = (iA + 1) % len(path)
        b = path[iB]
        
        return a, b

    def run(self, path, x, y):

        a, b = self.nearest_two_pts(path, x, y)
        
        if a and b:
            #logging.info("nearest: (%f, %f) to (%f, %f)" % ( a[0], a[1], x, y))
            a_v = Vec3(a[0], 0., a[1])
            b_v = Vec3(b[0], 0., b[1])
            p_v = Vec3(x, 0., y)
            line = Line3D(a_v, b_v)
            err = line.vector_to(p_v)
            sign = -1.0
            cp = line.dir.cross(err.normalized())
            if cp.y > 0.0 :
                sign = 1.0
            self.cte = err.mag() * sign
        return self.cte

class Navigator(object):

    def __init__(self, wpt_reach_tolerance=0.25):
        self.pos = numpy.array([0.,0.])
        self.wpts = []
        self.target = {'idx': 0, 'pos': numpy.array([0., 0.]), 'distance': 0.}
        self.wpt_reach_tolerance = wpt_reach_tolerance
    
    def _print_nav_info(self):
        print("Navigation target: {}, distance: {:.2f} m".format(self.target['idx'], self.target['distance']))

    def _increase_target(self):
        self.target['idx'] += 1
        self.target['idx'] = self.target['idx'] % len(self.wpts)

        self.target['pos'] = self.wpts[self.target['idx']]['position']
        self.target['distance'] = numpy.linalg.norm( self.pos - self.target['pos'])

    def _decrease_target(self):
        self.target['idx'] -= 1
        if self.target['idx'] < 0:
            self.target['idx'] = len(self.wpts) - 1
        self.target['pos'] = self.wpts[self.target['idx']]['position']
        self.target['distance'] = numpy.linalg.norm( self.pos - self.target['pos'])

    def increase_target(self):
        if len(self.wpts) > 0:
            self._increase_target()
            self._print_nav_info()
        else:
            print("cannot change waypoint target: no waypoints available")

    def decrease_target(self):
        if len(self.wpts) > 0:
            self._decrease_target()
            self._print_nav_info()
        else:
            print("cannot change waypoint target: no waypoints available")

    def run(self, waypoints, x, y, yaw):
        # update self and target
        self.pos = numpy.array([x,y])
        self.wpts= waypoints

        if len(self.wpts) == 0:
            self.target = {'idx': 0, 'pos': numpy.array([0., 0.]), 'distance': 0.}
            return 0
        else:
            self.target['pos'] = (
                                    waypoints[self.target['idx']]['position'][0], 
                                    waypoints[self.target['idx']]['position'][1]
            )
            self.target['distance'] = numpy.linalg.norm( self.pos - self.target['pos'])

            if self.target['distance'] < self.wpt_reach_tolerance:
                print("waypoint ", self.target['idx'], "reached! tolerance: ", self.wpt_reach_tolerance, " m.")
                self.increase_target()
                return 0.

            # compute error for PID control
            dest_dir = Vec3(self.target['pos'][0] - self.pos[0], self.target['pos'][1] - self.pos[1], 0).normalized()
            pose_dir = Vec3(math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0)
            error = dest_dir.cross(pose_dir)

            # print("error vector: ", error.x, error.y, error.z)
            # print("yaw = ", yaw)
            # print("pose_dir = ", pose_dir.x,pose_dir.y)
            # print("dest vec = ",  dest_dir.x,dest_dir.y)

            if error.z > 0.0 :
                return error.mag()
            else:
                return -error.mag()
    
    def update(self):
        pass

    def run_threaded(self, waypoints, x, y, yaw):
        return self.run(waypoints, x, y, yaw)

class PID_Pilot(object):

    def __init__(self, pid, throttle):
        self.pid = pid
        self.throttle = throttle

    def run(self, cte):
        steer = self.pid.run(cte)
        #logging.info("CTE: %f steer: %f" % (cte, steer))
        return steer, self.throttle

class PosStream:
    def run(self, trans, yaw):
        #RS_t265: y is up, x is right, z is backwards/forwards
        if trans is None:
            return 0,0,0
        else:
            return -trans.z, -trans.x, yaw

class gray2color:

    def __init__(self):
        self.img = None

    def run(self, img_gray):
        self.img = cv2.cvtColor(img_gray,cv2.COLOR_GRAY2RGB)

    def update(self):
        pass

    def run_threaded(self, img_gray):
        return self.run(img_gray)