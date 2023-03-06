import cv2
import numpy as np
import logging
from donkeycar.config import Config

logger = logging.getLogger(__name__)

#
# HACK: workaround for imgaug bug; mock our implementation
# TODO: remove this when https://github.com/autorope/donkeycar/issues/970
#       is addressed.
#
try:
    import imgaug.augmenters as iaa
    
    #
# Albumentations https://github.com/albumentations-team/albumentations#a-simple-example
#



    class ImageAugmentation:
        def __init__(self, cfg, key):
            aug_list = getattr(cfg, key, [])
            augmentations = \
                [ImageAugmentation.create(a, cfg) for a in aug_list]
            self.augmentations = iaa.Sequential(augmentations)

        @classmethod
        def create(cls, aug_type: str, config: Config) -> iaa.meta.Augmenter:
            """ Augmenatition factory. Cropping and trapezoidal mask are
                transfomations which should be applied in training, validation
                and inference. Multiply, Blur and similar are augmentations
                which should be used only in training. """

            if aug_type == 'MULTIPLY':
                interval = getattr(config, 'AUG_MULTIPLY_RANGE', (0.5, 1.5))
                logger.info(f'Creating augmentation {aug_type} {interval}')
                return iaa.Multiply(interval)

            elif aug_type == 'BLUR':
                interval = getattr(config, 'AUG_BLUR_RANGE', (0.0, 3.0))
                logger.info(f'Creating augmentation {aug_type} {interval}')
                return iaa.GaussianBlur(sigma=interval)
            else:
                msg = f"{aug_type} is not a valid augmentation"
                logger.error(msg)
                raise ValueError(msg)

        # Parts interface
        def run(self, img_arr):
            aug_img_arr = self.augmentations.augment_image(img_arr)
            return aug_img_arr

except ImportError:

    #
    # mock implementation
    #
    class ImageAugmentation:
        def __init__(self, cfg, key):
            aug_list = getattr(cfg, key, [])
            for aug in aug_list:
                logger.warn(
                    'Augmentation library could not load.  '
                    f'Augmentation {aug} will be ignored')

        def run(self, img_arr):
            return img_arr

class AugmentationAdapter(object):
    """
    Some ready to use image augumentations.
    """
    def __init__(self, part) -> None:
        self.part = part

        def _transform_images(images, random_state, parents, hooks):
            # Transform a batch of images
            transformed = []
            mask = None
            for image in images:
                transformed.append(self.part.run(image))

            return transformed

        def _transform_keypoints(keypoints_on_images, random_state,
                                    parents, hooks):
            # No-op
            return keypoints_on_images

        augmentation = iaa.Lambda(func_images=_transform_images,
                                    func_keypoints=_transform_keypoints)
        return augmentation
