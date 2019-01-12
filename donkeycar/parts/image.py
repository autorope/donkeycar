import os
import io
from PIL import Image
import numpy as np
from donkeycar.utils import img_to_binary, binary_to_img, arr_to_img, img_to_arr

class ImgArrToJpg():

    def run(self, img_arr):
        if img_arr is None:
            return None
        image = arr_to_img(img_arr)
        jpg = img_to_binary(image)
        return jpg

class JpgToImgArr():

    def run(self, jpg):
        if jpg is None:
            return None
        image = binary_to_img(jpg)
        img_arr = img_to_arr(image)
        return img_arr
