#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 12:32:53 2017

@author: wroscoe
"""
import os
import sys
import time
import json
import datetime
import random
import itertools

from PIL import Image

import numpy as np


class Tub(object):
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
        try:
            with open(path, 'w') as fp:
                json.dump(json_data, fp)
                #print('wrote record:', json_data)
        except TypeError:
            print('troubles with record:', json_data)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def get_num_records(self):
        import glob
        files = glob.glob(os.path.join(self.path, 'record_*.json'))
        return len(files)

    def get_json_record_path(self, ix):
        return os.path.join(self.path, 'record_'+str(ix)+'.json')

    def get_json_record(self, ix):
        path = self.get_json_record_path(ix)
        try:
            with open(path, 'r') as fp:
                json_data = json.load(fp)
        except UnicodeDecodeError:
            raise Exception('bad record: %d. You may want to run `python manage.py check --fix`' % ix)            
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

        return json_data

    def check(self, fix=False):
        '''
        Iterate over all records and make sure we can load them.
        Optionally remove records that cause a problem.
        '''
        print('Checking tub:%s.' % self.path)
        print('Found: %d records.' % self.get_num_records())
        problems = False
        for ix in self.get_index(shuffled=False):
            try:
                self.get_record(ix)
            except:
                problems = True
                if fix == False:
                    print('problems with record:', self.path, ix)
                else:
                    print('problems with record, removing:', self.path, ix)
                    self.remove_record(ix)
        if not problems:
            print("No problems found.")

    def remove_record(self, ix):
        '''
        remove data associate with a record
        '''
        record = self.get_json_record_path(ix)
        os.unlink(record)

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
        for i in index:
            record = self.get_record(i)
            if record_transform:
                record = record_transform(record)
            yield record

    def batch_gen(self, keys=None, index=None, batch_size=128,
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


    def train_gen(self, X_keys, Y_keys, index=None, batch_size=128,
                  record_transform=None):
        batch_gen = self.batch_gen(X_keys+Y_keys, index, batch_size, record_transform)
        while True:
            batch = next(batch_gen)
            X = [batch[k] for k in X_keys]
            Y = [batch[k] for k in Y_keys]
            yield X, Y

            
    def train_val_gen(self, X_keys, Y_keys, batch_size=32, record_transform=None, train_split=.8):
        index = self.get_index(shuffled=True)
        train_cutoff = int(len(index)*train_split)
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



class TubImageStacker(Tub):
    '''
    A Tub for training a NN with images that are the last three records stacked 
    togther as 3 channels of a single image. The idea is to give a simple feedforward
    NN some chance of building a model based on motion.
    If you drive with the ImageFIFO part, then you don't need this.
    Just make sure your inference pass uses the ImageFIFO that the NN will now expect.
    '''
    
    def stack3Images(self, img_a, img_b, img_c):
        '''
        convert 3 rgb images into grayscale and put them into the 3 channels of
        a single output image
        '''
        width, height, _ = img_a.shape

        gray_a = cv2.cvtColor(img_a, cv2.COLOR_RGB2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_RGB2GRAY)
        gray_c = cv2.cvtColor(img_c, cv2.COLOR_RGB2GRAY)
        
        img_arr = np.zeros([width, height, 3], dtype=np.dtype('B'))

        img_arr[...,0] = np.reshape(gray_a, (width, height))
        img_arr[...,1] = np.reshape(gray_b, (width, height))
        img_arr[...,2] = np.reshape(gray_c, (width, height))

        return img_arr

    def get_record(self, ix):
        '''
        get the current record and two previous.
        stack the 3 images into a single image.
        '''
        data = super(TubImageStacker, self).get_record(ix)

        if ix > 1:
            data_ch1 = super(TubImageStacker, self).get_record(ix - 1)
            data_ch0 = super(TubImageStacker, self).get_record(ix - 2)

            json_data = self.get_json_record(ix)
            for key, val in json_data.items():
                typ = self.get_input_type(key)

                #load objects that were saved as separate files
                if typ == 'image':
                    val = self.stack3Images(data_ch0[key], data_ch0[key], data[key])
                    data[key] = val
                elif typ == 'image_array':
                    img = self.stack3Images(data_ch0[key], data_ch0[key], data[key])
                    val = np.array(img)

        return data


class TubChain:
    '''
    Multiple tubs chained together to generate data in one single training session
    '''

    def __init__(self, tub_paths, X_keys, Y_keys, batch_size=32, record_transform=None, train_split=.8):
        self.X_keys = X_keys
        self.Y_keys = Y_keys
        self.batch_size = batch_size
        self.record_transform = record_transform

        self.tub_dataset_splits = []

        for p in tub_paths:
            tub = Tub(p)
            index = tub.get_index(shuffled=True)
            train_cutoff = int(len(index)*train_split)
            train_index = index[:train_cutoff]
            val_index = index[train_cutoff:]
            self.tub_dataset_splits.append((tub, train_index, val_index))
    
    def train_gen(self):
        while True:
            gens = [tub_ds[0].train_gen(X_keys=self.X_keys, Y_keys=self.Y_keys, index=tub_ds[1],
                batch_size=self.batch_size, record_transform=self.record_transform)
                for tub_ds in self.tub_dataset_splits]

            for batch in itertools.chain(*gens):
                yield batch

    def val_gen(self):
        while True:
            gens = [tub_ds[0].train_gen(X_keys=self.X_keys, Y_keys=self.Y_keys, index=tub_ds[2],
                batch_size=self.batch_size, record_transform=self.record_transform)
                for tub_ds in self.tub_dataset_splits]

            for batch in itertools.chain(*gens):
                yield batch

    def train_val_gen(self):
        return self.train_gen(), self.val_gen()

    def total_records(self):
        return sum([t[0].get_num_records() for t in self.tub_dataset_splits])
