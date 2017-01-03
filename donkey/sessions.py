import os
import time
import numpy as np
from PIL import Image
from skimage import exposure

class Session():
    ''' 
    A class to store images and vehicle data to the local filesystem.
    '''
    def __init__(self, path):
        print('Loading Session')
        self.session_dir = path
        self.img_paths = self.get_img_paths()
        self.img_count = len(self.img_paths)
        self.train_cutoff = int( (self.img_count * .8) // 1 )
        print(self.train_cutoff)
        self.train_img_paths = self.img_paths[:self.train_cutoff]
        self.test_img_paths = self.img_paths[self.train_cutoff:]

        self.frame_count = 0



    def get_img_paths(self):
        """ return list of file paths for the images in session """
        files = os.listdir(self.session_dir)
        files = [f for f in files if f[-3:] =='jpg']
        files.sort()
        file_paths = [os.path.join(self.session_dir, f) for f in files]
        return file_paths

    def record(self, img, angle, throttle, milliseconds):
        ''' 
        Save image with encoded angle, throttle and time data in the filename
        '''
        self.frame_count += 1

        file_name = str("%s/" % self.session_dir +
                        "frame_" + str(self.frame_count).zfill(5) +
                        "_ttl_" + str(throttle) +
                        "_agl_" + str(angle) +
                        "_mil_" + str(milliseconds) +
                        '.jpg')

        img.save(file_name, 'jpeg')

    def get_arrays(self):
        '''
        Return two sets of arrays ready to be feed into a Keras Model.

            X - array of n rows of immage arrays representing the 
                image converted to greyscale.  
            Y - array of n rows [angle, throttle]

            Where n is the number of recorded images.
        '''

        gen = self.generator(format=None)

        X = [] #images
        Y = [] #velocity (angle, speed)
        for x, y in gen:
            X.append(x)
            Y.append(y)
            
        X = np.array(X) #image array [[image1],[image2]...]
        Y = np.array(Y) #array [[angle1, speed1],[angle2, speed2] ...]

        return X, Y


    def generator(self, format='keras'):
        ''' Rerturn a generator that will return the image array and throttle variables. ''' 
        
        files = self.img_paths()

        print('files: %s' % len(files))
        while True:
            for f in files:
                img = Image.open(f)
                x = np.array(img)
                y = np.array(self.parse_file_name(f))
                y = y.reshape((1,) + y.shape)
                x = x.transpose(2, 0, 1)
                x = x.reshape((1,) + x.shape)

                yield x, y


    def variant_generator(self, img_paths, variant_funcs):

        def orient(arr, flip=False):
            if flip == False:
                return arr
            else: 
                return np.fliplr(arr)
        
        print(len(img_paths))

        while True:
            for flip in [True, False]:
                for v in variant_funcs:
                    for img_path in img_paths:
                        img = Image.open(img_path)
                        img = np.array(img)
                        img =  v['func'](img, **v['args'])
                        img = orient(img, flip=flip)
                        x = img.transpose(2, 0, 1)
                        angle, speed = self.parse_file_name(img_path)
                        if flip == True: 
                            angle = -angle #reverse stering angle
                        y = np.array([angle, speed])
                        x = np.expand_dims(x, axis=0)
                        y = y.reshape(1, 2)
                        yield x, y

    def training_data_generator(self):
        variant_funcs = [
             {'func': lambda x: x, 'args': {}},
             {'func': exposure.adjust_sigmoid, 'args': {'cutoff':.4, 'gain':7}}
            ]

        return self.variant_generator(self.train_img_paths, variant_funcs)

    def test_data_generator(self):
        variant_funcs = [
             {'func': lambda x: x, 'args': {}}
             ]
        return self.variant_generator(self.test_img_paths, variant_funcs)


    def parse_file_name(self, f):
        f = f.split('/')[-1]
        f = f.split('.')[0]
        f = f.split('_')
        throttle = int(f[3])
        angle = int(f[5])
        #msecs = int(f[7])
        return angle, throttle




class SessionHandler():
    def __init__(self, sessions_path):

        self.sessions_path = os.path.expanduser(sessions_path)
        

    def new(self, name=None):
        path = self.make_session_dir(self.sessions_path, session_name=name)
        session = Session(path)
        return session

    def load(self, name):
        path = os.path.join(self.sessions_path, name)
        session = Session(path)
        return session


    def last(self):
        '''
        return the last created session
        '''
        dirs = [ name for name in os.listdir(self.sessions_path) if os.path.isdir(os.path.join(self.sessions_path, name)) ]
        dirs.sort()
        path = os.join(self.sessions_path, dirs[-1])
        session = Seession(path)
        return session


    def make_session_dir(self, base_path, session_name=None):
        # Make a new dir based on current time
        
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