import cv2
import numpy as np
import logging
import imgaug.augmenters as iaa
from donkeycar.config import Config


logger = logging.getLogger(__name__)


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

        def _transform_keypoints(keypoints_on_images, random_state,
                                 parents, hooks):
            # No-op
            return keypoints_on_images

        augmentation = iaa.Lambda(func_images=_transform_images,
                                  func_keypoints=_transform_keypoints)
        return augmentation


class ImageAugmentation:
    def __init__(self, cfg, key):
        aug_list = getattr(cfg, key, [])
        augmentations = [ImageAugmentation.create(a, cfg) for a in aug_list]
        self.augmentations = iaa.Sequential(augmentations)

    @classmethod
    def create(cls, aug_type: str, config: Config) -> iaa.meta.Augmenter:
        """ Augmentation factory. Cropping and trapezoidal mask are
            transformations which should be applied in training, validation and
            inference. Multiply, Blur and similar are augmentations which should
            be used only in training. """

        if aug_type == 'CROP':
            logger.info(f'Creating augmentation {aug_type} with ROI_CROP ' 
                        f'L: {config.ROI_CROP_LEFT}, '
                        f'R: {config.ROI_CROP_RIGHT}, '
                        f'B: {config.ROI_CROP_BOTTOM}, ' 
                        f'T: {config.ROI_CROP_TOP}')

            return Augmentations.crop(left=config.ROI_CROP_LEFT,
                                      right=config.ROI_CROP_RIGHT,
                                      bottom=config.ROI_CROP_BOTTOM,
                                      top=config.ROI_CROP_TOP,
                                      keep_size=True)
        elif aug_type == 'TRAPEZE':
            logger.info(f'Creating augmentation {aug_type}')
            return Augmentations.trapezoidal_mask(
                        lower_left=config.ROI_TRAPEZE_LL,
                        lower_right=config.ROI_TRAPEZE_LR,
                        upper_left=config.ROI_TRAPEZE_UL,
                        upper_right=config.ROI_TRAPEZE_UR,
                        min_y=config.ROI_TRAPEZE_MIN_Y,
                        max_y=config.ROI_TRAPEZE_MAX_Y)

        elif aug_type == 'MULTIPLY':
            interval = getattr(config, 'AUG_MULTIPLY_RANGE', (0.5, 3.0))
            logger.info(f'Creating augmentation {aug_type} {interval}')
            return iaa.Multiply(interval)

        elif aug_type == 'BLUR':
            interval = getattr(config, 'AUG_BLUR_RANGE', (0.0, 3.0))
            logger.info(f'Creating augmentation {aug_type} {interval}')
            return iaa.GaussianBlur(sigma=interval)

    # Parts interface
    def run(self, img_arr):
        aug_img_arr = self.augmentations.augment_image(img_arr)
        return aug_img_arr
