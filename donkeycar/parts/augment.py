import time
import numpy as np
from donkeycar.pipeline.augmentations import ImageAugmentation
from donkeycar.config import Config


class ImageAugmentationPart:
    """ Image augmentation as part for the vehicle"""
    def __init__(self, cfg: Config, delay: float = 0.002) -> None:
        """
        :param cfg:     donkey config
        :param delay:   time spent in threaded part, if augmentation takes
                        longer, the last augmented image will be delivered
        """
        self.augmenter = ImageAugmentation(cfg)
        self.img_arr = None
        self.aug_img_arr = None
        self.delay = delay
        self.on = True

    def run(self, img_arr: np.ndarray) -> np.ndarray:
        return self.augmenter.augment(img_arr)

    def update(self) -> None:
        while self.on:
            if self.img_arr is not None:
                self.aug_img_arr = self.augmenter.augment(self.img_arr)
                self.img_arr = None

    def run_threaded(self, img_arr: np.ndarray) -> np.ndarray:
        self.img_arr = img_arr
        time.sleep(self.delay)
        return self.aug_img_arr

    def shutdown(self) -> None:
        self.on = False
