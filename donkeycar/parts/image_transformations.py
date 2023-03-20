import logging
from typing import List
from donkeycar.config import Config
from donkeycar.parts import cv as cv_parts


logger = logging.getLogger(__name__)


class ImageTransformations:
    def __init__(self, config: Config, transformation: str,
                 post_transformation: str = None) -> object:
        """
        Part that constructs a list of image transformers
        and run them in sequence to produce a transformed image
        """
        transformations = getattr(config, transformation, [])
        if post_transformation:
            transformations += getattr(config, post_transformation, [])
        self.transformations = [image_transformer(name, config) for name in
                                transformations]
        logger.info(f'Creating ImageTransformations {transformations}')
    
    def run(self, image):
        """
        Run the list of tranformers on the image
        and return transformed image.
        """
        for transformer in self.transformations:
            image = transformer.run(image)
        return image


def image_transformer(name: str, config):
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
        return cv_parts.ImgCanny(config.CANNY_LOW_THRESHOLD,
                                 config.CANNY_HIGH_THRESHOLD,
                                 config.CANNY_APERTURE)
    # 
    # blur transformations
    #
    elif "BLUR" == name:
        if config.BLUR_GAUSSIAN:
            return cv_parts.ImgGaussianBlur(config.BLUR_KERNEL,
                                            config.BLUR_KERNEL_Y)
        else:
            return cv_parts.ImgSimpleBlur(config.BLUR_KERNEL,
                                          config.BLUR_KERNEL_Y)
    # 
    # resize transformations
    #
    elif "RESIZE" == name:
        return cv_parts.ImageResize(config.RESIZE_WIDTH, config.RESIZE_HEIGHT)
    elif "SCALE" == name:
        return cv_parts.ImageScale(config.SCALE_WIDTH, config.SCALE_HEIGHT)
    elif name.startswith("CUSTOM"):
        return custom_transformer(name, config)
    else:
        msg = f"{name} is not a valid augmentation"
        logger.error(msg)
        raise ValueError(msg)


def custom_transformer(name:str,
                       config:Config,
                       file_path:str=None,
                       class_name:str=None) -> object:
    """
    Instantiate a custom image transformer.  A custome transformer
    is a class whose constructor takes a Config object to get its
    configuration and whose run() method gets an image as an argument
    and returns a transformed image.  Like:
    ```
    class CustomImageTransformer:
        def __init__(self, config:Config):
            #
            # save configuration in instance variables
            #
            self.foo = config.foo  # get configuration

        def run(self, image):
            # 
            # operate on image, then return 
            # the transformed image.
            #
            return image.copy()
    ```

    The name of transformer will begin with "CUSTOM", like "CUSTOM_BLUR".
    There must also be config for the module and the class to instatiate;
    - The name of the module that leads to the python file would be 
      the transformer name with a "_MODULE" suffix, like "CUSTOM_BLUR_MODULE".
    - The name of the class to instantiate would be the transformer name
      with a "_CLASS" suffix, like "CUSTOM_BLUR_CLASS"

    :param name:str name of transformer
    :param config:Config configuration
    :param module_name:str if not None then this is name of the module;
                           otherwise look for the module name in the config
    :param class_name:str if not None then this is the name of the class;
                          otherwise look for the class name in the config
    :return:object instance of the custom transformer.  The run() method
            must take an image and return an image.
    """
    if file_path is None:
        file_path = getattr(config, name + "_MODULE", None)
    if file_path is None:
        raise ValueError(f"No module file path declared for custom image transformer: {name}")
    if class_name is None:
        class_name = getattr(config, name + "_CLASS", None)
    if class_name is None:
        raise ValueError(f"No class declared for custom image transformer: {name}")
    
    import os
    import sys
    import importlib.util
    # specify the module that needs to be
    # imported relative to the path of the
    # module

    #
    # create a module name by pulling out base file name
    # and appending to a custom namespace
    #
    namespace = "custom.transformation." + os.path.split(file_path)[1].split('.')[0]
    module = sys.modules.get(namespace)
    if module:
        # already loaded
        logger.info(f"Found cached custom transformation module: {namespace}")
    else:
        logger.info(f"Loading custom transformation module {namespace} at {file_path}")

        # dynamically load from python file
        spec=importlib.util.spec_from_file_location(namespace, file_path)
        if spec:
            # creates a new module based on spec
            module = importlib.util.module_from_spec(spec)
            if module:
                logger.info(f"Caching custom transformation module {namespace}")
                sys.modules[namespace] = module

                # executes the module in its own namespace
                # when a module is imported or reloaded.
                spec.loader.exec_module(module)
            else:
                logger.error(f"Failed to dynamically load custom transformation module {namespace} at {file_path} from spec")
        else:
            logger.error(f"Failed to dynamically load custom transformation spec {namespace} from {file_path}")

    if module:
        # get the class from the module
        my_class = getattr(module, class_name, None)
        if my_class is None:
            raise ValueError(f"Cannot find class {class_name} in module {namespace} at {file_path}")

        #
        # instantiate the an instance of the class.
        # the __init__() must take a Config object.
        #
        return my_class(config)
    else:
        raise ValueError(f"Unable to load custom tranformation module at {file_path}")

