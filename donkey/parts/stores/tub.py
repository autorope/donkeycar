#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 12:32:53 2017

@author: wroscoe
"""
import os
import time
import csv 

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
    
    
    
    def __init__(self, path, inputs, types, overwrite=False):
               
        self.path = os.path.expanduser(path)
        self.log_path = os.path.join(self.path, 'log.txt')
        
        self.inputs = inputs
        self.types = types
        
        if overwrite:
            if os.path.exists(self.path):
                self.delete()

        self.load_log(overwrite=overwrite)
        self.record_id = 0
        self.start_time = time.time()
            
    def load_log(self, overwrite=False):
        """
        Create the datastore directory and open it's log.
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)    
        
        exists=False
        if os.path.exists(self.log_path):
            exists = True
                
        self.log_file = open(self.log_path, 'a')
        self.log_writer = csv.writer(self.log_file)
        
        if not exists:
            self.write_log_header()
            
            
    def write_log_header(self):
        self.write_log_record(self.inputs)
        
        
    def write_log_record(self, line):
        self.log_writer.writerow(line)
        
    
    def close_log(self):
        self.log_file.close()
            
    def read_log(self):
        self.close_log()
        return pd.read_csv(self.log_path)
    
        
    def save_image(self, path, image):
            image.save(path)
            return path
        
    def save_array(self, key, array):
            file_path = self.make_file_path(key, ext='.npy')
            array.tofile(file_path)
            return file_path
    
    
    def run(self, *args):
        
        ''' Save the key and value to disk.'''
        
        assert len(self.inputs) == len(args)
        self.record_time = int(time.time() - self.start_time)

        record = self.prepare_record(args)
        self.write_log_record(record)
        self.record_id += 1
        
    def prepare_record(self, vals):
        """
        Save values like images that can't be saved in the csv log and
        return a record with references to the saved values that can
        be saved in a csv.
        """
        
        record = []
        
        for i, val in enumerate(vals):
            typ = self.types[i]
            key = self.inputs[i]
            
            if typ in ['str', 'float', 'int']:
                record.append(val)       

            elif typ is 'image':
                path = self.make_file_path(key)
                self.save_image(path, val)
                record.append(path)
                
            elif typ is 'image_array':
                path = self.make_file_path(key)
                img = Image.fromarray(np.uint8(val))
                self.save_image(path, img)
                record.append(path)

            else:
                raise TypeError('Tub does not know what to do with this type {}'.format(typ))
        
        return record
    
    @staticmethod
    def clean_file_name(name):
        name = name.replace('/', '-')
        return name
    
    def make_file_path(self, key, ext='.png'):
        name = '_'.join([str(self.record_id), key, str(self.record_time), ext])
        name = self.clean_file_name(name)
        file_path = os.path.join(self.path, name)
        return file_path
        
    def delete(self):
        """ Delete the folder and files for this tub. """
        import shutil
        shutil.rmtree(self.path)