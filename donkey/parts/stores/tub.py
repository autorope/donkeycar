#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 12:32:53 2017

@author: wroscoe
"""
import os
import time
import json

from PIL import Image

import pandas as pd
import numpy as np


class Tub():
    """
    A datastore to store sensor data in a key, value format.
    
    Accepts str, int, float, image_array, image, and array data types.
    
    For example:
    
    #Create a tub to store speed values.
    >>> path = '~/mydonkey/test_tub'
    >>> inputs = ['user/speed', 'cam/image']
    >>> types = ['float', 'image']
    >>> t=Tub(path=path, inputs=inputs, types=types)
    
    """
    
    def __init__(self, path, inputs=None, types=None):
               
        self.path = os.path.expanduser(path)
        self.log_path = os.path.join(self.path, 'log.csv')
        self.meta_path = os.path.join(self.path, 'meta.json')
        
        exists = os.path.exists(self.path)
        self.current_ix = 0
        
        #TODO: Current handeling of existing tubs is bad.
        #If a tub already exists it will get overwritten silently.
        
        if exists:
            #load log and meta
            self.log = pd.read_csv(self.log_path,  index_col='ix')
            with open(self.meta_path, 'r') as f:
                self.meta = json.load(f)
                
        elif not exists and inputs and types:
            #create log and save meta
            os.makedirs(self.path)    
            self.log = pd.DataFrame(columns=inputs)
            self.log.index.name = 'ix'
            self.meta = {'inputs': inputs, 'types':types}
            with open(self.meta_path, 'w') as f:
                json.dump(self.meta, f)
        else:
            raise AttributeError('The path doesnt exist and you didnt give inputs and types')
        
        
        self.start_time = time.time()
        
    def get_last_ix(self):
        if len(self.log)<1:
            return 0
        else:
            return self.log.index[-1]
        
    @property
    def inputs(self):
        return self.meta['inputs']
    
    @property
    def types(self):
        return self.meta['types']
        
    def write_line(self, line):
        self.log.loc[self.current_ix] = line
        self.current_ix += 1
        
    def read_line(self, keys, ix):           
        line = dict(self.log.loc[ix, keys])
        return line
    
    def save_log(self):
        self.log.to_csv(self.log_path)
        
    def put_record(self, vals):
        """
        Save values like images that can't be saved in the csv log and
        return a record with references to the saved values that can
        be saved in a csv.
        """
        
        line = []
        
        for i, val in enumerate(vals):
            typ = self.types[i]
            key = self.inputs[i]
            
            if typ in ['str', 'float', 'int']:
                line.append(val)       

            elif typ is 'image':
                path = self.make_file_path(key)
                val.save(path)
                line.append(path)
                
            elif typ == 'image_array':
                path = self.make_file_path(key, ext='.png')
                img = Image.fromarray(np.uint8(val))
                img.save(path)
                line.append(path)

            else:
                msg = 'Tub does not know what to do with this type {}'.format(typ)
                raise TypeError(msg)
        
        #write csv line
        self.write_line(line)
    
    def get_record(self, *args, ix=None):
        if ix is None:
            ix = self.current_ix
        if len(args) < 0:
            keys = self.inputs
        else:
            keys = args
        
        log_record = self.read_line(keys, ix)
        record = {}
        
        for key, val in log_record.items():
            typ = self.types[self.inputs.index(key)]
            
            #load objects that were saved as separate files
            if typ == 'image':
                val = Image.open(val)
            elif typ == 'image_array':
                img = Image.open(val)
                val = np.array(img)
            
            record[key] = val
            
        return record
            
    
    @staticmethod
    def clean_file_name(name):
        name = name.replace('/', '-')
        return name
    
    def make_file_path(self, key, ext='.png'):
        name = '_'.join([str(self.current_ix), key, ext])
        name = self.clean_file_name(name)
        file_path = os.path.join(self.path, name)
        return file_path
        
    def delete(self):
        """ Delete the folder and files for this tub. """
        import shutil
        shutil.rmtree(self.path)
        
    def shutdown(self):
        self.save_log()
    
    
class TubWriter(Tub):
    def __init__(self, *args, **kwargs):
        super(TubWriter, self).__init__(*args, **kwargs)
    
    
    def run(self, *args):
        ''' 
        API function needed to use as a Donkey part.
        
        Accepts values, pairs them with their inputs keys and saves them
        to disk.
        '''
        
        assert len(self.inputs) == len(args)
        self.record_time = int(time.time() - self.start_time)
        self.put_record(args)
        
        
        
class TubReader(Tub):
    def __init__(self, path, *args, **kwargs):
        super(TubReader, self).__init__(*args, **kwargs)
    
    
    def run(self, *args):
        ''' 
        API function needed to use as a Donkey part.
        
        Accepts keys to read from the tub and retrieves them sequentially.
        '''
        
        record = self.get_record(args)
        record = [record[key] for key in args ]
        return record
