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
import math

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


def img_to_binary(img, format='jpeg'):
    '''
    accepts: PIL image
    returns: binary stream (used to save to database)
    '''
    f = BytesIO()
    try:
        img.save(f, format=format)
    except Exception as e:
        raise e
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
    if binary is None or len(binary) == 0:
        return None

    img = BytesIO(binary)
    try:
        img = Image.open(img)
        return img
    except:
        return None


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


def rgb2gray(rgb):
    '''
    take a numpy rgb image return a new single channel image converted to greyscale
    '''
    return np.dot(rgb[...,:3], [0.299, 0.587, 0.114])


def load_scaled_image_arr(filename, cfg):
    '''
    load an image from the filename, and use the cfg to resize if needed
    '''
    import donkeycar as dk
    try:
        img = Image.open(filename)
        if img.height != cfg.IMAGE_H or img.width != cfg.IMAGE_W:
            img = img.resize((cfg.IMAGE_W, cfg.IMAGE_H))
        img_arr = np.array(img)
        if img_arr.shape[2] == 3 and cfg.IMAGE_DEPTH == 1:
            img_arr = dk.utils.rgb2gray(img_arr).reshape(cfg.IMAGE_H, cfg.IMAGE_W, 1)
    except:
        print('failed to load image:', filename)
        img_arr = None
    return img_arr


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




'''
BINNING
functions to help converte between floating point numbers and categories.
'''

def clamp(n, min, max):
    if n < min:
        return min
    if n > max:
        return max
    return n

def linear_bin(a, N=15, offset=1, R=2.0):
    '''
    create a bin of length N
    map val A to range R
    offset one hot bin by offset, commonly R/2
    '''
    a = a + offset
    b = round(a / (R/(N-offset)))
    arr = np.zeros(N)
    b = clamp(b, 0, N - 1)
    arr[int(b)] = 1
    return arr


def linear_unbin(arr, N=15, offset=-1, R=2.0):
    '''
    preform inverse linear_bin, taking
    one hot encoded arr, and get max value
    rescale given R range and offset
    '''
    b = np.argmax(arr)
    a = b *(R/(N + offset)) + offset
    return a


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
ANGLES
'''
def norm_deg(theta):
    while theta > 360:
        theta -= 360
    while theta < 0:
        theta += 360
    return theta

DEG_TO_RAD = math.pi / 180.0

def deg2rad(theta):
    return theta * DEG_TO_RAD

'''
VECTORS
'''
def dist(x1, y1, x2, y2):
    return math.sqrt(math.pow(x2 - x1, 2) + math.pow(y2 - y1, 2))


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


"""
Tub management
"""

def expand_path_masks(paths):
    '''
    take a list of paths and expand any wildcards
    returns a new list of paths fully expanded
    '''
    import glob
    expanded_paths = []
    for path in paths:
        if '*' in path or '?' in path:
            mask_paths = glob.glob(path)
            expanded_paths += mask_paths
        else:
            expanded_paths.append(path)

    return expanded_paths


def gather_tub_paths(cfg, tub_names=None):
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub paths
    '''
    if tub_names:
        if type(tub_names) == list:
            tub_paths = [os.path.expanduser(n) for n in tub_names]
        else:
            tub_paths = [os.path.expanduser(n) for n in tub_names.split(',')]
        return expand_path_masks(tub_paths)
    else:
        paths = [os.path.join(cfg.DATA_PATH, n) for n in os.listdir(cfg.DATA_PATH)]
        dir_paths = []
        for p in paths:
            if os.path.isdir(p):
                dir_paths.append(p)
        return dir_paths


def gather_tubs(cfg, tub_names):    
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub objects initialized to each path
    '''
    from donkeycar.parts.datastore import Tub
    
    tub_paths = gather_tub_paths(cfg, tub_names)
    tubs = [Tub(p) for p in tub_paths]

    return tubs

def get_image_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[0])


def get_record_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[1].split('.')[0])

def gather_records(cfg, tub_names, opts=None, verbose=False):

    tubs = gather_tubs(cfg, tub_names)

    records = []

    for tub in tubs:
        if verbose:
            print(tub.path)
        record_paths = tub.gather_records()
        records += record_paths

    return records

def get_model_by_type(model_type, cfg):
    '''
    given the string model_type and the configuration settings in cfg
    create a Keras model and return it.
    '''
    from donkeycar.parts.keras import KerasRNN_LSTM, KerasBehavioral, KerasCategorical, KerasIMU, KerasLinear, Keras3D_CNN, KerasLocalizer, KerasLatent
 
    if model_type is None:
        model_type = cfg.DEFAULT_MODEL_TYPE

    input_shape = (cfg.IMAGE_H, cfg.IMAGE_W, cfg.IMAGE_DEPTH)
    roi_crop = (cfg.ROI_CROP_TOP, cfg.ROI_CROP_BOTTOM)

    if model_type == "localizer" or cfg.TRAIN_LOCALIZER:
        kl = KerasLocalizer(num_outputs=2, num_behavior_inputs=len(cfg.BEHAVIOR_LIST), num_locations=cfg.NUM_LOCATIONS, input_shape=input_shape)
    elif model_type == "behavior" or cfg.TRAIN_BEHAVIORS:
        kl = KerasBehavioral(num_outputs=2, num_behavior_inputs=len(cfg.BEHAVIOR_LIST), input_shape=input_shape)        
    elif model_type == "imu":
        kl = KerasIMU(num_outputs=2, num_imu_inputs=6, input_shape=input_shape)        
    elif model_type == "linear":
        kl = KerasLinear(input_shape=input_shape, roi_crop=roi_crop)
    elif model_type == "3d":
        kl = Keras3D_CNN(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, seq_length=cfg.SEQUENCE_LENGTH)
    elif model_type == "rnn":
        kl = KerasRNN_LSTM(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, seq_length=cfg.SEQUENCE_LENGTH)
    elif model_type == "categorical":
        kl = KerasCategorical(input_shape=input_shape, throttle_range=cfg.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE, roi_crop=roi_crop)
    elif model_type == "latent":
        kl = KerasLatent(input_shape=input_shape)
    else:
        raise Exception("unknown model type: %s" % model_type)

    return kl

def get_test_img(model):
    '''
    query the input to see what it likes
    make an image capable of using with that test model
    '''
    try:
        count, h, w, ch = model.inputs[0].get_shape()
        seq_len = 0
    except:
        count, seq_len, h, w, ch = model.inputs[0].get_shape()

    #generate random array in the right shape
    img = np.random.rand(int(h), int(w), int(ch))

    return img


