import random 
import pickle
import math
from io import BytesIO
import os
import glob
import socket

from PIL import Image
import numpy as np

'''
IMAGES
'''

def scale(im, size=128):
    '''
    accepts: PIL image, size of square sides
    returns: PIL image scaled so sides lenght = size 
    '''
    
    size = (size,size)
    im.thumbnail(size, Image.ANTIALIAS)
    return im


def img_to_binary(img):
    '''
    accepts: PIL image
    returns: binary stream (used to save to database)
    '''

    f = BytesIO()
    img.save(f, format='jpeg')
    return f.getvalue()


def arr_to_binary(arr):
    '''
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    '''
    img = arr_to_img(arr)
    return img_to_binary(img)


def arr_to_img(arr):
    '''
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    '''
    arr = np.uint8(arr)
    img = Image.fromarray(arr)
    return img

def img_to_arr(img):
    '''
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    '''
    return np.array(img)


def binary_to_img(binary):
    '''
    accepts: binary file object from BytesIO
    returns: PIL image
    '''
    img = BytesIO(binary)
    return Image.open(img)


def create_video(img_dir_path, output_video_path):
    import envoy
    # Setup path to the images with telemetry.
    full_path = os.path.join(img_dir_path, 'frame_*.png')

    # Run ffmpeg.
    command = ("""ffmpeg
               -framerate 30/1
               -pattern_type glob -i '%s'
               -c:v libx264
               -r 15
               -pix_fmt yuv420p
               -y
               %s""" % (full_path, output_video_path))
    response = envoy.run(command)




'''
DATASETS
'''

def split_data(X, Y, test_frac=.8):
    count = len(X)
    assert len(X) == len(Y)
    
    cutoff = int((count * test_frac) // 1)
    
    X_train = X[:cutoff]
    Y_train = Y[:cutoff]
    
    X_test = X[cutoff:]
    Y_test = Y[cutoff:]
    
    return X_train, Y_train, X_test, Y_test


def split_list(L, sequential=False, test_frac=.8):

    count = len(L)
    cutoff = int((count * test_frac) // 1)
    
    if sequential == False:
        random.shuffle(L)

    L_train = L[:cutoff]
    L_test =  L[cutoff:]

    return L_train, L_test










'''
file utilities
'''


def most_recent_file(dir_path, ext=''):
    '''
    return the most recent file given a directory path and extension
    '''
    query = dir_path + '/*' + ext
    newest = min(glob.iglob(query), key=os.path.getctime)
    return newest


def make_dir(path):
    real_path = os.path.expanduser(path)
    if not os.path.exists(real_path):
        os.makedirs(real_path)
    return real_path


def create_donkey_data(path):
    make_dir(path)

    models_path = os.path.join(path, 'models')
    sessions_path = os.path.join(path, 'sessions')
    make_dir(models_path)
    make_dir(sessions_path)







'''
BINNING
functions to help converte between floating point numbers and categories.
'''

def log_bin(a, has_negative=True):
    """ 
    Returns bin number (between 0 and 14) of a number
    num (between -100 and 100).

    If has_negative == True:  bin range = 0-14
    If has_negative == False: bin range = 0-7 
    
    """
    b = int(round(math.copysign(math.log(abs(a) + 1, 2.0), a)))
    if has_negative: 
        b = b + 7
    return b


def log_unbin(b, has_negative=True):
    if has_negative: 
        b = b - 7
        
    a = math.copysign(2 ** abs(b), b) - 1
    return a


def bin_telemetry(angle, throttle):
    #convert angle between -90 (left) and 90 (right) into a 15 bin array.
    a_arr = np.zeros(15, dtype='float')
    a_arr[log_bin(angle)] = 1
    
    #convert throttle between 0 (stopped) and 100 (full throttle) into a 5 bin array.
    t_arr = np.zeros(7, dtype='float')
    t_arr[log_bin(throttle, has_negative=False)] = 1    
     
    y = np.concatenate([a_arr, t_arr])
    
    #return array containing both angle and throttle bins.
    #y.shape = (15+6)
    return y



def unbin_telemetry(y):
    #convert binned telemetry array to angle and throttle
    a_arr = y[:15]
    t_arr = y[15:]
    
    angle = log_unbin(np.argmax(a_arr)) #not 90 so 0 angle is possible
    print(np.argmax(a_arr))
    throttle = log_unbin(np.argmax(t_arr), has_negative=False)
    
    return angle, throttle





'''
NETWORKING
'''

def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('192.0.0.8', 1027))
    return s.getsockname()[0]


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z