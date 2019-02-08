import os
import io
from PIL import Image
import numpy as np
from donkeycar.utils import img_to_binary, binary_to_img, arr_to_img, img_to_arr

class ImgArrToJpg():

    def run(self, img_arr):
        if img_arr is None:
            return None
        try:
            image = arr_to_img(img_arr)
            jpg = img_to_binary(image)
            return jpg
        except:
            return None

class JpgToImgArr():

    def run(self, jpg):
        if jpg is None:
            return None
        image = binary_to_img(jpg)
        img_arr = img_to_arr(image)
        return img_arr

class StereoPair:
    '''
    take two images and put together in a single image
    '''
    def run(self, image_a, image_b):
        '''
        This will take the two images and combine them into a single image
        One in red, the other in green, and diff in blue channel.
        '''
        if image_a is not None and image_b is not None:
            width, height, _ = image_a.shape
            grey_a = dk.utils.rgb2gray(image_a)
            grey_b = dk.utils.rgb2gray(image_b)
            grey_c = grey_a - grey_b
            
            stereo_image = np.zeros([width, height, 3], dtype=np.dtype('B'))
            stereo_image[...,0] = np.reshape(grey_a, (width, height))
            stereo_image[...,1] = np.reshape(grey_b, (width, height))
            stereo_image[...,2] = np.reshape(grey_c, (width, height))
        else:
            stereo_image = []

        return np.array(stereo_image)