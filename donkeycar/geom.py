'''
Geometry
Author: Tawn Kramer
Date: Nov 11, 2014
'''
from .la import Vec2

class LineSeg2d(object):

    def __init__(self, x1, y1, x2, y2):
        a = Vec2(x1, y1)
        b = Vec2(x2, y2)
        self.point = a
        self.end = b
        self.ray = a - b
        self.ray.normalize()

    def closest_vec_to(self, vec2_pt):
        '''
        produces a vector normal to this line passing through the given point vec2_pt
        '''
        delta_pt = self.point - vec2_pt
        dp = delta_pt.dot(self.ray)
        return self.ray * dp - delta_pt

    def cross_track_error(self, vec2_pt):
        '''
        a signed magnitude of distance from line segment
        '''
        err_vec = self.closest_vec_to(vec2_pt)
        mag = err_vec.mag()
        err_vec.scale(1.0 / mag)
        sign = 1.
        if err_vec.cross(self.ray) < 0.0:
            sign = -1.
        return mag * sign

