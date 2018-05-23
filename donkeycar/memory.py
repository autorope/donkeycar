#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 11:07:48 2017

@author: wroscoe
"""


class Memory:
    """
    A convenience class to save key/value pairs.
    """
    def __init__(self, *args, **kw):
        self.d = {}

    def __setitem__(self, key, value):
        if type(key) is not tuple:
            key = (key,)
            value=(value,)

        for i, k in enumerate(key):
            self.d[k] = value[i]

    def __getitem__(self, key):
        if type(key) is tuple:
            return [self.d[k] for k in key]
        else:
            return self.d[key]

    def update(self, new_d):
        self.d.update(new_d)

    def put(self, keys, inputs):
        if len(keys) > 1:
            for i, key in enumerate(keys):
                try:
                    self.d[key] = inputs[i]
                except IndexError as e:
                    error = str(e) + ' issue with keys: ' + str(key)
                    raise IndexError(error)
        else:
            self.d[keys[0]] = inputs

    def get(self, keys):
        result = [self.d.get(k) for k in keys]
        return result

    def keys(self):
        return self.d.keys()

    def values(self):
        return self.d.values()

    def items(self):
        return self.d.items()
