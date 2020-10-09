
from PIL import Image
import numpy as np
from donkeycar.utils import img_to_binary, binary_to_img, arr_to_img, \
    img_to_arr, normalize_image


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


class ImgCrop:
    """
    Crop an image to an area of interest. 
    """
    def __init__(self, top=0, bottom=0, left=0, right=0):
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        
    def run(self, img_arr):
        if img_arr is None:
            return None
        width, height, _ = img_arr.shape
        img_arr = img_arr[self.top:height-self.bottom, 
                          self.left: width-self.right]
        return img_arr

    def shutdown(self):
        pass


class ImgStack:
    """
    Stack N previous images into a single N channel image, after converting
    each to grayscale. The most recent image is the last channel, and pushes
    previous images towards the front.
    """
    def __init__(self, num_channels=3):
        self.img_arr = None
        self.num_channels = num_channels

    def rgb2gray(self, rgb):
        '''
        take a numpy rgb image return a new single channel image converted to
        greyscale
        '''
        return np.dot(rgb[...,:3], [0.299, 0.587, 0.114])
        
    def run(self, img_arr):
        width, height, _ = img_arr.shape        
        gray = self.rgb2gray(img_arr)
        
        if self.img_arr is None:
            self.img_arr = np.zeros([width, height, self.num_channels], dtype=np.dtype('B'))

        for ch in range(self.num_channels - 1):
            self.img_arr[...,ch] = self.img_arr[...,ch+1]

        self.img_arr[...,self.num_channels - 1:] = np.reshape(gray, (width, height, 1))

        return self.img_arr

    def shutdown(self):
        pass
