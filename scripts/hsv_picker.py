#
# Python/opencv script to show an image and then mask it 
# using  low and high HSV values chosen with trackbars
# or sampled from a rectangular select.
# - click on a pixel to show it's position, RGB and HSV values
# - select an area to sample low and high HSV value for an image mask OR
# - adjust the trackbars to choose low and high HSV values for an image mask
# - press Escape to reset the low and high hsv value
# - press 'q' to quit
#
import cv2
import numpy as np



def nothing(x):
    """
    Trackbar callback does nothing
    """
    pass


# 
# Text metrics
#
font = cv2.FONT_HERSHEY_SIMPLEX
line_height = 25  
fontScale = 0.4
text_color = (0, 0, 0)
text_lines = []

frame = None  # the current image frame

def show_pixel_values(image, x, y):
    """
    Create text lines that show the value of the given pixel
    The text lines are used in the main loop to draw text.
    """
    text = []
    if image is not None:
        text.append(f"Pixel at x={x}, y={y}")

        colorsRGB = image[y,x]
        text.append(f"Pixel RGB = ({colorsRGB[0]}, {colorsRGB[1]}, {colorsRGB[2]})")
    
        colorsHSV = bgr_to_hsv(colorsRGB)
        text.append(f"Pixel HSV = ({colorsHSV[0]}, {colorsHSV[1]}, {colorsHSV[2]})")
        
        hsv_low, hsv_high = get_hsv_trackbars()
        if hsv_low is not None and hsv_high is not None:
            text.append(f"Mask HSV Low = ({hsv_low[0]}, {hsv_low[1]}, {hsv_low[2]})")
            text.append(f"Mask HSV High = ({hsv_high[0]}, {hsv_high[1]}, {hsv_high[2]})")
            
    return text


def get_hsv_range(image, left, top, right, bottom):
    if image is None:
        return ((0, 0, 0), (179, 255, 255   ))
        
    min_pixel = None
    max_pixel = None
    width = abs(right - left)
    height = abs(bottom - top)
    if width > 1 and height > 1:
        #
        # get min and max HSV values and put them into the trackbars
        #
        left = min(left, right)
        right = left + width
        top = min(top, bottom)
        bottom = top + height
                
        for y in range(top, bottom):
            for x in range(left, right):
                pixel = bgr_to_hsv(image[y, x])
                if pixel[0] > 0:  # reject black noise pixels
                    min_pixel = pixel if min_pixel is None else np.minimum(pixel, min_pixel)
                    max_pixel = pixel if max_pixel is None else np.maximum(pixel, max_pixel)
        
    return (min_pixel, max_pixel)


# mouse callback variables
drag_rect = None

# mouse callback function
def mouse_callback(event, x, y, flags, param):
    global drag_rect, frame, text_lines
    
    if frame is None:
        return
    
    if event == cv2.EVENT_LBUTTONDOWN: #checks mouse left button down condition
        drag_rect = (x, y, x, y)
        text_lines = show_pixel_values(frame, x, y)
    elif event == cv2.EVENT_MOUSEMOVE:
        if drag_rect is not None:
            drag_rect = (drag_rect[0], drag_rect[1], x, y)
            text_lines = show_pixel_values(frame, x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        if drag_rect is not None:
            width = abs(drag_rect[2] - drag_rect[0])
            height = abs(drag_rect[3] - drag_rect[1])
            if width > 1 and height > 1:
                min_hsv, max_hsv = get_hsv_range(frame, *drag_rect)
                if min_hsv is not None and max_hsv is not None:
                    set_hsv_trackbars(min_hsv, max_hsv)
            text_lines = show_pixel_values(frame, x, y)
        drag_rect = None


def set_hsv_trackbars(hsv_low, hsv_high):
    global window_name
    if hsv_low is not None and hsv_high is not None:
        cv2.setTrackbarPos("h-low", window_name, hsv_low[0])
        cv2.setTrackbarPos("s-low", window_name, hsv_low[1])
        cv2.setTrackbarPos("v-low", window_name, hsv_low[2])
        cv2.setTrackbarPos("h-high", window_name, hsv_high[0])
        cv2.setTrackbarPos("s-high", window_name, hsv_high[1])
        cv2.setTrackbarPos("v-high", window_name, hsv_high[2])


def get_hsv_trackbars():
    global window_name
    h_low = cv2.getTrackbarPos('h-low', window_name)
    s_low = cv2.getTrackbarPos('s-low', window_name)
    v_low = cv2.getTrackbarPos('v-low', window_name)
    h_high = cv2.getTrackbarPos('h-high', window_name)
    s_high = cv2.getTrackbarPos('s-high', window_name)
    v_high = cv2.getTrackbarPos('v-high', window_name)
    return [h_low, s_low, v_low], [h_high, s_high, v_high]

def print_hsv_trackbars():
    (h_low, s_low, v_low), (h_high, s_high, v_high) = get_hsv_trackbars()
    print(f"Low HSV  = ({h_low}, {s_low}, {v_low})")
    print(f"High HSV = ({h_high}, {s_high}, {v_high})")

def bgr_to_hsv(pixelRGB):
    """
    Convert a single RGB pixel to HSV
    """
    imgRGB = np.uint8([[pixelRGB]])  
    imgHSV = cv2.cvtColor(imgRGB, cv2.COLOR_BGR2HSV)
    pixelHSV = imgHSV[0][0]
    return pixelHSV

# Creating a window for later use
window_name = 'hsv_range_picker'

def main(camera_index=0, width=640, height=480, file_image=None):
    global frame, drag_rect, text_lines

    cap = None
    if file_image is None:
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    cv2.namedWindow(window_name)

    # Starting with 100's to prevent error while masking
    h,s,v = 100,255,255

    # Creating track bar for hsv-low value
    cv2.createTrackbar('h-low', window_name, 0, 179, nothing)
    cv2.createTrackbar('s-low', window_name, 0, 255, nothing)
    cv2.createTrackbar('v-low', window_name, 0, 255, nothing)

    # trackbar for hsv high value
    cv2.createTrackbar('h-high', window_name, 179, 179, nothing)
    cv2.createTrackbar('s-high', window_name, 255, 255, nothing)
    cv2.createTrackbar('v-high', window_name, 255, 255, nothing)

    cv2.setMouseCallback(window_name, mouse_callback)

    while(1):

        frame = None
        if file_image is not None:
            frame = file_image.copy()
        else: 
            _, frame = cap.read()
            if frame is None:
                continue
        
        #
        # mask the image using the current HSV value
        #
    
        #converting to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # get info from track bar, create mask and mask the image
        hsv_low, hsv_high = get_hsv_trackbars()

        # Normal masking algorithm
        hsv_low = np.array(hsv_low)
        hsv_high = np.array(hsv_high)
        mask = cv2.inRange(hsv, hsv_low, hsv_high)
        image = cv2.bitwise_and(frame, frame, mask = mask)
        
        # draw drag rectangle
        if drag_rect is not None:
            top_left = (min(drag_rect[0], drag_rect[2]), min(drag_rect[1], drag_rect[3]))
            bottom_right = (max(drag_rect[0], drag_rect[2]), max(drag_rect[1], drag_rect[3]))
            
            # white rectangle with black outline
            image = cv2.rectangle(image, (top_left[0] - 1, top_left[1] - 1), (bottom_right[0] + 1, bottom_right[1] + 1), (0, 0, 0), 1)
            image = cv2.rectangle(image, top_left, bottom_right, (255, 255, 255), 1)
        
        # draw pixel value
        if text_lines:
            x = line_height
            y = line_height
            for line in text_lines:
                # black text with white outline
                image = cv2.putText(image, line, color=(0,0,0), org=(x, y), fontFace=font, fontScale=fontScale, thickness=3)
                image = cv2.putText(image, line, color=(0,255,0), org=(x, y), fontFace=font, fontScale=fontScale, thickness=1)
                y += line_height

        cv2.imshow(window_name, image)

        k = cv2.waitKey(5) & 0xFF
        if k == ord('q') or k == ord('Q'):  # 'Q' or 'q'
            break
        elif k == 27:  # escape
            set_hsv_trackbars((0,0,0), (179,255,255))
            text_lines = []  # clear text
        elif k == ord('p') or k == ord('P'):  # 'P' or 'p'
            # print current HSV range
            print_hsv_trackbars()

    print_hsv_trackbars()
    
    if cap is not None:
        cap.release()

    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--camera", type=int, default=0,
                        help = "index of camera if using multiple cameras")
    parser.add_argument("-wd", "--width", type=int, default=640,
                        help = "width of image to capture")
    parser.add_argument("-ht", "--height", type=int, default=480,
                        help = "height of image to capture")
    parser.add_argument("-f", "--file", type=str,
                        help = "path to image file to user rather that a camera")

    # Read arguments from command line
    args = parser.parse_args()
    
    image = None
    help = []
    if args.file is not None:
        image = cv2.imread(args.file)
        if image is None:
            help.append("-f/--file did not resolve to an image file.")
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
        
    print("- click on a pixel to show it's position, RGB and HSV values")
    print("- select an area to sample low and high HSV value for an image mask OR")
    print("- adjust the trackbars to choose low and high HSV values for an image mask")
    print("- press Escape to reset the low and high hsv value")
    print("- press 'q' to quit")
    
    main(args.camera, args.width, args.height, image)
