import settings

import os
import io
import time

'''
Datastore Classes to standardize interface.
'''

class FileRecorder():
    def __init__(self):
        #create new directory for session
        #name folder based on time. 
        

        self.frame_count = 0
        self.session_dir = make_data_folder(settings.DATA_DIR)


    def record(self, img, angle, speed, milliseconds):
        self.frame_count += 1
        '''Save image and ecode variables into file name'''
        file_name = str("%s/" % self.session_dir +
                        "frame_" + str(self.frame_count).zfill(5) +
                        "_spd_" + str(speed) +
                        "_agl_" + str(angle) +
                        "_mil_" + str(milliseconds) +
                        'jpg')

        img.save(file_name, 'jpeg')




def make_data_folder(base_path):
    # Make a new dir to store data.
    base_path = os.path.expanduser(base_path)
    session_dir_name = time.strftime('%Y_%m_%d__%I_%M_%S_%p')
    session_full_path = os.path.join(base_path, session_dir_name)
    if not os.path.exists(session_full_path):
        os.makedirs(session_full_path)
    return session_full_path