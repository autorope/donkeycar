from os.path import dirname, realpath 
import os
import PIL
import numpy as np
import pickle

import requests
import io

from .sessions import SessionHandler


def save_dataset(X, Y, file_path):
    with open(file_path, 'wb') as f:
        pickel.dump((X, Y), f)


def load_file(file_path):
    with open(file_path, 'rb') as f:
        X, Y = pickle.load(f)
    return X,Y


def load_url(url):
    r = requests.get(url)
    f = io.BytesIO(r.content)
    X, Y = pickle.load(f)
    return X, Y


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
        labels[t] = np.array([x, y])
        
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




