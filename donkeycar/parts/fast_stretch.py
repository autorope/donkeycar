import cv2
import numpy as np
from pathlib import Path
import time

Mx = 128  # Natural mean
C = 0.007  # Base line fraction
Ts = 0.02  # Tunable amplitude
Tr = 0.7  # Threshold
T = -0.3  # Gamma boost
Epsilon = 1e-07  # Epsilon


def fast_stretch(image, debug=False):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    (h, s, v) = cv2.split(hsv)
    input = v
    shape = input.shape
    rows = shape[0]
    cols = shape[1]
    size = rows * cols
    output = np.empty_like(input)
    if debug:
        start = time.time()
    mean = np.mean(input)
    t = (mean - Mx) / Mx
    Sl = 0.
    Sh = 0.
    if t <= 0:
        Sl = C
        Sh = C - (Ts * t)
    else:
        Sl = C + (Ts * t)
        Sh = C

    gamma = 1.
    if t <= T:
        gamma = max((1 + (t - T)), Tr)

    if debug:
        time_taken = (time.time() - start) * 1000
        print('Preprocessing time %s' % time_taken)
        start = time.time()

    histogram = cv2.calcHist([input], [0], None, [256], [0, 256])
    # Walk histogram
    Xl = 0
    Xh = 255
    targetFl = Sl * size
    targetFh = Sh * size

    count = histogram[Xl]
    while count < targetFl:
        count += histogram[Xl]
        Xl += 1

    count = histogram[Xh]
    while count < targetFh:
        count += histogram[Xh]
        Xh -= 1

    if debug:
        time_taken = (time.time() - start) * 1000
        print('Histogram Binning %s' % time_taken)
        start = time.time()

    # Vectorized ops
    output = np.where(input <= Xl, 0, input)
    output = np.where(output >= Xh, 255, output)
    output = np.where(np.logical_and(output > Xl, output < Xh), np.multiply(
        255, np.power(np.divide(np.subtract(output, Xl), np.max([np.subtract(Xh, Xl), Epsilon])), gamma)), output)
    # max to 255
    output = np.where(output > 255., 255., output)
    output = np.asarray(output, dtype='uint8')
    output = cv2.merge((h, s, output))
    output = cv2.cvtColor(output, cv2.COLOR_HSV2RGB)

    if debug:
        time_taken = (time.time() - start) * 1000
        print('Vector Ops %s' % time_taken)
        start = time.time()

    return output


if __name__ == "__main__":
    path = Path('images/Lenna.jpg')
    image = cv2.imread(path.as_posix())
    # Ensure BGR
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    image_data = np.asarray(bgr, dtype=np.uint8)

    stretched = fast_stretch(image_data, debug=True)
    cv2.imshow('Original', image)
    cv2.imshow('Contrast Stretched', stretched)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
