import os
import time
import numpy as np
from PIL import Image
from skimage import exposure

class Session():
    ''' 
    Class to store images and vehicle data to the local file system and later retrieve them
    as arrays or generators.
    '''

    def __init__(self, path):
        print('Loading Session')
        self.session_dir = path

        self.frame_count = 0

    def put(self, img, data):
        
        ''' 
        Save image with encoded angle, throttle and time data in the filename
        '''

        throttle =     data['throttle']
        angle =        data['angle']
        milliseconds = data['milliseconds']


        self.frame_count += 1

        file_name = str("%s/" % self.session_dir +
                        "frame_" + str(self.frame_count).zfill(5) +
                        "_ttl_" + str(throttle) +
                        "_agl_" + str(angle) +
                        "_mil_" + str(milliseconds) +
                        '.jpg')

        img.save(file_name, 'jpeg')


    def get(self, file_path):
        ''' 
        Retrieve an image and the data saved with it.
        '''

        with Image.open(file_path) as img:
            img_arr = np.array(img)
        
        
        f = file_path.split('/')[-1]
        f = f.split('.')[0]
        f = f.split('_')

        throttle = int(f[3])
        angle = int(f[5])
        milliseconds = int(f[7])
        
        data = {'throttle':throttle, 'angle':angle, 'milliseconds': milliseconds} 
        
        return img_arr, data


    def img_paths(self):
        """ 
        Returns a list of file paths for the images in the session. 
        """
        files = os.listdir(self.session_dir)
        files = [f for f in files if f[-3:] =='jpg']
        files.sort()
        file_paths = [os.path.join(self.session_dir, f) for f in files]
        return file_paths


    def img_count(self):
        return len(self.img_paths())


    def load_data(self):
        '''
        Returns image arrays and data arrays.

            X - array of n samples of immage arrays representing.  
            Y - array with the shape (samples, 1) containing the 
                angle lable for each image

            Where n is the number of recorded images.
        '''

        gen = self.load_generator()

        X = [] #images
        Y = [] #velocity (angle, speed)
        for _ in range(self.img_count()):
            x, y = next(gen)
            X.append(x)
            Y.append(y)
            
        X = np.array(X) #image array [[image1],[image2]...]
        Y = np.array(Y) #array [[angle1, speed1],[angle2, speed2] ...]

        return X, Y


    def load_generator(self):
        ''' 
        Rerturn a generator that will loops through image arrays and data labels.
        ''' 
        
        files = self.img_paths()

        print('files: %s' % len(files))
        while True:
            for f in files:
                img_arr, data = self.get(f)
                
                #return only angle for now
                y = np.array(data['angle'])
                y = y.reshape((1,) + y.shape)
                x = img_arr.reshape((1,) + img_arr.shape)

                yield x, y


    def variant_generator(self, img_paths, variant_funcs):

        def orient(arr, flip=False):
            if flip == False:
                return arr
            else: 
                return np.fliplr(arr)
        
        print('images before variants %s' % len(img_paths))

        while True:
            for flip in [True, False]:
                for v in variant_funcs:
                    for img_path in img_paths:
                        img = Image.open(img_path)
                        img = np.array(img)
                        img =  v['func'](img, **v['args'])
                        img = orient(img, flip=flip)
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