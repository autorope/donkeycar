#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 11:07:48 2017

@author: wroscoe
"""

class Memory():
    def __init__(self):
        self.dict = {}
        pass
    
    def put(self, keys, inputs):
        for i, key in enumerate(keys):
            self.dict[key] = inputs[i]
            
    def get(self, keys):
        result = [self.dict.get(k) for k in keys]
        return result