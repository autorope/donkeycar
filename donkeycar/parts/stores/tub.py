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
import random

from PIL import Image

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
        self.meta_path = os.path.join(self.path, 'meta.json')

        exists = os.path.exists(self.path)

        if exists:
            #load log and meta
            print("Tub does exist")
            with open(self.meta_path, 'r') as f:
                self.meta = json.load(f)
            self.current_ix = self.get_last_ix() + 1

        elif not exists and inputs:
            print('tub does NOT exist')
            #create log and save meta
            os.makedirs(self.path)
            self.meta = {'inputs': inputs, 'types': types}
            with open(self.meta_path, 'w') as f:
                json.dump(self.meta, f)
            self.current_ix = 0
        else:
            raise AttributeError('The path doesnt exist and you pass meta info.')

        self.start_time = time.time()


    def get_last_ix(self):
        index = self.get_index()
        return max(index)

    def get_index(self, shuffled=True):
        files = next(os.walk(self.path))[2]
        record_files = [f for f in files if f[:6]=='record']
        
        def get_file_ix(file_name):
            try:
                name = file_name.split('.')[0]
                num = int(name.split('_')[1])
            except:
                num = 0
            return num

        nums = [get_file_ix(f) for f in record_files]
        
        if shuffled:
            random.shuffle(nums)
        else:
            nums = sorted(nums)
            
        return nums 


    @property
    def inputs(self):
        return list(self.meta['inputs'])

    @property
    def types(self):
        return list(self.meta['types'])

    def get_input_type(self, key):
        input_types = dict(zip(self.inputs, self.types))
        return input_types.get(key)

    def write_json_record(self, json_data):
        path = self.get_json_record_path(self.current_ix)
        with open(path, 'w') as fp:
            try:
                json.dump(json_data, fp)
            except TypeError as te:
                print('Type Error in tub::write_json_record: ', te)
            except Exception as e:
                print('Exception in tub::write_json_record', e)

    def get_json_record_path(self, ix):
        return os.path.join(self.path, 'record_'+str(ix)+'.json')

    def get_json_record(self, ix):
        path = self.get_json_record_path(ix)
        with open(path, 'r') as fp:
            json_data = json.load(fp)
        return json_data

    def put_record(self, data):
        """
        Save values like images that can't be saved in the csv log and
        return a record with references to the saved values that can
        be saved in a csv.
        """
        json_data = {}
        
        for key, val in data.items():
            typ = self.get_input_type(key)

            if typ in ['str', 'float', 'int', 'boolean']:
                json_data[key] = val

            elif typ is 'image':
                path = self.make_file_path(key)
                val.save(path)
                json_data[key]=path

            elif typ == 'image_array':
                img = Image.fromarray(np.uint8(val))
                name = self.make_file_name(key, ext='.jpg')
                img.save(os.path.join(self.path, name))
                json_data[key]=name

            else:
                msg = 'Tub does not know what to do with this type {}'.format(typ)
                raise TypeError(msg)

        self.write_json_record(json_data)
        self.current_ix += 1

    def get_record(self, ix):

        json_data = self.get_json_record(ix)
        data={}
        for key, val in json_data.items():
            typ = self.get_input_type(key)

            #load objects that were saved as separate files
            if typ == 'image':
                val = Image.open(os.path.join(self.path, val))
            elif typ == 'image_array':
                img = Image.open(os.path.join(self.path, val))
                val = np.array(img)

            data[key] = val

        return data


    def make_file_name(self, key, ext='.png'):
        name = '_'.join([str(self.current_ix), key, ext])
        name = name = name.replace('/', '-')
        return name

    def delete(self):
        """ Delete the folder and files for this tub. """
        import shutil
        shutil.rmtree(self.path)

    def shutdown(self):
        pass


    def record_gen(self, index=None, record_transform=None):
        if index==None:
            index=self.get_index(shuffled=True)
        while True:
            for i in index:
                record = self.get_record(i)
                if record_transform:
                    record = record_transform(record)
                yield record

    def batch_gen(self, keys=None, index=None, batch_size=32,
                  record_tranform=None):
        record_gen = self.record_gen(index, record_tranform)
        if keys==None:
            keys = self.inputs
        while True:
            record_list = []
            for _ in range(batch_size):
                record_list.append(next(record_gen))

            batch_arrays = {}
            for i, k in enumerate(keys):
                arr = np.array([r[k] for r in record_list])
                #if len(arr.shape) == 1:
                #    arr = arr.reshape(arr.shape + (1,))
                batch_arrays[k] = arr

            yield batch_arrays


    def train_gen(self, X_keys, Y_keys, index=None, batch_size=32,
                  record_transform=None):
        batch_gen = self.batch_gen(X_keys+Y_keys, index, batch_size, record_transform)
        while True:
            batch = next(batch_gen)
            X = [batch[k] for k in X_keys]
            Y = [batch[k] for k in Y_keys]
            yield X, Y

            
    def train_val_gen(self, X_keys, Y_keys, batch_size=32, record_transform=None, train_split=.8):
        index = self.get_index(shuffled=True)
        train_cutoff = int(len(index)*.8)
        train_index = index[:train_cutoff]
        val_index = index[train_cutoff:]
    
        train_gen = self.train_gen(X_keys=X_keys, Y_keys=Y_keys, index=train_index, 
                              batch_size=batch_size, record_transform=record_transform)
        
        val_gen = self.train_gen(X_keys=X_keys, Y_keys=Y_keys, index=val_index, 
                              batch_size=batch_size, record_transform=record_transform)
        
        return train_gen, val_gen



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
        record = dict(zip(self.inputs, args))
        self.put_record(record)


class TubReader(Tub):
    def __init__(self, path, *args, **kwargs):
        super(TubReader, self).__init__(*args, **kwargs)

    def run(self, *args):
        '''
        API function needed to use as a Donkey part.

        Accepts keys to read from the tub and retrieves them sequentially.
        '''

        record = self.get_record()
        record = [record[key] for key in args ]
        return record


class TubHandler():
    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def get_tub_list(self,path):
        folders = next(os.walk(path))[1]
        return folders

    def next_tub_number(self, path):
        def get_tub_num(tub_name):
            try:
                num = int(tub_name.split('_')[1])
            except:
                num = 0
            return num

        folders = self.get_tub_list(path)
        numbers = [get_tub_num(x) for x in folders]
        #numbers = [i for i in numbers if i is not None]
        next_number = max(numbers+[0]) + 1
        return next_number

    def create_tub_path(self):
        tub_num = self.next_tub_number(self.path)
        date = datetime.datetime.now().strftime('%y-%m-%d')
        name = '_'.join(['tub',str(tub_num),date])
        tub_path = os.path.join(self.path, name)
        return tub_path

    def new_tub_writer(self, inputs, types):
        tub_path = self.create_tub_path()
        tw = TubWriter(path=tub_path, inputs=inputs, types=types)
        return tw
