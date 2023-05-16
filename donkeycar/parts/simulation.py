#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parts to try donkeycar without a physical car.
"""

import random
import numpy as np


class MovingSquareTelemetry:
    """
    Generator of cordinates of a bouncing moving square for simulations.
    """
    def __init__(self, max_velocity=29,
                 x_min=10, x_max=150,
                 y_min=10, y_max=110):

        self.velocity = random.random() * max_velocity

        self.x_min, self.x_max = x_min, x_max
        self.y_min, self.y_max = y_min, y_max

        self.x_direction = random.random() * 2 - 1
        self.y_direction = random.random() * 2 - 1

        self.x = random.random() * x_max
        self.y = random.random() * y_max

        self.tel = self.x, self.y

    def run(self):
        # move
        self.x += self.x_direction * self.velocity
        self.y += self.y_direction * self.velocity

        # make square bounce off walls
        if self.y < self.y_min or self.y > self.y_max:
            self.y_direction *= -1
        if self.x < self.x_min or self.x > self.x_max:
            self.x_direction *= -1

        return int(self.x), int(self.y)

    def update(self):
        self.tel = self.run()

    def run_threaded(self):
        return self.tel


class SquareBoxCamera:
    """
    Fake camera that returns an image with a square box.

    This can be used to test if a learning algorithm can learn.
    """

    def __init__(self, resolution=(120, 160), box_size=4, color=(255, 0, 0)):
        self.resolution = resolution
        self.box_size = box_size
        self.color = color

    def run(self, x, y, box_size=None, color=None):
        """
        Create an image of a square box at a given coordinates.
        """
        radius = int((box_size or self.box_size)/2)
        color = color or self.color
        frame = np.zeros(shape=self.resolution + (3,))
        frame[y - radius: y + radius,
              x - radius: x + radius, :] = color
        return frame
