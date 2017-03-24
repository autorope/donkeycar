'''
datasets.py

Datasets consist of images (X) and the angle and throttle values (Y).
This file contains functions to manipulate these datasets and example 
datasets for convenience. 

TODO: This project really needs a data abstraction layer that just lets 
each component dump dictionarys of data with timestamps. A good model for this 
is the ROSBAG

Key functions of this databag include:
* save item
* load (sequential or shuffled) and be able to select only the keys you want.
* play/view - inspect the data. 

'''


from os.path import dirname, realpath 
import os
import PIL
import numpy as np
import pickle

import requests
import io
import h5py
import tempfile
import numpy as np
import math

import donkey as dk

def load_url(url):
    '''
    Download an h5py file and return X, Y. 

    TODO: save the file to datasets folder and check if its downloaded before downloading again.
    '''
    print('Starting download.')
    r = requests.get(url)
    name = tempfile.mktemp()
    with open(name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
    print('loading hdf5 file')
    f = h5py.File(name, "r")
    X = np.array(f['X'])
    Y = np.array(f['Y'])
    return X, Y


def row_gen(h5_path, ix):
    ''' 
    A generator to loop an hdf5 dataset referencing only
    the rows given in the index (ix).
    '''
    f = h5py.File(h5_path, "r")
    
    while True:
        i = np.random.choice(ix)
        yield dk.utils.norm_img(f['X'][i, :]), f['Y'][i, :]
        
        
def batch_gen(dataset_list, batch_size=128):
    '''
    Generator to return batches of randomly sampled data given a dictionary 
    of datasets containing their paths and indexes to sample from
    '''
       
    rgens = [row_gen(d['path'], d['ix']) for d in dataset_list]
    
    while True:
        X = []
        Y = []
        for i in range(batch_size):
            rg = np.random.choice(rgens)
            x, y = next(rg)
            X.append(x)
            Y.append(y)

        X = np.array(X)
        Y = np.array(Y)

        yield X, {'angle_out': dk.utils.bin_Y(Y[:, 0]), 'throttle_out': Y[:, 1]}
    
    
def split_datasets(h5_paths, val_frac=.1, test_frac=.1, batch_size=128):
    '''
    Return three shuffled generators for train, val and test.
    '''

    #create a dictionary of the datasets and their suffled indexes
    ds = []
    for p in h5_paths:
        d = {}
        file = h5py.File(p, "r")
        n = file['X'].shape[0]
        ix = np.arange(n)
        np.random.shuffle(ix)
        
        d['path'] = p
        d['n'] = n
        d['ix'] = ix
        
        ds.append(d)
        

    #split the datasets into train,val,test using by splitting their indexes
    ds_train = []
    ds_val =   []
    ds_test =  []
    
    for d in ds:
        d_train = {'path': d['path']}
        d_val =  {'path': d['path']}
        d_test = {'path': d['path']}
        
        val_cutoff = math.ceil(d['n'] * (1 - (val_frac + test_frac)))
        test_cutoff = math.ceil(d['n'] * (1- test_frac))
        
        d_train['ix'] = np.sort(d['ix'][:val_cutoff])
        d_val['ix'] = np.sort(d['ix'][val_cutoff:test_cutoff])
        d_test['ix']= np.sort(d['ix'][test_cutoff:])
        
        d_train['n'] = len(d_train['ix'])
        d_val['n'] = len(d_val['ix'])
        d_test['n'] = len(d_test['ix'])

        ds_train.append(d_train)
        ds_val.append(d_val)
        ds_test.append(d_test)

    #return a generator that combines all the datasets. 
    train = {'gen': batch_gen(ds_train), 'n': sum([i['n'] for i in ds_train])}
    val = {'gen': batch_gen(ds_val), 'n': sum([i['n'] for i in ds_val])}
    test = {'gen': batch_gen(ds_test), 'n': sum([i['n'] for i in ds_test])}

    return train, val, test   




    ######################
    #                    # 
    #  EXAMPLE DATASETS  #
    #                    #
    ######################


def moving_square(n_frames=100, return_x=True, return_y=True):
    
    '''
    Generate sequence of images of square bouncing around 
    the image and labels of its coordinates. Can be used as a 
    basic simple performance test of convolution networks. 
    '''
    
    row = 120
    col = 160
    movie = np.zeros((n_frames, row, col, 3), dtype=np.float)
    labels = np.zeros((n_frames, 2), dtype=np.float)

    #initial possition
    x = np.random.randint(20, col-20)
    y = np.random.randint(20, row-20)
    
    # Direction of motion
    directionx = -1
    directiony = 1
    
    # Size of the square
    w = 4
    
    for t in range(n_frames):
        #move
        x += directionx
        y += directiony
        
        #make square bounce off walls
        if y < 5 or y > row-5: 
            directiony *= -1
        if x < 5 or x > col-5: 
            directionx *= -1
            
        #draw square and record labels
        movie[t, y - w: y + w, x - w: x + w,  1] += 1
        labels[t] = np.array([(x-col/2)/(col/2), y/row])
        
    #convert array to dtype that PIL.Image accepts
    #and scale it to 0-256
    movie = np.uint8(movie*255.999)

    #only return requested labels
    if return_x and return_y:
        return movie, labels
    elif return_x and not return_y:
        return movie, labels[:,0]
    else:
        return movie, labels[:,1]