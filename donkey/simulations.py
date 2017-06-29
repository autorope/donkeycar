#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 17:30:28 2017

@author: wroscoe
"""
import random

class MovingSquareTelemetry:
    """
    Generator of cordinates of a bouncing moving square for simulations.
    """
    def __init__(self, max_velocity=29, 
                 x_min = 10, x_max=150, 
                 y_min = 10, y_max=110):
        
        self.velocity = random.random() * max_velocity
        
        self.x_min, self.x_max = x_min, x_max
        self.y_min, self.y_max = y_min, y_max
               
        self.x_direction = random.random() * 2 - 1
        self.y_direction = random.random() * 2 - 1
        
        self.x = random.random() * x_max
        self.y = random.random() * y_max 
        
    def run(self):
        #move
        self.x += self.x_direction * self.velocity
        self.y += self.y_direction * self.velocity
        
        #make square bounce off walls
        if self.y < self.y_min or self.y > self.y_max: 
            self.y_direction *= -1
        if self.x < self.x_min or self.x > self.x_max: 
            self.x_direction *= -1
        
        return int(self.x), int(self.y)
        