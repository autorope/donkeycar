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
import random
import time
import signal
from typing import List, Any, Tuple

from PIL import Image
import numpy as np


'''
IMAGES
'''
ONE_BYTE_SCALE = 1.0 / 255.0


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
    accepts: numpy array with shape (Height, Width, Channels)
    returns: binary stream (used to save to database)
    '''
    arr = np.uint8(arr)
    img = Image.fromarray(arr)
    return img


def img_to_arr(img):
    '''
    accepts: PIL image
    returns: a numpy uint8 image
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
    return (img - img.mean() / np.std(img)) * ONE_BYTE_SCALE


def rgb2gray(rgb):
    """
    Convert normalized numpy image array with shape (w, h, 3) into greyscale
    image of shape (w, h)
    :param rgb:     normalized [0,1] float32 numpy image array or [0,255] uint8
                    numpy image array with shape(w,h,3)
    :return:        normalized [0,1] float32 numpy image array shape(w,h) or
                    [0,255] uint8 numpy array in grey scale
    """
    # this will translate a uint8 array into a float64 one
    grey = np.dot(rgb[..., :3], [0.299, 0.587, 0.114])
    # transform back if the input is a uint8 array
    if rgb.dtype.type is np.uint8:
        grey = round(grey).astype(np.uint8)
    return grey


def img_crop(img_arr, top, bottom):
    if bottom == 0:
        end = img_arr.shape[0]
    else:
        end = -bottom
    return img_arr[top:end, ...]


def normalize_image(img_arr_uint):
    """
    Convert uint8 numpy image array into [0,1] float image array
    :param img_arr_uint:    [0,255]uint8 numpy image array
    :return:                [0,1] float32 numpy image array
    """
    return img_arr_uint.astype(np.float64) * ONE_BYTE_SCALE


def denormalize_image(img_arr_float):
    """
    :param img_arr_float:   [0,1] float numpy image array
    :return:                [0,255]uint8 numpy image array
    """
    return (img_arr_float * 255.0).astype(np.uint8)


def load_pil_image(filename, cfg):
    """Loads an image from a file path as a PIL image. Also handles resizing.

    Args:
        filename (string): path to the image file
        cfg (object): donkey configuration file

    Returns: a PIL image.
    """
    try:
        img = Image.open(filename)
        if img.height != cfg.IMAGE_H or img.width != cfg.IMAGE_W:
            img = img.resize((cfg.IMAGE_W, cfg.IMAGE_H))

        if cfg.IMAGE_DEPTH == 1:
            img = img.convert('L')
        
        return img

    except Exception as e:
        print(e)
        print('failed to load image:', filename)
        return None


def load_image(filename, cfg):
    """
    :param string filename:     path to image file
    :param cfg:                 donkey config
    :return np.ndarray:         numpy uint8 image array
    """
    img = load_pil_image(filename, cfg)

    if not img:
        return None

    img_arr = np.asarray(img)

    # If the PIL image is greyscale, the np array will have shape (H, W)
    # Need to add a depth channel by expanding to (H, W, 1)
    if img.mode == 'L':
        h, w = img_arr.shape[:2]
        img_arr = img_arr.reshape(h, w, 1)

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
    b = round(a / (R / (N - offset)))
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
    a = b * (R / (N + offset)) + offset
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


def map_range_float(x, X_min, X_max, Y_min, Y_max):
    '''
    Same as map_range but supports floats return, rounded to 2 decimal places
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    y = ((x-X_min) / XY_ratio + Y_min)

    # print("y= {}".format(y))

    return round(y,2)

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
THROTTLE
'''

STEERING_MIN = -1.
STEERING_MAX = 1.
# Scale throttle ~ 0.5 - 1.0 depending on the steering angle
EXP_SCALING_FACTOR = 0.5
DAMPENING = 0.05


def _steering(input_value):
    input_value = clamp(input_value, STEERING_MIN, STEERING_MAX)
    return ((input_value - STEERING_MIN) / (STEERING_MAX - STEERING_MIN))


def throttle(input_value):
    magnitude = _steering(input_value)
    decay = math.exp(magnitude * EXP_SCALING_FACTOR)
    dampening = DAMPENING * magnitude
    return ((1 / decay) - dampening)

'''
OTHER
'''


def map_frange(x, X_min, X_max, Y_min, Y_max):
    '''
    Linear mapping between two ranges of values
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range/Y_range

    y = ((x-X_min) / XY_ratio + Y_min)

    return y


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


def kill(proc_id):
    os.kill(proc_id, signal.SIGINT)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_model_by_type(model_type: str, cfg: 'Config') -> 'KerasPilot':
    '''
    given the string model_type and the configuration settings in cfg
    create a Keras model and return it.
    '''
    from donkeycar.parts.keras import KerasPilot, KerasCategorical, \
        KerasLinear, KerasInferred
    from donkeycar.parts.tflite import TFLitePilot

    if model_type is None:
        model_type = cfg.DEFAULT_MODEL_TYPE
    print("\"get_model_by_type\" model Type is: {}".format(model_type))

    input_shape = (cfg.IMAGE_H, cfg.IMAGE_W, cfg.IMAGE_DEPTH)
    kl: KerasPilot
    if model_type == "linear":
        kl = KerasLinear(input_shape=input_shape)
    elif model_type == "categorical":
        kl = KerasCategorical(input_shape=input_shape,
                              throttle_range=cfg.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE)
    elif model_type == 'inferred':
        kl = KerasInferred(input_shape=input_shape)
    elif model_type == "tflite_linear":
        kl = TFLitePilot()
    elif model_type == "tensorrt_linear":
        # Aggressively lazy load this. This module imports pycuda.autoinit
        # which causes a lot of unexpected things to happen when using TF-GPU
        # for training.
        from donkeycar.parts.tensorrt import TensorRTLinear
        kl = TensorRTLinear(cfg=cfg)
    else:
        raise Exception("Unknown model type {:}, supported types are "
                        "linear, categorical, inferred, tflite_linear, "
                        "tensorrt_linear"
                        .format(model_type))

    return kl


def get_test_img(model):
    """
    query the input to see what it likes make an image capable of using with
    that test model
    :param model:                   input keras model
    :return np.ndarry(np.uint8):    numpy random img array
    """
    assert(len(model.inputs) > 0)
    try:
        count, h, w, ch = model.inputs[0].get_shape()
        seq_len = 0
    except Exception as e:
        count, seq_len, h, w, ch = model.inputs[0].get_shape()

    # generate random array in the right shape
    img = np.random.randint(0, 255, size=(h, w, ch))
    return img.astype(np.uint8)


def train_test_split(data_list: List[Any],
                     shuffle: bool = True,
                     test_size: float = 0.2) -> Tuple[List[Any], List[Any]]:
    '''
    take a list, split it into two sets while selecting a
    random element in order to shuffle the results.
    use the test_size to choose the split percent.
    shuffle is always True, left there to be backwards compatible
    '''
    target_train_size = int(len(data_list) * (1. - test_size))

    if shuffle:
        train_data = []
        i_sample = 0
        while i_sample < target_train_size and len(data_list) > 1:
            i_choice = random.randint(0, len(data_list) - 1)
            train_data.append(data_list.pop(i_choice))
            i_sample += 1

        # remainder of the original list is the validation set
        val_data = data_list

    else:
        train_data = data_list[:target_train_size]
        val_data = data_list[target_train_size:]

    return train_data, val_data


"""
Timers
"""


class FPSTimer(object):
    def __init__(self):
        self.t = time.time()
        self.iter = 0

    def reset(self):
        self.t = time.time()
        self.iter = 0

    def on_frame(self):
        self.iter += 1
        if self.iter == 100:
            e = time.time()
            print('fps', 100.0 / (e - self.t))
            self.t = time.time()
            self.iter = 0
