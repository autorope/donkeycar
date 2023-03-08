import logging
from typing import List
from donkeycar.config import Config
from donkeycar.parts import cv as cv_parts


logger = logging.getLogger(__name__)

class ImageTransformations:
    def __init__(self, config: Config, names: List[str]) -> object:
        """
        Part that constructs a list of image transformers
        and run them in sequence to produce a transformed image
        """
        self.transformations = [image_transformer(name, config) for name in names]
    
    def run(self, image):
        """
        Run the list of tranformers on the image
        and return transformed image.
        """
        for transformer in self.transformations:
            image = transformer.run(image)
        return image


def image_transformer(name:str, config):
    """
    Factory for cv image transformation parts.
    :param name: str, name of the transformation
    :param config: object, the configuration to apply when constructing the part
    :return: object, a cv image transformation part
    """
    #
    # masking transformations
    #
    if "TRAPEZE" == name:
        return cv_parts.ImgTrapezoidalMask(
            config.ROI_TRAPEZE_UL,
            config.ROI_TRAPEZE_UR,
            config.ROI_TRAPEZE_LL,
            config.ROI_TRAPEZE_LR,
            config.ROI_TRAPEZE_MIN_Y,
            config.ROI_TRAPEZE_MAX_Y
        )

    elif "CROP" == name:
        return cv_parts.ImgCropMask(
            config.ROI_CROP_LEFT,
            config.ROI_CROP_TOP,
            config.ROI_CROP_RIGHT,
            config.ROI_CROP_BOTTOM
        )
    #
    # color space transformations
    #
    elif "RGB2BGR" == name:
        return cv_parts.ImgRGB2BGR()
    elif "BGR2RGB" == name:
        return cv_parts.ImgBGR2RGB()
    elif "RGB2HSV" == name:
        return cv_parts.ImgRGB2HSV()
    elif "HSV2RGB" == name:
        return cv_parts.ImgHSV2RGB()
    elif "BGR2HSV" == name:
        return cv_parts.ImgBGR2HSV()
    elif "HSV2BGR" == name:
        return cv_parts.ImgHSV2BGR()
    elif "RGB2GRAY" == name:
        return cv_parts.ImgRGB2GRAY()
    elif "RBGR2GRAY" == name:
        return cv_parts.ImgBGR2GRAY()
    elif "HSV2GRAY" == name:
        return cv_parts.ImgHSV2GRAY()
    elif "GRAY2RGB" == name:
        return cv_parts.ImgGRAY2RGB()
    elif "GRAY2BGR" == name:
        return cv_parts.ImgGRAY2BGR()
    elif "CANNY" == name:
        # canny edge detection
        return cv_parts.ImgCanny(config.CANNY_LOW_THRESHOLD, config.CANNY_HIGH_THRESHOLD, config.CANNY_APERTURE)
    # 
    # blur transformations
    #
    elif "BLUR" == name:
        if config.BLUR_GAUSSIAN:
            return cv_parts.ImgGaussianBlur(config.BLUR_KERNAL, config.BLUR_KERNAL_Y)
        else:
            return cv_parts.ImgSimpleBlur(config.BLUR_KERNAL, config.BLUR_KERNAL_Y)
    # 
    # resize transformations
    #
    elif "RESIZE" == name:
        return cv_parts.ImageResize(config.RESIZE_WIDTH, config.RESIZE_HEIGHT)
    elif "SCALE" == name:
        return cv_parts.ImageScale(config.SCALE_WIDTH, config.SCALE_HEIGHT)
    else:
        msg = f"{name} is not a valid augmentation"
        logger.error(msg)
        raise ValueError(msg)
