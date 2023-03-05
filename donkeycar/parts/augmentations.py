#
# parts that can be used to transform an image
#
import cv2
import numpy as np
import logging
import sys

logger = logging.getLogger(__name__)


class TrapezoidalMask:
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
        #      ul     ur         min_y
        #
        #
        #
        #  ll             lr     max_y
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
    
class CropMask(TrapezoidalMask):
    def __init__(self, top, bottom, fill=[255, 255, 255]) -> None:
        self.top = top
        self.bottom = bottom
        self.fill = fill
        self.masks = {}

    def run(self, image):
        """
        Apply trapezoidal mask
        # # # # # # # # # # # # #
        #      ul     ur         min_y
        #
        #
        #
        #  ll             lr     max_y
        """
        transformed = None
        if image is not None:
            mask = None
            key = str(image.shape)
            if self.masks.get(key) is None:
                height, width, depth = image.shape
                mask = np.zeros(image.shape, dtype=np.int32)
                points = [
                    [0, self.top],
                    [width, self.top],
                    [width, self.bottom],
                    [0, self.bottom]
                ]
                cv2.fillConvexPoly(mask,
                                    np.array(points, dtype=np.int32),
                                    self.fill)
                mask = np.asarray(mask, dtype='bool')
                self.masks[key] = mask

            mask = self.masks[key]
            transformed = np.multiply(image, mask)

        return transformed


if __name__ == "__main__":
    import argparse
    import cv2
    import json
    from threading import Thread
    
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--camera", type=int, default=0,
                        help = "index of camera if using multiple cameras")
    parser.add_argument("-wd", "--width", type=int, default=160,
                        help = "width of image to capture")
    parser.add_argument("-ht", "--height", type=int, default=120,
                        help = "height of image to capture")
    parser.add_argument("-f", "--file", required=True, type=str,
                        help = "path to image file to user rather that a camera")
    parser.add_argument("-a", "--aug", required=True, type=str.upper, choices=['CROP', 'TRAPEZE'],
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


    #
    # setup augmentations
    #
    augmentations = {}

    # Read arguments from command line
    args = parser.parse_args()
    
    file_image = None
    help = []
    if args.file is not None:
        file_image = cv2.imread(args.file)
        if file_image is None:
            help.append(f"-f/--file did not resolve to a readable image file: {args.image}")
    else:
        if args.camera < 0:
            help.append("-c/--camera must be >= 0")
        if args.width < 160:
            help.append("-wd/--width must be >= 160")
        if args.height < 120:
            help.append("-ht/--height must be >= 120")

    if len(help) > 0:
        parser.print_help()
        for h in help:
            print("  " + h)
        sys.exit(1)


    width = None
    height = None
    depth = 3
    if file_image is not None:
        print(str(file_image.shape))
        height, width, depth = file_image.shape
    else:
        width = args.width
        height = args.height


    #
    # setup augmentations
    #
    left = args.left
    right = args.right if args.right is not None else width
    top = args.top
    bottom = args.bottom if args.bottom is not None else height

    augmentations["TRAPEZE"] = TrapezoidalMask(
        left,
        right,
        args.left_bottom if args.left_bottom is not None else 0,
        args.right_bottom if args.right_bottom is not None else width,
        args.top,
        args.bottom if args.bottom is not None else height
    )

    augmentations["CROP"] = CropMask(top, bottom)

    aug = augmentations.get(args.aug)
    if aug is None:
        print("-a/--aug is not a valid augmentation")
        exit()

    cap = None
    if file_image is None:
        cap = cv2.VideoCapture(args.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Creating a window for later use
    window_name = 'hsv_range_picker'
    cv2.namedWindow(window_name)

    while(1):

        frame = None
        if file_image is not None:
            frame = file_image.copy()
        else: 
            _, frame = cap.read()
            if frame is None:
                continue

        #
        # apply the augmentation
        #
        transformed_image = aug.run(frame)

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

    
