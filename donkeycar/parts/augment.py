import numpy as np
import random

class Augmentor(object):
    """
    This class provides data augmentation functions
    for enhanced neural network training.
    """
    def __init__(self, X_key='cam/image_array',
                       Y_key='user/angle'):
        self.X_key = X_key
        self.Y_key = Y_key

    def flip_left_right(self, record, probability=0.5):
        """
        Randomly flips an image in the left right direction

        Args:
            record: Record containing the image and the angle

        Returns:
            Flips record with probability self.flip_rate
        """
        if random.uniform(0., 1.) < probability:
            record[self.X_key] = np.fliplr(record[self.X_key])
            record[self.Y_key] = record[self.Y_key] * -1.
        return record

    def random_horizontal_shift(self, record, pixel_range=50, pixel_change=0.01):
        '''
        Shifts the image horizontally

        Args:
            record: Recording containing the image and the steering angle
            pixel_range: By how much the shift can be
            pixel_change: By how much the steering is affected for each pixel shift

        Return:
            shifted record
        '''
        import cv2
        dX = pixel_range * np.random.uniform() - pixel_range / 2
        record[self.Y_key] += dX * pixel_change
        shift = np.float32([[1,0,dX],[0,1,0]])
        record[self.X_key] = cv2.warpAffine(record[self.X_key],
                                            shift,
                                            (record[self.X_key].shape[1],
                                             record[self.X_key].shape[0]))
        return record