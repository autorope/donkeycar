from io import BytesIO
from PIL import Image
import numpy as np

import envoy

def square(im):
    ''' 
    accepts: PIL image
    returns: the center square of an PIL image
    '''
    
    width, height = im.size
    size = min(height, width)
    width_diff = (width-size)//2
    height_diff = (height-size)//2
    x1 = width_diff
    x2 = width - width_diff
    y1 = height_diff
    y2 = height - height_diff
    im = im.crop((x1, y1, x2, y2))
    return im


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

def binary_to_img(binary):
    '''
    accepts: binary file object from BytesIO
    returns: PIL image
    '''
    img = BytesIO(binary)
    return Image.open(img)


def img_to_greyarr(img):
    '''
    Accepts PIL immage and returns flat greyscale numpy array
    '''
    arr=img.convert('L') #makes it greyscale
    arr=np.asarray(arr.getdata(),dtype=np.float64).reshape((arr.size[1],arr.size[0]))
    arr = arr/255
    return arr


def create_video(img_dir_path, output_video_path):

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


def variant_generator(img_paths, variant_funcs = None):

    if variant_funcs == None:
        variants_funcs = [
             {'func': lambda x: x, 'args': {}},
             {'func': exposure.adjust_sigmoid, 'args': {'cutoff':.4, 'gain':7}}
            ]

    def orient(arr, flip=False):
        if flip == False:
            return arr
        else: 
            return np.fliplr(arr)
    
    while True:
        for flip in [True, False]:
            for v in variants:
                for img_path in img_paths:
                    img = Image.open(img_path)
                    img = np.array(img)
                    img =  v['func'](img, **v['args'])
                    img = orient(img, flip=flip)
                    x = arr.transpose(2, 0, 1)
                    angle, speed = parse_file_name(img_path)
                    if flip == True: 
                        angle = -angle #reverse stering angle
                    y = np.array([angle, speed])
                    x = np.expand_dims(x, axis=0)
                    y = y.reshape(1, 2)
                    yield (x, y)