from io import BytesIO
from PIL import Image

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
    img.save(f, format='png')
    return f.getvalue()

def binary_to_img(binary):
    '''
    accepts: binary file object from BytesIO
    returns: PIL image
    '''
    img = BytesIO(binary)
    return Image.open(img)


