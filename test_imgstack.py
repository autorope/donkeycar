import os
import donkeycar as dk
import cv2
from PIL import Image

ist = dk.parts.ImgStack(num_channels=3)
img = cv2.imread(os.path.expanduser('~/Pictures/test1.jpg'))
res = ist.run(img)

img = cv2.imread(os.path.expanduser('~/Pictures/test2.jpg'))
res = ist.run(img)

img = cv2.imread(os.path.expanduser('~/Pictures/test3.jpg'))
res = ist.run(img)

img = cv2.imread(os.path.expanduser('~/Pictures/test1.jpg'))
res = ist.run(img)

img = cv2.imread(os.path.expanduser('~/Pictures/test1.jpg'))
res = ist.run(img)

img = cv2.imread(os.path.expanduser('~/Pictures/test1.jpg'))
res = ist.run(img)

img = Image.fromarray(res)
img.save('test.jpg')

