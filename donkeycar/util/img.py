
import random
import io
import os

from PIL import Image
import cv2
import numpy as np
# TODO: put this in its own image_utils file.


'''
IMAGES
'''

def scale(im, size=128):
    '''
    accepts: PIL image, size of square sides
    returns: PIL image scaled so sides length = size
    '''
    size = (size,size)
    im.thumbnail(size, Image.ANTIALIAS)
    return im


def img_to_binary(img):
    '''
    accepts: PIL image
    returns: binary stream (used to save to database)
    '''
    f = io.BytesIO()
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

