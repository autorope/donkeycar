import random
import albumentations.core.transforms_interface
import logging
import albumentations as A
import cv2
import numpy as np
from albumentations import GaussianBlur, RandomGamma, GaussNoise
from albumentations.augmentations import RandomBrightnessContrast
from albumentations.core.transforms_interface import ImageOnlyTransform


from donkeycar.config import Config


logger = logging.getLogger(__name__)


class RandomShadow(ImageOnlyTransform):
    """ Adds one or more randomly shaped, randomly placed shadows to an
        image, so the model sees the kind of partial, irregular shadows
        (trees, buildings, etc.) that cross the lane at different times of
        day. Only the lightness is reduced (via the HLS color space), so hue
        and saturation - and hence the road / lane colors - are preserved,
        rather than the whole image being darkened. """

    def __init__(self,
                num_shadows_range=(1, 2),
                darkness_range=(0.4, 0.7),
                shadow_dimension=5,
                shadow_roi=(0.0, 0.3, 1.0, 1.0),
                blur_ksize=21,
                p=0.5):
        super().__init__(p=p)
        self.num_shadows_range = num_shadows_range
        self.darkness_range = darkness_range
        self.shadow_dimension = shadow_dimension
        self.shadow_roi = shadow_roi
        self.blur_ksize = blur_ksize

    def apply(self, img, **params):
        # Compatibility guard: shadow simulation reduces lightness via the
        # HLS color space, which requires a 3-channel (RGB/BGR) image.
        # Skip (no-op) on grayscale or other channel counts (e.g. if a
        # config sets IMAGE_DEPTH = 1) instead of letting cv2 raise.
        if img.ndim != 3 or img.shape[2] != 3:
            return img

        height, width = img.shape[:2]
        x_min, y_min, x_max, y_max = self.shadow_roi
        roi_x_min, roi_x_max = int(x_min * width), int(x_max * width)
        roi_y_min, roi_y_max = int(y_min * height), int(y_max * height)

        # Build a single 0..1 mask that can hold several shadow shapes.
        # Each shape is a random, irregular polygon (not a rectangle), so
        # shadows look like real cast shadows rather than a hard box.
        mask = np.zeros((height, width), dtype=np.float32)
        num_shadows = random.randint(*self.num_shadows_range)
        for _ in range(num_shadows):
            vertices = np.array(
                [[random.randint(roi_x_min, roi_x_max),
                 random.randint(roi_y_min, roi_y_max)]
                 for _ in range(self.shadow_dimension)], dtype=np.int32)
            darkness = random.uniform(*self.darkness_range)
            polygon_mask = np.zeros((height, width), dtype=np.float32)
            cv2.fillPoly(polygon_mask, [vertices], 1.0)
            mask = np.maximum(mask, polygon_mask * darkness)

        # Blur the mask edges so the shadow fades into the image instead of
        # appearing as a hard-edged cutout.
        if self.blur_ksize and self.blur_ksize > 1:
            k = self.blur_ksize | 1  # cv2 requires an odd kernel size
            mask = cv2.GaussianBlur(mask, (k, k), 0)

        # Reduce lightness only. cv2's RGB<->HLS and BGR<->HLS conversions
        # produce the same L channel (it only depends on per-pixel max/min
        # across channels), and we convert back with the matching HLS2RGB
        # code, so this is correct whether img is in RGB or BGR order.
        orig_dtype = img.dtype
        hls = cv2.cvtColor(img, cv2.COLOR_RGB2HLS).astype(np.float32)
        hls[:, :, 1] *= (1.0 - mask)
        hls = np.clip(hls, 0, 255).astype(np.uint8)
        shadowed = cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)
        return shadowed.astype(orig_dtype)

    def get_transform_init_args_names(self):
        return ('num_shadows_range', 'darkness_range', 'shadow_dimension',
                'shadow_roi', 'blur_ksize')


class ImageAugmentation:
    def __init__(self, cfg, key, prob=0.5):
        aug_list = getattr(cfg, key, [])
        augmentations = [ImageAugmentation.create(a, cfg, prob)
                         for a in aug_list]
        self.augmentations = A.Compose(augmentations)

    @classmethod
    def create(cls, aug_type: str, config: Config, prob) -> \
            albumentations.core.transforms_interface.BasicTransform:
        """ Augmentation factory. Cropping and trapezoidal mask are
            transformations which should be applied in training, validation
            and inference. Multiply, Blur and similar are augmentations
            which should be used only in training. """

        if aug_type == 'BRIGHTNESS':
            b_limit = getattr(config, 'AUG_BRIGHTNESS_RANGE', 0.2)
            # AUG_CONTRAST_RANGE is optional and defaults to the brightness
            # range, so existing configs that only set AUG_BRIGHTNESS_RANGE
            # keep their exact previous behaviour (brightness and contrast
            # limits equal).
            c_limit = getattr(config, 'AUG_CONTRAST_RANGE', b_limit)
            logger.info(f'Creating augmentation {aug_type} '
                       f'brightness={b_limit} contrast={c_limit}')
            return RandomBrightnessContrast(brightness_limit=b_limit,
                                            contrast_limit=c_limit,
                                            p=prob)

        elif aug_type == 'BLUR':
            b_range = getattr(config, 'AUG_BLUR_RANGE', 3)
            logger.info(f'Creating augmentation {aug_type} {b_range}')
            return GaussianBlur(sigma_limit=b_range, blur_limit=(13, 13),
                                p=prob)

        elif aug_type == 'GAMMA':
            # Nonlinear brightness change. gamma_limit is a percentage
            # around 100: values below 100 brighten the image, values above
            # 100 darken it, so a single range like (60, 160) simulates
            # both glare/overexposure and dim/nighttime conditions without
            # needing separate augmentations for each direction.
            gamma_limit = getattr(config, 'AUG_GAMMA_RANGE', (80, 120))
            gamma_prob = getattr(config, 'AUG_GAMMA_PROBABILITY', prob)
            logger.info(f'Creating augmentation {aug_type} {gamma_limit} '
                       f'p={gamma_prob}')
            return RandomGamma(gamma_limit=gamma_limit, p=gamma_prob)

        elif aug_type == 'NOISE':
            # Simulates sensor grain, most noticeable in low-light /
            # nighttime footage. std_range/mean_range are fractions of the
            # image's max pixel value (e.g. 0.1 ~= 10% of 255 for uint8
            # images).
            std_range = getattr(config, 'AUG_NOISE_STD_RANGE', (0.05, 0.15))
            mean_range = getattr(config, 'AUG_NOISE_MEAN_RANGE', (0.0, 0.0))
            noise_prob = getattr(config, 'AUG_NOISE_PROBABILITY', prob)
            logger.info(f'Creating augmentation {aug_type} std={std_range} '
                       f'p={noise_prob}')
            return GaussNoise(std_range=std_range, mean_range=mean_range,
                              p=noise_prob)

        elif aug_type == 'SHADOW':
            shadow_prob = getattr(config, 'AUG_SHADOW_PROBABILITY', prob)
            num_shadows_range = getattr(config, 'AUG_SHADOW_COUNT_RANGE',
                                        (1, 2))
            darkness_range = getattr(config, 'AUG_SHADOW_DARKNESS_RANGE',
                                     (0.4, 0.7))
            shadow_dimension = getattr(config, 'AUG_SHADOW_DIMENSION', 5)
            shadow_roi = getattr(config, 'AUG_SHADOW_ROI',
                                 (0.0, 0.3, 1.0, 1.0))
            blur_ksize = getattr(config, 'AUG_SHADOW_BLUR_KSIZE', 21)
            logger.info(f'Creating augmentation {aug_type} '
                       f'darkness={darkness_range} p={shadow_prob}')
            return RandomShadow(num_shadows_range=num_shadows_range,
                                darkness_range=darkness_range,
                                shadow_dimension=shadow_dimension,
                                shadow_roi=shadow_roi,
                                blur_ksize=blur_ksize,
                                p=shadow_prob)

    # Parts interface
    def run(self, img_arr):
        if len(self.augmentations) == 0:
            return img_arr
        aug_img_arr = self.augmentations(image=img_arr)["image"]
        return aug_img_arr

