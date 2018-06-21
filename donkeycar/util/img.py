
import random
import io
import os

from PIL import Image
import numpy as np
# TODO: put this in its own image_utils file.


"""
IMAGES
"""

def scale(im, size=128):
    """
    accepts: PIL image, size of square sides
    returns: PIL image scaled so sides length = size
    """
    size = (size,size)
    im.thumbnail(size, Image.ANTIALIAS)
    return im


def img_to_binary(img):
    """
    accepts: PIL image
    returns: binary stream (used to save to database)
    """
    f = io.BytesIO()
    img.save(f, format='jpeg')
    return f.getvalue()


def arr_to_binary(arr):
    """
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    """
    img = arr_to_img(arr)
    return img_to_binary(img)


def arr_to_img(arr):
    """
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    """
    arr = np.uint8(arr)
    img = Image.fromarray(arr)
    return img

def img_to_arr(img):
    """
    accepts: numpy array with shape (Hight, Width, Channels)
    returns: binary stream (used to save to database)
    """
    return np.array(img)


def binary_to_img(binary):
    """
    accepts: binary file object from BytesIO
    returns: PIL image
    """
    img = io.BytesIO(binary)
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