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
    elif "TRAPEZE_EDGE" == name:
        return cv_parts.ImgTrapezoidalEdgeMask(
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
    elif "BGR2GRAY" == name:
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
        msg = f"{name} is not a valid transformation"
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


class ImgTransformList:
    """
    A list of image transforms supplied by
    a json file and run in the order and with
    the arguments specified in the json.
    """
    def __init__(self, transforms) -> None:
        self.transforms = transforms

    @staticmethod
    def fromJson(filepath):
        config = load_img_transform_json(filepath)
        transforms = img_transform_list_from_json(config)
        return ImgTransformList(transforms)

    def run(self, image):
        for transform in self.transforms:
            image = transform.run(image)
        return image

    def shutdown(self):
        for transform in self.transforms:
            if callable(getattr(transform, "shutdown", None)):
                transform.shutdown()


def img_transform_from_json(transform_config):
    """
    Construct a single Image transform from given dictionary.
    The dictionary corresponds the the image transform's
    constructor arguments, so it can be passed to the 
    constructor using object destructuring.
    """
    if not isinstance(transform_config, object):
        raise TypeError("transform_config must be a dictionary")
    
    
    #
    # a config is a [string, object] pair
    # where the string specifies the transform
    # and the optional object provides the arguments
    # to it's constructor.
    #
    transformation = transform_config[0]
    args = transform_config[1] if len(transform_config) == 2 else None
    transformer = None

    #
    # masking transformations
    #
    if "TRAPEZE_EDGE" == transformation:
        transformer = cv_parts.ImgTrapezoidalEdgeMask(**args)
    elif 'CROP' == transformation:
        transformer = cv_parts.ImgCropMask(**args)

    #
    # color space transformations
    #
    elif "RGB2BGR" == transformation:
        transformer = cv_parts.ImgRGB2BGR()
    elif "BGR2RGB" == transformation:
        transformer = cv_parts.ImgBGR2RGB()
    elif "RGB2HSV" == transformation:
        transformer = cv_parts.ImgRGB2HSV()
    elif "HSV2RGB" == transformation:
        transformer = cv_parts.ImgHSV2RGB()
    elif "BGR2HSV" == transformation:
        transformer = cv_parts.ImgBGR2HSV()
    elif "HSV2BGR" == transformation:
        transformer = cv_parts.ImgHSV2BGR()
    elif "RGB2GREY" == transformation or "RGB2GRAY" == transformation:
        transformer = cv_parts.ImgRGB2GRAY()
    elif "GREY2RGB" == transformation or "GRAY2RGB" == transformation:
        transformer = cv_parts.ImgGRAY2RGB()
    elif "BGR2GREY" == transformation or "BGR2GRAY" == transformation:
        transformer = cv_parts.ImgBGR2GRAY()
    elif "GREY2BGR" == transformation or "GRAY2BGR" == transformation:
        transformer = cv_parts.ImgGRAY2BGR()
    elif "HSV2GREY" == transformation or "HSV2GRAY" == transformation:
        transformer = cv_parts.ImgHSV2GRAY()
    elif "CANNY" == transformation:
        # canny edge detection
        transformer = cv_parts.ImgCanny(**args)
    # 
    # blur transformations
    #
    elif "GBLUR" == transformation:
        transformer = cv_parts.ImgGaussianBlur(**args)
    elif "BLUR" == transformation:
        transformer = cv_parts.ImgSimpleBlur(**args)
    # 
    # resize transformations
    #
    elif "RESIZE" == transformation:
        transformer = cv_parts.ImageResize(**args)
    elif "SCALE" == transformation:
        transformer = cv_parts.ImageScale(args.scale, args.scale_height)

    #
    # custom transform
    #
    elif transformation.startswith("CUSTOM"):
        transformer = custom_transformer(transformation, args)

    #
    # not a valid transform name
    #
    else:
        msg = f"'{transformation}' is not a valid transformation"
        logger.error(msg)
        raise ValueError(msg)
    
    return transformer


def img_transform_list_from_json(transforms_config):
    """
    Parse one or more Image transforms from given list
    and return an ImgTransformer that applies
    them with the arguments and in the order given
    in the file.

    """
    if not isinstance(transforms_config, list):
        raise TypeError("transforms_config must be a list")
    
    transformers = []
    
    for transform_config in transforms_config:
        transformers.append(img_transform_from_json(transform_config))

    return transformers


def load_img_transform_json(filepath):
    """
    Load a json file that specifies a list with one or more
    image transforms, their order and their arguments.

    The list will contain a series of tuples as a two
    element list. The first element of the tuple is the name 
    of the transform and the second element is a dictionary
    the named arguments for the transform's constructor.
    The named arguments using object destructuring except
    for the custom transform where the dictionary is
    pass as-is without destructuring.

    You can look at the constructor for each image transform
    in cv.py to see what the fields of the argument object in 
    the json should be.  You may leave out an argument if it
    has a default.  

    Here is an example that has one of each transformtion
    specified with all of it's arguments.

    ```
    [
        ["BGR2GRAY"],
        ["BGR2HSV"],
        ["BGR2RGB"],
        ["BLUR", {"kernel_size": 5, "kernel_y": null}],
        ["CANNY", {"low_threshold": 60, "high_threshold": 110, "aperture_size": 3, "l2gradient": false}],
        ["CROP", {"left": 0, "top": 0, "right": 0, "bottom": 0}],
        ["GBLUR", {"kernel_size": 5, "kernel_y": null}],
        ["GRAY2BGR"],
        ["GRAY2RGB"],
        ["HSV2BGR"],
        ["HSV2RGB"],
        ["HSV2GRAY"],
        ["RESIZE", {"width": 160, "height": 120}],
        ["RGB2BGR"],
        ["RGB2GRAY"],
        ["RGB2HSV"],
        ["SCALE", {"scale": 1.0, "scale_height": null}],
        ["TRAPEZE", {"left":0, "right":0, "bottom_left":0, "bottom_right":0, "top":0, "bottom":0, "fill": [255,255,255]}],
        ["TRAPEZE_EDGE", {"upper_left":0, "upper_right":0, "lower_left":0, "lower_right":0, "top":0, "bottom":0, "fill": [255,255,255]}]
    ]
    ```

    """
    import json

    #
    # load and parse the file
    #
    try:
        with open(filepath) as f:
            try:
                data = json.load(f)
                #
                # TODO: validate json data against a schema
                #
                return data
            except e:
                logger.error(f"Can't parse transforms json due to error: {e}")
                raise e
    except OSError as e:
        logger.error(f"Can't open transforms json file '{filepath}' due to error: {e}")
        raise e


if __name__ == "__main__":
    """
    Image transforms self test.
    You provide a json file that specifies a transformation pipeline 
    and configure either an single image to be loaded or a camera to be used.
    The image transformation pipeline is constructed and applied the
    the configured image source and shown in an opencv window.

    This json specifies a pipeline that applies canny edge detection to the image.

    ```
    [
        ["RGB2GRAY"],
        ["BLUR", {}],
        ["CANNY", {}],
        ["CROP", {"left": 0, "top": 45, "right": 0, "bottom": 0}],
        ["GRAY2RGB"]
    ]
    ```

    Here the "BLUR" and "CANNY" transforms are using default parameters, so the 
    argument object is empty.  The "CROP" transform is supplied with a argument object
    that specifies all named parameters and their values.  The color conversion transforms
    "RGB2GRAY" and "GRAY2RGB" do not have arguments so no argument object is supplied.

    If it was in a json file named `canny_pipeline.json` in `pi` home folder the usage would be:

    ```
    cd donkeycar/parts
    python image_transformations.py --width=640 --height=480 --json=/Home/pi/canny_pipeline.json
    ```

    """
    import argparse
    import sys
    import time
    import cv2
    import numpy as np
    import logging

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--camera", type=int, default=0,
                        help = "index of camera if using multiple cameras")
    parser.add_argument("-wd", "--width", type=int, default=160,
                        help = "width of image to capture")
    parser.add_argument("-ht", "--height", type=int, default=120,
                        help = "height of image to capture")
    parser.add_argument("-f", "--file", type=str,
                        help = "path to image file to user rather that a camera")
    parser.add_argument("-js", "--json", type=str,
                        help = "path to json file with list of tranforms")

 
    # Read arguments from command line
    args = parser.parse_args()
    
    image_source = None
    help = []
    if args.file is None:
        if args.camera < 0:
            help.append("-c/--camera must be >= 0")
        if args.width is None or args.width < 160:
            help.append("-wd/--width must be >= 160")
        if args.height is None or args.height < 120:
            help.append("-ht/--height must be >= 120")

    if args.json is None:
        help.append("-js/--json must be supplied to specify the json file with transformers.")


    if len(help) > 0:
        parser.print_help()
        for h in help:
            print("  " + h)
        sys.exit(1)

    #
    # load file OR setup camera
    #
    cap = None
    width = None
    height = None
    depth = 3
    if args.file is not None:
        print(f"Loading image from file `{args.file}`...")
        image_source = cv_parts.CvImgFromFile(args.file, image_w=args.width, image_h=args.height, copy=True)
        height, width, depth = cv_parts.image_shape(image_source.run())
    else:
        print("Initializing camera...")
        width = args.width
        height = args.height
        image_source = cv_parts.CvCam(image_w=width, image_h=height, iCam=args.camera)
    print("done.")

    #
    # read list transformations from json file
    # with fields like:
    #
    # [
    #     ["BGR2GRAY"],
    #     ["BGR2HSV"],
    #     ["BGR2RGB"],
    #     ["BLUR", {"gaussian": false, "kernel": 5, "kernel_y": null}]
    #     ["CANNY", {"low_threshold": 60, "high_threshold": 110, "aperture": 3}]
    #     ["CROP", {"left": 0, "top": 0, "right": 0, "bottom": 0}],
    #     ["GRAY2BGR"],
    #     ["GRAY2RGB"],
    #     ["HSV2BGR"],
    #     ["HSV2RGB"],
    #     ["HSV2GRAY"],
    #     ["RESIZE", {"width": 160, "height": 120}],
    #     ["RGB2BGR"],
    #     ["RGB2GRAY"],
    #     ["RGB2HSV"],
    #     ["SCALE", {"scale_width": 1.0, "scale_height": 1.0}],
    #     ["TRAPEZE", {"upper_left":0, "upper_right":0, "lower_left":0, "lower_right":0, "top":0, "bottom":0}]
    # ]
    #
    print("Loading tranform list from json file `{args.json}`...")
    transformer = ImgTransformList.fromJson(args.json)
    print("done.")

    # Creating a window for later use
    window_name = 'image_tranformer'
    cv2.namedWindow(window_name)

    while(1):

        frame = image_source.run()

        #
        # apply the augmentation
        #
        transformed_image = transformer.run(frame)

        #
        # show augmented image
        #
        cv2.imshow(window_name, transformed_image)

        k = cv2.waitKey(5) & 0xFF
        if k == ord('q') or k == ord('Q'):  # 'Q' or 'q'
            break
    
    if cap is not None:
        cap.release()

    cv2.destroyAllWindows()
