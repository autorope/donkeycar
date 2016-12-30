import os
import io
import time

from PIL import Image
import numpy as np
from .utils import image_utils

'''
Recorders provide a consistent way to save and retrieve driving data. 
'''

class FileRecorder():
    ''' 
    A class to store images and vehicle data to the local filesystem.
    '''
    def __init__(self, session=None, sessions_dir=None):
        print('Loading FileRecorder')
        
        print('Starting Session: %s' %session)
        self.session_dir = make_session_dir(sessions_dir,
                                            session_name=session)

        #TODO: this frame count should start at the last frame number
        self.frame_count = 0

    def record(self, img, angle, speed, milliseconds):
        ''' 
        Save image with encoded angle, speed and time data in the filename
        '''
        self.frame_count += 1
        '''Save image and ecode variables into file name'''
        file_name = str("%s/" % self.session_dir +
                        "frame_" + str(self.frame_count).zfill(5) +
                        "_spd_" + str(speed) +
                        "_agl_" + str(angle) +
                        "_mil_" + str(milliseconds) +
                        '.jpg')

        img.save(file_name, 'jpeg')

    def get_arrays(self):
        '''
        Return two sets of arrays ready to be feed into a Keras Model.

            X - array of n rows of immage arrays representing the 
                image converted to greyscale.  
            Y - array of n rows [angle, speed]

            Where n is the number of recorded images.
        '''
        files = os.listdir(self.session_dir)
        files = [f for f in files if f[-3:] =='jpg']
        files.sort()

        X = [] #images
        Y = [] #velocity (angle, speed)
        for f in files:
            img = Image.open(os.path.join(self.session_dir, f))
            #img_arr = image_utils.img_to_greyarr(img)
            img_arr = np.array(img)
            X.append(img_arr)
            Y.append(np.array(self.parse_file_name(f)))
            
        X = np.array(X) #image array [[image1],[image2]...]
        Y = np.array(Y) #array [[angle1, speed1],[angle2, speed2] ...]

        return X, Y


    def parse_file_name(self, f):
        f = f.split('.')[0]
        f = f.split('_')
        speed = int(f[3])
        angle = int(f[5])
        #msecs = int(f[7])
        return angle, speed

    def use_last_session(self):
        ''' set the session dir to the last created data directory'''
        base_path = os.path.expanduser(settings.DATA_DIR)
        dirs = [ name for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name)) ]
        dirs.sort()
        self.session_dir = base_path + dirs[-1]



def make_session_dir(base_path, session_name=None):
    # Make a new dir based on current time
    
    print('Creating a new session directory: %s' %session_name)
    base_path = os.path.expanduser(base_path)
    if session_name is None:
        session_dir_name = time.strftime('%Y_%m_%d__%I_%M_%S_%p')
    else:
        session_dir_name = session_name

    session_full_path = os.path.join(base_path, session_dir_name)
    if not os.path.exists(session_full_path):
        os.makedirs(session_full_path)
    return session_full_path
