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
        if len(keys) > 1:
            for i, key in enumerate(keys):
                self.dict[key] = inputs[i]
        else:
            self.dict[keys[0]] = inputs
            
    def get(self, keys):
        result = [self.dict.get(k) for k in keys]
        return result