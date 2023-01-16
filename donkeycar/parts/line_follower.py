import cv2
import numpy as np
from simple_pid import PID


class LineFollower:
    '''
    OpenCV based controller
    This controller takes a horizontal slice of the image at a set Y coordinate.
    Then it converts to HSV and does a color thresh hold to find the yellow pixels.
    It does a histogram to find the pixel of maximum yellow. Then is uses that iPxel
    to guid a PID controller which seeks to maintain the max yellow at the same point
    in the image.
    '''
    def __init__(self, overlay_image=True, debug=False):
        self.debug = debug
        self.overlay_image = overlay_image
        self.scan_y = 60   # num pixels from the top to start horiz scan
        self.scan_height = 10 # num pixels high to grab from horiz scan
        self.color_thr_low = np.asarray((0, 50, 50)) # hsv dark yellow
        self.color_thr_hi = np.asarray((50, 255, 255)) # hsv light yellow
        self.target_pixel = None # of the N slots above, which is the ideal relationship target
        self.steering = 0.0 # from -1 to 1
        self.throttle = 0.15 # from -1 to 1
        self.recording = False # Set to true if desired to save camera frames
        self.delta_th = 0.1 # how much to change throttle when off
        self.throttle_max = 0.3
        self.throttle_min = 0.15

        # These three PID constants are crucial to the way the car drives. If you are tuning them
        # start by setting the others zero and focus on first Kp, then Kd, and then Ki.
        self.pid_st = PID(Kp=-0.01, Ki=0.00, Kd=-0.001)


    def get_i_color(self, cam_img):
        '''
        get the horizontal index of the color at the given slice of the image
        input: cam_image, an RGB numpy array
        output: index of max color, value of cumulative color at that index, and mask of pixels in range
        '''
        # take a horizontal slice of the image
        iSlice = self.scan_y
        scan_line = cam_img[iSlice : iSlice + self.scan_height, :, :]

        # convert to HSV color space
        img_hsv = cv2.cvtColor(scan_line, cv2.COLOR_RGB2HSV)

        # make a mask of the colors in our range we are looking for
        mask = cv2.inRange(img_hsv, self.color_thr_low, self.color_thr_hi)

        # which index of the range has the highest amount of yellow?
        hist = np.sum(mask, axis=0)
        max_yellow = np.argmax(hist)

        return max_yellow, hist[max_yellow], mask


    def run(self, cam_img):
        '''
        main runloop of the CV controller
        input: cam_image, an RGB numpy array
        output: steering, throttle, and recording flag
        '''
        if cam_img is None:
            return 0, 0, False, None

        max_yellow, confidense, mask = self.get_i_color(cam_img)
        conf_thresh = 0.001

        if self.target_pixel is None:
            # Use the first run of get_i_color to set our relationship with the yellow line.
            # You could optionally init the target_pixel with the desired value.
            self.target_pixel = max_yellow

            # this is the target of our steering PID controller
            self.pid_st.setpoint = self.target_pixel

        elif confidense > conf_thresh:
            # invoke the controller with the current yellow line position
            # get the new steering value as it chases the ideal
            self.steering = self.pid_st(max_yellow)

            # slow down linearly when away from ideal, and speed up when close
            if abs(max_yellow - self.target_pixel) > 10:
                if self.throttle > self.throttle_min:
                    self.throttle -= self.delta_th
            else:
                if self.throttle < self.throttle_max:
                    self.throttle += self.delta_th


        # show some diagnostics
        if self.overlay_image:
            cam_img = self.overlay_display(cam_img, mask, max_yellow, confidense)

        return self.steering, self.throttle, self.recording, cam_img

    def overlay_display(self, cam_img, mask, max_yellow, confidense):
        '''
        composite mask on top the original image.
        show some values we are using for control
        '''

        mask_exp = np.stack((mask, ) *3, axis=-1)
        iSlice = self.scan_y
        img = np.copy(cam_img)
        img[iSlice : iSlice + self.scan_height, :, :] = mask_exp
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        display_str = []
        display_str.append("STEERING:{:.1f}".format(self.steering))
        display_str.append("THROTTLE:{:.2f}".format(self.throttle))
        display_str.append("I YELLOW:{:d}".format(max_yellow))
        display_str.append("CONF:{:.2f}".format(confidense))

        y = 10
        x = 10

        for s in display_str:
            cv2.putText(img, s, color=(0 ,0 ,0), org=(x ,y), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.4)
            y += 10

        return img

