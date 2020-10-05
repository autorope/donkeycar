import cv2
import numpy as np


class Augumentations(object):
    """
    Some ready to use image augumentations.
    """

    @classmethod
    def crop(cls, left, right, top, bottom, keep_size=False):
        '''
        The image augumentation sequence.
        Crops based on a region of interest among other things.
        left, right, top & bottom are the number of pixels to crop.
        '''
        import imgaug as ia
        import imgaug.augmenters as iaa

        augmentation = iaa.Sequential([
            iaa.Crop(
                px=(top, right, bottom, left),
                keep_size=keep_size
            ),
        ])
        return augmentation

    @classmethod
    def trapezoidal_mask(cls, lower_left, lower_right, upper_left, upper_right, min_y, max_y):
        '''
        Uses a binary mask to generate a trapezoidal region of interest.
        Especially useful in filtering out uninteresting features from an
        input image.
        '''
        import imgaug as ia
        import imgaug.augmenters as iaa

        def _transform_images(images, random_state, parents, hooks):
            # Transform a batch of images
            transformed = []
            mask = None
            for image in images:
                if mask is None:
                    mask = np.zeros(image.shape, dtype='int32')
                    # # # # # # # # # # # # #
                    #       ul     ur          min_y
                    #
                    #
                    #
                    #    ll             lr     max_y
                    points = [
                        [upper_left, min_y],
                        [upper_right, min_y],
                        [lower_right, max_y],
                        [lower_left, max_y]
                    ]
                    cv2.fillConvexPoly(mask, np.array(points, dtype=np.int32), [255, 255, 255])
                    mask = np.asarray(mask, dtype='bool')

                masked = np.multiply(image, mask)
                transformed.append(masked)

            return transformed

        def _transform_keypoints(keypoints_on_images, random_state, parents, hooks):
            # No-op
            return keypoints_on_images

        augmentation = iaa.Sequential([
            iaa.Lambda(func_images=_transform_images, func_keypoints=_transform_keypoints)
        ])

        return augmentation
