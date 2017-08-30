#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 12:32:53 2017

@author: wroscoe
"""
import os
import time
import json
import datetime

from PIL import Image

import numpy as np

class OriginalWriter:
    """
    A datastore to store sensor data in the original `filename format' and a *.json
    file with the same index.

    Accepts str, int, float, image_array, image, and array data types.

    """

    def __init__(self, path, inputs = None, types = None):
        self.path = os.path.expanduser(path)
        self.current_ix = 0

        exists = os.path.exists(self.path)


        if exists:
            # XXX: Find the biggest index and use that to continue.
            pass
        elif not exists and inputs and types:
            os.makedirs(self.path)

            meta_inputs = []
            meta_types = []
            for i, v in enumerate(types):
                if v != 'boolean':
                    meta_inputs.append(inputs[i])
                    meta_types.append(v)

            self.orig = { 'inputs': inputs, 'types': types }
            self.meta = { 'inputs': meta_inputs, 'types': meta_types }
            self.current_ix = 0
        else:
            raise AttributeError('The path doesnt exist and you didnt give inputs and types')

        self.start_time = time.time()

    def make_img_path(self, ext = '.jpg'):
        name = "frame_%.5d_ttl_%.3f_agl_%.3f_mil_%.1f%s" % (self.current_ix, self.out['trottle'], self.out['angle'], self.out['milliseconds'], ext)
        file_path = os.path.join(self.path, name)
        return file_path

    def make_json_path(self):
        name = "frame_%.5d.json" % self.current_ix
        file_path = os.path.join(self.path, name)
        return file_path

    def run(self, *args):
        '''
        API function needed to use as a Donkey part.

        Accepts values, pairs them with their inputs keys and saves them
        to disk.
        '''
        assert len(self.orig['inputs']) == len(args)

        t = time.time()
        self.record_time = (t - self.start_time) * 1000

        write = False
        self.out = { 'extra': {} }

        for i, val in enumerate(args):
            typ = self.orig['types'][i]
            key = self.orig['inputs'][i]

            if typ == 'boolean':      # the recording value
                write = val

        if write:
            self.out['milliseconds'] = self.record_time
            self.out['extra']['linaccel'] = None
            img = None

            for i, val in enumerate(args):
                typ = self.orig['types'][i]
                key = self.orig['inputs'][i]

                if typ in [ 'float' ]:
                    if key == 'user/angle':
                        self.out['angle'] = val
                    elif key == 'user/throttle':
                        self.out['trottle'] = val
                    elif key == 'odo/speed':
                        self.out['extra']['speed'] = val
                elif typ is 'str':
                    if key == 'user/mode':
                        self.out['extra']['mode'] = val
                elif typ == 'image_array':
                    img = Image.fromarray(np.uint8(val))
                elif typ == 'boolean':
                    pass
                else:
                    msg = 'OriginalWriter does not know what to do with this type {}'.format(typ)
                    raise TypeError(msg)

            if img != None:
                path = self.make_img_path()
                img.save(path, 'jpeg')

                path = self.make_json_path()
                f = open(path, 'w')
                self.out['extra']['time'] = (time.time() - t) * 1000
                json.dump(self.out, f)
                f.close()
                self.current_ix += 1

    def shutdown(self):
        pass
