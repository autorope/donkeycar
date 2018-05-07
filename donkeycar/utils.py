'''
utils.py

Functions that don't fit anywhere else.

'''
from io import BytesIO
import os
import glob
import socket
import zipfile
import sys
import itertools
import subprocess
import time

from PIL import Image
import numpy as np

def get_ip_address():
    ip = ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1],
                           [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
                             [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0])
    return ip

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


def norm_img(img):
    return (img - img.mean() / np.std(img))/255.0


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


import random
import cv2
# TODO: put this in its own image_utils file.

def gen_random_rectangle_coords(top, bottom, left, right, min_width, max_width):
    width = int(random.randint(min_width, max_width) / 2)
    height = random.randint(30, 50)
    x_center = random.randint(left, right)
    y_center = random.randint(top, bottom)

    tl = (x_center - width, y_center + height)
    br = (x_center + width, y_center - height)
    return tl, br


def add_rectangle(arr, probability=.2,
                  top=10, bottom=30, left=10, right=150,
                  min_width=10, max_width=30):
    if probability > random.random():
        tl, br = gen_random_rectangle_coords(top, bottom, left, right, min_width, max_width)
        color = tuple(random.choice(range(0, 200)) for i in range(3))
        arr = cv2.rectangle(arr, tl, br, color, -1)
    return arr


def add_rectangles(arr, n=2):
    for _ in range(n):
        arr = add_rectangle(arr, probability=.2)
    return arr


def random_blur(arr, probability=.2, min_kernal_size=2, max_kernal_size=3):
    if probability > random.random():
        kernal_size = random.randint(min_kernal_size, max_kernal_size)
        kernel = np.ones((kernal_size, kernal_size), np.float32) / (kernal_size ** 2)
        arr = cv2.filter2D(arr, -1, kernel)
    return arr


def random_brightness(arr, probability=.1):
    if probability > random.random():
        random_bright = np.random.uniform(.1, 1) + .5
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)  # convert it to hsv
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * random_bright, 0, 255)
        arr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return arr


def augment_images(arr):
    arr = add_rectangles(arr, n=5)
    arr = random_blur(arr, probability=.2, min_kernal_size=2, max_kernal_size=4)
    arr = random_brightness(arr)
    return arr





'''
FILES
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


def zip_dir(dir_path, zip_path):
    """ 
    Create and save a zipfile of a one level directory
    """
    file_paths = glob.glob(dir_path + "/*") #create path to search for files.
    
    zf = zipfile.ZipFile(zip_path, 'w')
    dir_name = os.path.basename(dir_path)
    for p in file_paths:
        file_name = os.path.basename(p)
        zf.write(p, arcname=os.path.join(dir_name, file_name))
    zf.close()
    return zip_path

def time_since_last_file_edited(path):
    """return seconds since last file was updated"""
    list_of_files = glob.glob(os.path.join(path, '*'))
    if len(list_of_files) > 0:
        latest_file = max(list_of_files, key=os.path.getctime)
        return int(time.time() - os.path.getctime(latest_file))
    return 0


'''
BINNING
functions to help converte between floating point numbers and categories.
'''

def linear_bin(a):
    a = a + 1
    b = round(a / (2/14))
    arr = np.zeros(15)
    arr[int(b)] = 1
    return arr


def linear_unbin(arr):
    b = np.argmax(arr)
    a = b * (2/14) - 1
    return a


def bin_Y(Y):
    d = []
    for y in Y:
        arr = np.zeros(15)
        arr[linear_bin(y)] = 1
        d.append(arr)
    return np.array(d) 
        
def unbin_Y(Y):
    d=[]
    for y in Y:
        v = linear_unbin(y)
        d.append(v)
    return np.array(d)

def map_range(x, X_min, X_max, Y_min, Y_max):
    ''' 
    Linear mapping between two ranges of values 
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    y = ((x-X_min) / XY_ratio + Y_min) // 1

    return int(y)



'''
NETWORKING
'''

def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('192.0.0.8', 1027))
    return s.getsockname()[0]




'''
OTHER
'''
def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z



def param_gen(params):
    '''
    Accepts a dictionary of parameter options and returns 
    a list of dictionary with the permutations of the parameters.
    '''
    for p in itertools.product(*params.values()):
        yield dict(zip(params.keys(), p ))


def run_shell_command(cmd, cwd=None, timeout=15):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out = []
    err = []

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill(proc.pid)

    for line in proc.stdout.readlines():
        out.append(line.decode())

    for line in proc.stderr.readlines():
        err.append(line)
    return out, err, proc.pid

'''
def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
'''
import signal

def kill(proc_id):
    os.kill(proc_id, signal.SIGINT)




def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)




def expand_path_mask(path):
    matches = []
    path = os.path.expanduser(path)
    for file in glob.glob(path):
        if os.path.isdir(file):
            matches.append(os.path.join(os.path.abspath(file)))
    return matches


def expand_path_arg(path_str):
    path_list = path_str.split(",")
    expanded_paths = []
    for path in path_list:
        paths = expand_path_mask(path)
        expanded_paths += paths
    return expanded_paths

