import settings

import os
import io
import time

from PIL import Image
import numpy as np
import utils.image as image_utils

'''
Datastore Classes to standardize interface.
'''

class FileRecorder():
    def __init__(self):

        self.frame_count = 0
        self.session_dir = None


    def record(self, img, angle, speed, milliseconds):
        ''' save image and encode angle, speed and milliseconds into the filename'''

        if session_dir is not None:
            self.frame_count += 1
            '''Save image and ecode variables into file name'''
            file_name = str("%s/" % self.session_dir +
                            "frame_" + str(self.frame_count).zfill(5) +
                            "_spd_" + str(speed) +
                            "_agl_" + str(angle) +
                            "_mil_" + str(milliseconds) +
                            '.jpg')

            img.save(file_name, 'jpeg')
        else:
            self.session_dir = make_data_folder(settings.DATA_DIR)


    def create_array_files(self):

        files = os.listdir(self.session_dir)
        files = [f for f in files if f[-3:] =='jpg']
        files.sort()

        x = [] #images
        y = [] #velocity (angel, speed)
        for f in files:
            img = Image.open(os.path.join(self.session_dir, f))
            img_arr = image_utils.img_to_greyarr(img)
            x.append(img_arr)
            y.append(np.array(self.parse_file_name(f)))
            
        x = np.array(x) #image array [[image1],[image2]...]
        y = np.array(y) #array [[angle1, speed1],[angle2, speed2] ...]

        np.save(os.path.join(self.session_dir, 'img_array'), x, 'imageArray')
        np.save(os.path.join(self.session_dir, 'vel_array'), y, 'velArray')

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



def make_data_folder(base_path):
    # Make a new dir based on current time
    base_path = os.path.expanduser(base_path)
    session_dir_name = time.strftime('%Y_%m_%d__%I_%M_%S_%p')
    session_full_path = os.path.join(base_path, session_dir_name)
    if not os.path.exists(session_full_path):
        os.makedirs(session_full_path)
    return session_full_path