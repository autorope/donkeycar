import albumentations.core.transforms_interface
import logging
import albumentations as A
from albumentations import GaussianBlur
from albumentations.augmentations.transforms import RandomBrightnessContrast

from donkeycar.config import Config


logger = logging.getLogger(__name__)


class ImageAugmentation:
    def __init__(self, cfg, key, prob=0.5, always_apply=False):
        aug_list = getattr(cfg, key, [])
        augmentations = [ImageAugmentation.create(a, cfg, prob, always_apply)
                         for a in aug_list]
        self.augmentations = A.Compose(augmentations)

    @classmethod
    def create(cls, aug_type: str, config: Config, prob, always) -> \
            albumentations.core.transforms_interface.BasicTransform:
        """ Augmentation factory. Cropping and trapezoidal mask are
            transformations which should be applied in training, validation
            and inference. Multiply, Blur and similar are augmentations
            which should be used only in training. """

        if aug_type == 'BRIGHTNESS':
            b_limit = getattr(config, 'AUG_BRIGHTNESS_RANGE', 0.2)
            logger.info(f'Creating augmentation {aug_type} {b_limit}')
            return RandomBrightnessContrast(brightness_limit=b_limit,
                                            contrast_limit=b_limit,
                                            p=prob, always_apply=always)

        elif aug_type == 'BLUR':
            b_range = getattr(config, 'AUG_BLUR_RANGE', 3)
            logger.info(f'Creating augmentation {aug_type} {b_range}')
            return GaussianBlur(sigma_limit=b_range, blur_limit=(13, 13),
                                p=prob, always_apply=always)

    # Parts interface
    def run(self, img_arr):
        if len(self.augmentations) == 0:
            return img_arr
        aug_img_arr = self.augmentations(image=img_arr)["image"]
        return aug_img_arr

