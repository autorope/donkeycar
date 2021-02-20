import cv2
import numpy as np
import logging
import imgaug.augmenters as iaa
from donkeycar.config import Config


logger = logging.getLogger()


class Augmentations(object):
    """
    Some ready to use image augumentations.
    """

    @classmethod
    def crop(cls, left, right, top, bottom, keep_size=False):
        """
        The image augumentation sequence.
        Crops based on a region of interest among other things.
        left, right, top & bottom are the number of pixels to crop.
        """
        augmentation = iaa.Crop(px=(top, right, bottom, left),
                                keep_size=keep_size)
        return augmentation

    @classmethod
    def trapezoidal_mask(cls, lower_left, lower_right, upper_left, upper_right,
                         min_y, max_y):
        """
        Uses a binary mask to generate a trapezoidal region of interest.
        Especially useful in filtering out uninteresting features from an
        input image.
        """
        def _transform_images(images, random_state, parents, hooks):
            # Transform a batch of images
            transformed = []
            mask = None
            for image in images:
                if mask is None:
                    mask = np.zeros(image.shape, dtype=np.int32)
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
                    cv2.fillConvexPoly(mask, np.array(points, dtype=np.int32),
                                       [255, 255, 255])
                    mask = np.asarray(mask, dtype='bool')

                masked = np.multiply(image, mask)
                transformed.append(masked)

            return transformed

        def _transform_keypoints(keypoints_on_images, random_state, parents, hooks):
            # No-op
            return keypoints_on_images

        augmentation = iaa.Lambda(func_images=_transform_images,
                                  func_keypoints=_transform_keypoints)
        return augmentation


class ImageAugmentation:
    def __init__(self, cfg):
        aug_list = getattr(cfg, 'AUGMENTATIONS', [])
        augmentations = [ImageAugmentation.create(a, cfg) for a in aug_list]
        self.augmentations = iaa.Sequential(augmentations)

    @classmethod
    def create(cls, aug_type: str, config: Config) -> iaa.meta.Augmenter:
        if aug_type == 'CROP':
            return Augmentations.crop(left=config.ROI_CROP_TOP,
                                      right=config.ROI_CROP_TOP,
                                      bottom=config.ROI_CROP_BOTTOM,
                                      top=config.ROI_CROP_TOP)
        elif aug_type == 'TRAPEZE':
            return Augmentations.trapezoidal_mask(
                        lower_left=config.ROI_TRAPEZE_LL,
                        lower_right=config.ROI_TRAPEZE_LR,
                        upper_left=config.ROI_TRAPEZE_UL,
                        upper_right=config.ROI_TRAPEZE_UR,
                        min_y=config.ROI_TRAPEZE_MIN_Y,
                        max_y=config.ROI_TRAPEZE_MAX_Y)

        elif aug_type == 'MULTIPLY':
            interval = getattr(config, 'AUG_MULTIPLY_RANGE', (0.5, 1.5))
            logger.info(f'Creating augmentation {aug_type} {interval}')
            return iaa.Multiply(interval)

        elif aug_type == 'BLUR':
            interval = getattr(config, 'AUG_BLUR_RANGE', (0.0, 3.0))
            logger.info(f'Creating augmentation {aug_type} {interval}')
            return iaa.GaussianBlur(sigma=interval)

    def augment(self, img_arr):
        aug_img_arr = self.augmentations.augment_image(img_arr)
        return aug_img_arr
