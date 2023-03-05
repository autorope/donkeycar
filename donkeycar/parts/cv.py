import time
import cv2
import numpy as np
import logging

from donkeycar.parts.camera import CameraError

logger = logging.getLogger(__name__)


class ImgGreyscale:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
            return img_arr
        except:
            logger.error("Unable to convert RGB image to greyscale")
            return None

    def shutdown(self):
        pass


class ImgRGB2GREY(ImgGreyscale):
    pass


class ImgBGR2GREY:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)
            return img_arr
        except:
            logger.error("Unable to convert BGR image to greyscale")
            return None

    def shutdown(self):
        pass

class ImgHSV2GREY:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_HSV2GRAY)
            return img_arr
        except:
            logger.error("Unable to convert HSV image to greyscale")
            return None

    def shutdown(self):
        pass


class ImgWriter:

    def __init__(self, filename):
        self.filename = filename

    def run(self, img_arr):
        cv2.imwrite(self.filename, img_arr)

    def shutdown(self):
        pass


class ImgBGR2RGB:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_BGR2RGB)
            return img_arr
        except:
            logger.error("Unable to convert BGR image to RGB")
            return None

    def shutdown(self):
        pass


class ImgRGB2BGR:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
            return img_arr
        except:
            logger.error("Unable to convert RGB image to BRG")
            return None

    def shutdown(self):
        pass


class ImgHSV2RGB:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_HSV2RGB)
            return img_arr
        except:
            logger.error("Unable to convert HSV image to RGB")
            return None

    def shutdown(self):
        pass


class ImgRGB2HSV:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2HSV)
            return img_arr
        except:
            logger.error("Unable to convert RGB image to HSV")
            return None

    def shutdown(self):
        pass

class ImgHSV2BGR:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_HSV2BGR)
            return img_arr
        except:
            logger.error("Unable to convert HSV image to BGR")
            return None

    def shutdown(self):
        pass


class ImgBGR2HSV:

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_BGR2HSV)
            return img_arr
        except:
            logger.error("Unable to convert BGR image to HSV")
            return None

    def shutdown(self):
        pass


class ImageScale:

    def __init__(self, scale):
        self.scale = scale

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            return cv2.resize(img_arr, (0,0), fx=self.scale, fy=self.scale)
        except:
            logger.error("Unable to resize image")
            return None

    def shutdown(self):
        pass


class ImageRotateBound:
    '''
    credit:
    https://www.pyimagesearch.com/2017/01/02/rotate-images-correctly-with-opencv-and-python/
    '''

    def __init__(self, rot_deg):
        self.rot_deg = rot_deg

    def run(self, image):
        if image is None:
            return None

        # grab the dimensions of the image and then determine the
        # center
        (h, w) = image.shape[:2]
        (cX, cY) = (w // 2, h // 2)
    
        # grab the rotation matrix (applying the negative of the
        # angle to rotate clockwise), then grab the sine and cosine
        # (i.e., the rotation components of the matrix)
        M = cv2.getRotationMatrix2D((cX, cY), -self.rot_deg, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
    
        # compute the new bounding dimensions of the image
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))
    
        # adjust the rotation matrix to take into account translation
        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY
    
        # perform the actual rotation and return the image
        return cv2.warpAffine(image, M, (nW, nH))

    def shutdown(self):
        pass


class ImgCanny:

    def __init__(self, low_threshold=60, high_threshold=110, aperture_size=3, l2gradient=False):
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.aperture_size = aperture_size   # 3, 5 or 7
        self.l2gradient = l2gradient

    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            return cv2.Canny(img_arr,
                             self.low_threshold,
                             self.high_threshold,
                             apertureSize=self.aperture_size,
                             L2gradient=self.l2gradient)
        except:
            logger.error("Unable to apply canny edge detection to image.")
            return None

    def shutdown(self):
        pass
    

class ImgGaussianBlur:

    def __init__(self, kernal_size=5, kernal_y=None):
        self.kernal_size = (kernal_size, kernal_y if kernal_y is not None else kernal_size)
        
    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            return cv2.GaussianBlur(img_arr,
                                    self.kernal_size, 
                                    0)
        except:
            logger.error("Unable to apply gaussian blur to image.")
            return None

    def shutdown(self):
        pass


class ImgSimpleBlur:

    def __init__(self, kernal_size=5, kernal_y=None):
        self.kernal_size = (kernal_size, kernal_y if kernal_y is not None else kernal_size)
        
    def run(self, img_arr):
        if img_arr is None:
            return None

        try:
            return cv2.blur(img_arr, self.kernal_size)
        except:
            logger.error("Unable to apply simple blur to image.")
            return None

    def shutdown(self):
        pass


class ArrowKeyboardControls:
    '''
    kind of sucky control, only one press active at a time. 
    good enough for a little testing.
    requires that you have an CvImageView open and it has focus.
    '''
    def __init__(self):
        self.left = 2424832
        self.right = 2555904
        self.up = 2490368
        self.down = 2621440
        self.codes = [self.left, self.right, self.down, self.up]
        self.vec = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def run(self):
        code = cv2.waitKeyEx(delay=100)
        for iCode, keyCode in enumerate(self.codes):
            if keyCode == code:
                return self.vec[iCode]
        return 0., 0.


class Pipeline:
    def __init__(self, steps):
        self.steps = steps
    
    def run(self, val):
        for step in self.steps:
            f = step['f']
            args = step['args']
            kwargs = step['kwargs']
            
            val = f(val, *args, **kwargs)
        return val


class CvImgFromFile(object):
    def __init__(self, file_path, image_w=None, image_h=None, image_d=None, copy=False):
        """
        Part to load image from file and output as RGB image
        """
        if file_path is None:
            raise ValueError("CvImage passed empty file_path")

        image = cv2.imread(file_path)
        if image is None:
            raise ValueError(f"CvImage file_path did not resolve to a readable image file: {file_path}")
        
        #
        # resize if there are overrides
        #
        height, width, depth = image.shape
        if (image_h is not None and image_h != height) or (image_w is not None and image_w != width):
            if image_h is not None:
                height = image_h
            if image_w is not None:
                width = image_w
            image = cv2.resize(image, (height, width))

        #
        # change color depth if there are overrides.
        # by default a color image will be loaded as BGR,
        # so make color image into RGB.
        #
        if image_d is not None and image_d != depth:
            if 1 == image_d:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif 3 == image_d:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif 3 == depth:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        self.image = image
        self.copy = copy

    def run(self):
        if self.copy:
            return self.image.copy()
        return self.image




class CvCam(object):
    def __init__(self, image_w=160, image_h=120, image_d=3, iCam=0, warming_secs=5):

        self.frame = None
        self.cap = cv2.VideoCapture(iCam)

        # warm up until we get a frame or we timeout
        if self.cap is not None:
            self.cap.set(3, image_w)
            self.cap.set(4, image_h)

            logger.info('CvCam opened...')
            warming_time = time.time() + warming_secs  # quick after 5 seconds
            while self.frame is None and time.time() < warming_time:
                logger.info("...warming camera")
                self.run()
                time.sleep(0.2)

            if self.frame is None:
                raise CameraError("Unable to start CvCam.")
        else:
            raise CameraError("Unable to open CvCam.")

        self.running = True
        logger.info("CvCam ready.")


    def poll(self):
        if self.cap.isOpened():
            _, self.frame = self.cap.read()

    def update(self):
        '''
        poll the camera for a frame
        '''
        while self.running:
            self.poll()

    def run_threaded(self):
        return self.frame

    def run(self):
        self.poll()
        return self.frame

    def shutdown(self):
        self.running = False
        time.sleep(0.2)
        self.cap.release()


class CvImageView(object):

    def run(self, image):
        if image is None:
            return

        try:
            cv2.imshow('frame', image)
            cv2.waitKey(1)
        except:
            logger.error("Unable to open image window.")

    def shutdown(self):
        cv2.destroyAllWindows()


class ImgTrapezoidalMask:
    def __init__(self, left, right, bottom_left, bottom_right, top, bottom, fill=[255,255,255]) -> None:
        """
        Apply a trapezoidal mask to an image, keeping image in
        the trapezoid and turns everything else the fill color
        """
        self.bottom_left = bottom_left
        self.bottom_right = bottom_right
        self.top_left = left
        self.top_right = right
        self.top = top
        self.bottom = bottom
        self.fill = fill
        self.masks = {}


    def run(self, image):
        """
        Apply trapezoidal mask
        # # # # # # # # # # # # #
        # xxxxxxxxxxxxxxxxxxxxxxx
        # xxxx ul     ur xxxxxxxx min_y
        # xxx             xxxxxxx
        # xx               xxxxxx
        # x                 xxxxx
        # ll                lr xx max_y
        """
        transformed = None
        if image is not None:
            mask = None
            key = str(image.shape)
            if self.masks.get(key) is None:
                mask = np.zeros(image.shape, dtype=np.int32)
                points = [
                    [self.top_left, self.top],
                    [self.top_right, self.top],
                    [self.bottom_right, self.bottom],
                    [self.bottom_left, self.bottom]
                ]
                cv2.fillConvexPoly(mask,
                                    np.array(points, dtype=np.int32),
                                    self.fill)
                mask = np.asarray(mask, dtype='bool')
                self.masks[key] = mask

            mask = self.masks[key]
            transformed = np.multiply(image, mask)

        return transformed
    
    def shutdown(self):
        self.masks = {}  # free cached masks


class ImgCropMask:
    def __init__(self, top=None, bottom=None, fill=[255, 255, 255]) -> None:
        """
        Apply a mask to top and/or bottom of image.
        """
        self.top = top
        self.bottom = bottom
        self.fill = fill
        self.masks = {}

    def run(self, image):
        """
        Apply top and/or bottom mask
        # # # # # # # # # # # # #
        # xxxxxxxxxxxxxxxxxxxxxxx       
        # xxxxxxxxxxxxxxxxxxxxxxx       
        #                        top
        #
        #
        # xxxxxxxxxxxxxxxxxxxxxx bottom
        # xxxxxxxxxxxxxxxxxxxxxx
        # # # # # # # # # # # # #
        """
        transformed = None
        if image is not None:
            mask = None
            key = str(image.shape)
            if self.masks.get(key) is None:
                height, width, depth = image.shape
                top = self.top if self.top is not None else 0
                bottom = self.bottom if self.bottom is not None else height
                mask = np.zeros(image.shape, dtype=np.int32)
                points = [
                    [0, top],
                    [width, top],
                    [width, bottom],
                    [0, bottom]
                ]
                cv2.fillConvexPoly(mask,
                                    np.array(points, dtype=np.int32),
                                    self.fill)
                mask = np.asarray(mask, dtype='bool')
                self.masks[key] = mask

            mask = self.masks[key]
            transformed = np.multiply(image, mask)

        return transformed

    def shutdown(self):
        self.masks = {}  # free cached masks


if __name__ == "__main__":
    import argparse
    import sys
    
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
    parser.add_argument("-a", "--aug", required=True, type=str.upper, 
                        choices=['CROP', 'TRAPEZE', 
                                 "RGB2HSV", "HSV2RGB", "RGB2BGR", "BGR2RGB", "BGR2HSV", "HSV2BRG", 
                                 "RGB2GREY", "BGR2GREY", "HSV2GREY", 
                                 "CANNY",
                                 "BLUR", "GBLUR"],
                        help = "augmentation to apply")
    parser.add_argument("-l", "--left", type=int, default=0,
                        help="top left horizontal pixel index, defaults to zero")
    parser.add_argument("-lb", "--left-bottom", type=int, default=None,
                    help="bottom, left horizontal pixel index, defaults to zero")
    parser.add_argument("-r", "--right", type=int, default=None,
                        help="top, right horizontal pixel index, defaults to image width")
    parser.add_argument("-rb", "--right-bottom", type=int, default=None,
                    help="bottom, right horizontal pixel index, defaults to image width")
    parser.add_argument("-t", "--top", type=int, default=0,
                        help="top vertical pixel index, defaults to 0")
    parser.add_argument("-b", "--bottom", type=int, default=None,
                    help="bottom vertical pixel index, defaults to image height")
    parser.add_argument("-cl", "--canny-low", type=int, default=60,
                        help="Canny edge detection low threshold value of intensity gradient.")
    parser.add_argument("-ch", "--canny-high", type=int, default=110,
                        help="Canny edge detection high threshold value of intensity gradient.")
    parser.add_argument("-ca", "--canny-aperture", type=int, choices=[3, 5, 7], default=3,
                        help="Canny edge detect aperture in pixels")
    parser.add_argument("-gk", "--guassian-kernal", type=int, choices=[3, 5, 7, 9], default=3,
                        help="Guassian blue kernal size in pixels")
    parser.add_argument("-gky", "--guassian-kernal-y", type=int, choices=[3, 5, 7, 9],
                        help="Guassian blue kernal y size in pixels, defaults to a square kernal")
    parser.add_argument("-bk", "--blur-kernal", type=int, choices=[3, 5, 7, 9], default=3,
                        help="Guassian blue kernal size in pixels")
    parser.add_argument("-bky", "--blur-kernal-y", type=int, choices=[3, 5, 7, 9], 
                        help="Simple blur kernal y size in pixels, defaults to a square kernal")


    #
    # setup augmentations
    #
    transformations = {}

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
        image_source = CvImgFromFile(args.file, image_w=args.width, image_h=args.height, copy=True)
        height, width, depth = image_source.run().shape
    else:
        width = args.width
        height = args.height
        image_source = CvCam(image_w=width, image_h=height, iCam=args.camera)

    #
    # setup augmentations
    #
    left = args.left
    right = args.right if args.right is not None else width
    top = args.top
    bottom = args.bottom if args.bottom is not None else height

    #
    # masking transformations
    #
    transformations["TRAPEZE"] = ImgTrapezoidalMask(
        left,
        right,
        args.left_bottom if args.left_bottom is not None else 0,
        args.right_bottom if args.right_bottom is not None else width,
        args.top,
        args.bottom if args.bottom is not None else height
    )
    transformations["CROP"] = ImgCropMask(top, bottom)

    #
    # color space transformations
    #
    transformations["RGB2BGR"] = ImgRGB2BGR()
    transformations["BGR2RGB"] = ImgBGR2RGB()
    transformations["RGB2HSV"] = ImgRGB2HSV()
    transformations["HSV2RGB"] = ImgHSV2RGB()
    transformations["BGR2HSV"] = ImgBGR2HSV()
    transformations["HSV2BGR"] = ImgHSV2BGR()
    transformations["RGB2GREY"] = ImgRGB2GREY()
    transformations["BRG2GREY"] = ImgBGR2GREY()
    transformations["HSV2GREY"] = ImgHSV2GREY()

    # canny edge detection
    transformations["CANNY"] = ImgCanny(args.canny_low, args.canny_high, args.canny_aperture)

    # blur
    transformations["GBLUR"] = ImgGaussianBlur(args.guassian_kernal, args.guassian_kernal_y)
    transformations["BLUR"] = ImgSimpleBlur(args.blur_kernal, args.blur_kernal_y)

    #
    # lookup the transformation
    #
    transformer = transformations.get(args.aug)
    if transformer is None:
        print("-a/--aug is not a valid augmentation")
        exit()

    
    # Creating a window for later use
    window_name = 'hsv_range_picker'
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

