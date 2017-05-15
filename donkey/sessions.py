'''
sessions.py

Class to simplify how data is saved while recording.

TODO: This should be merged with the dataset abstraction and made into
something like ROSBAGS.

'''

import json
import os
import time
import itertools
import numpy as np
import h5py
from PIL import Image
from skimage import exposure

import pickle

import donkey as dk

class Session():
    '''
    Class to store images and vehicle data to the local file system and later retrieve them
    as arrays or generators.
    '''

    def __init__(self, path):
        print('Loading Session: %s' %path)
        self.session_dir = path
        self.frame_count = 0

    def put(self, img, angle=None, throttle=None, milliseconds=None, req = None):
        '''
        Save image with encoded angle, throttle and time data in the filename
        '''
        self.frame_count += 1
        filepath = create_img_filepath(self.session_dir, self.frame_count, angle, throttle, milliseconds)
        img.save(filepath, 'jpeg')
        if req:
            filepath = create_json_filepath(self.session_dir, self.frame_count, angle, throttle, milliseconds)
            f = open(filepath, 'w')
            json.dump(req, f)
            f.close()


    def get(self, file_path):
        '''
        Retrieve an image and the data saved with it.
        '''
        img_arr, data = load_frame(file_path)
        return img_arr, data


    def img_paths(self):
        """
        Returns a list of file paths for the images in the session.
        """
        imgs = img_paths(self.session_dir)
        return imgs


    def img_count(self):
        return len(self.img_paths())


    def load_dataset(self, angle_only=True):
        '''
        Returns image arrays and data arrays.

            X - array of n samples of immage arrays representing.
            Y - array with the shape (samples, 1) containing the
                angle lable for each image

            Where n is the number of recorded images.
        '''
        X, Y = load_dataset(self.img_paths())

        return X, Y




class SessionHandler():
    '''
    Convienience class to create and load sessions.
    '''


    def __init__(self, sessions_path):

        self.sessions_path = os.path.expanduser(sessions_path)


    def new(self, name=None):
        '''
        Create a new session
        '''

        path = self.make_session_dir(self.sessions_path, session_name=name)
        session = Session(path)
        return session


    def load(self, name):
        '''
        Load a session given it's name.
        '''
        path = os.path.join(self.sessions_path, name)
        session = Session(path)
        return session


    def last(self):
        '''
        Return the last created session.
        '''
        dirs = [ name for name in os.listdir(self.sessions_path) if os.path.isdir(os.path.join(self.sessions_path, name)) ]
        dirs.sort()
        path = os.join(self.sessions_path, dirs[-1])
        session = Seession(path)
        return session


    def make_session_dir(self, base_path, session_name=None):
        '''
        Make a new dir with a given name. If name doesn't exist
        use the current date/time.
        '''

        base_path = os.path.expanduser(base_path)
        if session_name is None:
            session_dir_name = time.strftime('%Y_%m_%d__%I_%M_%S_%p')
        else:
            session_dir_name = session_name

        print('Creating a new session directory: %s' %session_dir_name)

        session_full_path = os.path.join(base_path, session_dir_name)
        if not os.path.exists(session_full_path):
            os.makedirs(session_full_path)
        return session_full_path




def img_paths(folder):
    """
    Returns a list of file paths for the images in the session.
    """
    files = os.listdir(folder)
    files = [f for f in files if f[-3:] =='jpg']
    files.sort()
    file_paths = [os.path.join(folder, f) for f in files]
    return file_paths


def load_frame(file_path):
    '''
    Retrieve an image and its telemetry data.
    '''

    with Image.open(file_path) as img:
        img_arr = np.array(img)

    data = dk.sessions.parse_img_filepath(file_path)

    return img_arr, data


def frame_generator(img_paths):
    '''
    Generator that loops through image arrays and their telemetry data.
    '''
    while True:
        for f in img_paths:

            img_arr, data = load_frame(f)

            #return only angle for now
            data_arr = np.array([data['angle'], data['throttle']])
            yield img_arr, data_arr


def batch_generator(img_paths, batch_size=32):
    '''
    Generator that returns batches of X, Y data.
    '''
    frame_gen = frame_generator(img_paths)

    while True:

        X, Y = [], []
        for _ in range(batch_size):
            x, y = next(frame_gen)
            X.append(x)
            Y.append(y)

        X = np.array(X)
        Y = np.array(Y)

        yield X, Y


def load_dataset(img_paths):
    '''
    Returns image arrays and data arrays.

        X - array of n samples of immage arrays representing.
        Y - array with the shape (samples, 1) containing the
            angle lable for each image

        Where n is the number of recorded images.
    '''
    batch_gen = batch_generator(img_paths, batch_size=len(img_paths))
    X, Y = next(batch_gen)
    return X, Y


def sessions_to_dataset(session_names):

    '''
    Combine, pickle and safe session data to a file.

    'sessions_folder' where the session folders reside
    'session_names' the names of the folders of the sessions to Combine
    'file_path' name of the pickled file that will be saved
    '''

    sh = dk.sessions.SessionHandler(dk.config.sessions_path)

    X = []
    Y = []

    for name in session_names:
        s = sh.load(name)
        x, y = s.load_dataset()
        X.append(x)
        Y.append(y)

    X = np.concatenate(X)
    Y = np.concatenate(Y)
    return X, Y


def dataset_to_hdf5(X, Y, file_path):
    print('Saving HDF5 file to %s' %file_path)
    f = h5py.File(file_path, "w")
    f.create_dataset("X", data=X)
    f.create_dataset("Y", data=Y)
    f.close()


def hdf5_to_dataset(file_path):
    f = h5py.File(file_path, "r")
    X = np.array(f['X'])
    Y = np.array(f['Y'])
    return X, Y


def parse_img_filepath(filepath):
    f = filepath.split('/')[-1]
    f = f[:-4] #remove ".jpg"
    f = f.split('_')

    throttle = round(float(f[3]), 2)
    angle = round(float(f[5]), 2)
    milliseconds = round(float(f[7]))

    data = {'throttle':throttle, 'angle':angle, 'milliseconds': milliseconds}

    jn = '/'.join(filepath.split("/")[0:-1]) + '/' + '_'.join(f[0:1]) + ".json"

    if os.path.exists(jn):
        f = open(jn, 'r')
        req = json.load(f)
        f.close()
        data['req'] = req

    return data

def create_img_filepath(directory, frame_count, angle, throttle, milliseconds):
    filepath = str("%s/" % directory +
                "frame_" + str(frame_count).zfill(5) +
                "_ttl_" + str(throttle) +
                "_agl_" + str(angle) +
                "_mil_" + str(milliseconds) +
                '.jpg')
    return filepath

def create_json_filepath(directory, frame_count, angle, throttle, milliseconds):
    filepath = str("%s/" % directory +
                "frame_" + str(frame_count).zfill(5) +
                '.json')
    return filepath




def param_gen(params):
    '''
    Accepts a dictionary of parameter options and returns
    a list of dictionary with the permutations of the parameters.
    '''
    for p in itertools.product(*params.values()):
        yield dict(zip(params.keys(), p ))
