import logging
from typing import Any

import cv2
import numpy as np
from simple_pid import PID

logger = logging.getLogger(__name__)

# The car config is a donkeycar.config.Config, populated by exec'ing the car's
# config.py, so its attributes do not exist statically. Naming the alias says
# "the car config" without promising a shape a type checker could verify.
CarConfig = Any


class LineFollower:
    """
    OpenCV based controller

    This controller takes a horizontal slice of the image at a set Y coordinate.
    Then it converts to HSV and does a color thresh hold to find the yellow pixels.
    It does a histogram to find the pixel of maximum yellow. Then is uses that pixel
    to guide a PID controller which seeks to maintain the max yellow at the same point
    in the image.

    The point it steers toward can be shifted sideways by `lane_offset_px`, which is
    how an agent asks the car to hold a lane to one side of the tape rather than
    centred on it. An offset of None or 0 reproduces the original behaviour exactly.
    """

    def __init__(self, pid: PID, cfg: CarConfig) -> None:
        self.overlay_image = cfg.OVERLAY_IMAGE
        self.scan_y = cfg.SCAN_Y  # num pixels from the top to start horiz scan
        self.scan_height = cfg.SCAN_HEIGHT  # num pixels high to grab from horiz scan
        self.color_thr_low = np.asarray(cfg.COLOR_THRESHOLD_LOW)  # hsv dark yellow
        self.color_thr_hi = np.asarray(cfg.COLOR_THRESHOLD_HIGH)  # hsv light yellow
        # of the N slots above, which is the ideal relationship target
        self.target_pixel = cfg.TARGET_PIXEL
        # minimum distance from target_pixel before a steering change is made
        self.target_threshold = cfg.TARGET_THRESHOLD
        # percentage of yellow pixels that must be in target_pixel slice
        self.confidence_threshold = cfg.CONFIDENCE_THRESHOLD
        self.steering = 0.0  # from -1 to 1
        self.throttle = cfg.THROTTLE_INITIAL  # from -1 to 1
        self.delta_th = cfg.THROTTLE_STEP  # how much to change throttle when off
        self.throttle_max = cfg.THROTTLE_MAX
        self.throttle_min = cfg.THROTTLE_MIN

        # Needed to clamp a requested lane offset to the frame. The controller
        # did not previously need to know the image width.
        self.image_w = getattr(cfg, "IMAGE_W", None)

        # The target actually being steered to, i.e. target_pixel plus any lane
        # offset. Kept as state so the overlay can show what is being chased.
        self.effective_target_pixel = self.target_pixel

        # How much of the last steering command to keep on each loop where the
        # line cannot be seen. 1.0 restores the old behaviour of holding the
        # last value indefinitely, which drives a blind car in a circle at
        # whatever lock it happened to be at when it lost the line.
        self.lost_line_decay = float(getattr(cfg, "LOST_LINE_STEERING_DECAY", 0.85))

        # Published so an agent can tell a confident lock from a lost line;
        # the steering value alone looks identical in both cases.
        self.confidence = 0.0
        self.line_detected = False
        self.loops_since_line = 0

        self.pid_st = pid

    def get_i_color(self, cam_img: np.ndarray) -> tuple[int, float, np.ndarray]:
        """
        get the horizontal index of the color at the given slice of the image

        input:  cam_image, an RGB numpy array
        output: index of max color, confidence at that index, and the mask.

        Confidence is the fraction of that column which matched, 0.0 to 1.0. It
        used to be the raw sum of mask values -- 255 per matching pixel -- while
        CONFIDENCE_THRESHOLD was documented as a fraction and defaulted to
        0.0015. A single matching pixel scored 255 and cleared it, so the gate
        could never reject anything: a ten-pixel speck at the edge of the frame
        counted as a confident line detection, and the car drove off after it.
        """
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

        # Matching pixels in the best column, over the height of that column.
        lit = float(hist[max_yellow]) / 255.0
        confidence = lit / float(self.scan_height) if self.scan_height else 0.0

        return int(max_yellow), confidence, mask

    def _resolve_target(self, cam_img: np.ndarray, lane_offset_px: int | None) -> int:
        """
        Combine the base target with the requested lane offset and clamp it into
        the frame. Returns the pixel column the PID should steer toward.
        """
        offset = 0 if lane_offset_px is None else int(lane_offset_px)
        target = self.target_pixel + offset

        # Prefer the configured width, but fall back to the frame we were handed
        # so a mis-set IMAGE_W cannot push the target outside the image.
        width = self.image_w if self.image_w else cam_img.shape[1]
        return max(0, min(int(target), int(width) - 1))

    def run(
        self, cam_img: np.ndarray | None, lane_offset_px: int | None = None
    ) -> tuple[float, float, np.ndarray | None, float, bool]:
        """
        main runloop of the CV controller

        input:  cam_image, an RGB numpy array
                lane_offset_px, pixels to shift the steering target sideways.
                    None or 0 holds the line itself, which is the original
                    behaviour. Positive moves the target right in image space.
        output: steering, throttle, and the image.
        If overlay_image is True, then the output image
        includes and overlay that shows how the
        algorithm is working; otherwise the image
        is just passed-through untouched.
        """
        if cam_img is None:
            self.confidence = 0.0
            self.line_detected = False
            return 0.0, 0.0, None, 0.0, False

        max_yellow, confidence, mask = self.get_i_color(cam_img)

        if self.target_pixel is None:
            # Use the first run of get_i_color to set our relationship with the yellow line.
            # You could optionally init the target_pixel with the desired value.
            self.target_pixel = max_yellow
            logger.info(f"Automatically chosen line position = {self.target_pixel}")

        # Everything below steers to the effective target, not the base target.
        # Using target_pixel here would make the offset move the setpoint while
        # leaving the throttle ramp measuring distance from the wrong column.
        self.effective_target_pixel = self._resolve_target(cam_img, lane_offset_px)

        if self.pid_st.setpoint != self.effective_target_pixel:
            # this is the target of our steering PID controller
            self.pid_st.setpoint = self.effective_target_pixel

        self.confidence = float(confidence)
        self.line_detected = bool(confidence >= self.confidence_threshold)

        if confidence >= self.confidence_threshold:
            self.loops_since_line = 0
            # invoke the controller with the current yellow line position
            # get the new steering value as it chases the ideal.
            # The PID returns None until it has produced an output, so hold the
            # previous steering rather than propagating None downstream.
            control = self.pid_st(max_yellow)
            if control is not None:
                self.steering = float(control)

            # slow down linearly when away from ideal, and speed up when close
            if abs(max_yellow - self.effective_target_pixel) > self.target_threshold:
                # we will be turning, so slow down
                if self.throttle > self.throttle_min:
                    self.throttle -= self.delta_th
                if self.throttle < self.throttle_min:
                    self.throttle = self.throttle_min
            else:
                # we are going straight, so speed up
                if self.throttle < self.throttle_max:
                    self.throttle += self.delta_th
                if self.throttle > self.throttle_max:
                    self.throttle = self.throttle_max
        else:
            # Straighten up rather than hold the last command. Holding meant a
            # car that lost the line kept driving at whatever lock it had --
            # observed on a real track as a full-lock turn off the course into
            # the furniture. Driving straight while blind is a great deal less
            # bad than circling.
            self.steering *= self.lost_line_decay
            if abs(self.steering) < 0.01:
                self.steering = 0.0
            self.loops_since_line += 1
            logger.info(
                "No line detected: confidence %s < %s (steering decayed to %.3f)",
                confidence,
                self.confidence_threshold,
                self.steering,
            )

        # show some diagnostics
        if self.overlay_image:
            cam_img = self.overlay_display(cam_img, mask, max_yellow, confidence)

        return self.steering, self.throttle, cam_img, self.confidence, self.line_detected

    def overlay_display(self, cam_img: np.ndarray, mask: np.ndarray, max_yellow: int, confidense: float) -> np.ndarray:
        """
        composite mask on top the original image.
        show some values we are using for control
        """

        mask_exp = np.stack((mask,) * 3, axis=-1)
        iSlice = self.scan_y
        img = np.copy(cam_img)
        img[iSlice : iSlice + self.scan_height, :, :] = mask_exp

        display_str = []
        display_str.append(f"STEERING:{self.steering:.1f}")
        display_str.append(f"THROTTLE:{self.throttle:.2f}")
        display_str.append(f"I YELLOW:{max_yellow:d}")
        display_str.append(f"CONF:{confidense:.3f}")
        display_str.append(f"TARGET:{self.effective_target_pixel}")
        if not self.line_detected:
            display_str.append(f"LINE LOST x{self.loops_since_line}")

        y = 10
        x = 10

        for s in display_str:
            cv2.putText(img, s, color=(0, 0, 0), org=(x, y), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.4)
            y += 10

        return img
