'''
Usage:
    preview_augumentations.py

Note:
    This script helps preview augumentations used when the model is being trained.
'''

import time
from pathlib import Path

import cv2
import imgaug as ia
import imgaug.augmenters as iaa
import numpy as np

from donkeycar.parts.augumentations import Augumentations

# Camera Parameters
WIDTH = 640
HEIGHT = 480

# Example augumentations
cropping = Augumentations.crop(0, 0, 100, 0, keep_size=True)
mask = Augumentations.trapezoidal_mask(10, 630, 100, 300, 50, 480)

def preview_augumentations():
    print('Connecting to Camera')
    capture = cv2.VideoCapture(0)
    time.sleep(2)
    if capture.isOpened():
        print('Camera Connected.')
    else:
        print('Unable to connect. Are you sure you are using the right camera parameters ?')
        return

    while True:
        success, frame = capture.read()
        if success:
            cropped = cropping.augment_image(frame)
            masked = mask.augment_image(frame)
            # Convert to RGB
            cv2.imshow('Preview', frame)
            cv2.imshow('Cropped', cropped)
            cv2.imshow('Trapezoidal Mask', masked)
            prompt = cv2.waitKey(1) & 0xFF
            if prompt == ord(' '):
                # Store output
                pass
            elif prompt == ord('q'):
                break

    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    preview_augumentations()
