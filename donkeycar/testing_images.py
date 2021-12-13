from PIL import Image
import numpy as np
# Open the image form working directory
image = Image.open('0_cam_image_array_.jpg')
# summarize some details about the image
print(image.format)
print(image.size)
print(image.mode)
# show the image
image.show()
img_arr = np.asarray(image)
print(img_arr.shape)
im_trim = img_arr[48:120,...]
Image.fromarray(im_trim).show()
from PIL import Image
import os.path, sys

path = "C:\\Users\\Hans\\mycar\\data\\team_nocontroller\\images"
dirs = os.listdir(path)

def crop():
    for item in dirs:
        fullpath = os.path.join(path,item)         #corrected
        if os.path.isfile(fullpath):
            im = Image.open(fullpath)
            f, e = os.path.splitext(fullpath)
            img_arr = np.asarray(im)
            print(img_arr.shape)
            im_trim = img_arr[55:120,...]
            Image.fromarray(im_trim).show()

crop()