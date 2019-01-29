import numpy as np
import cv2


class Graph(object):
    '''
    Take input values and plot them on an image.
    Takes a list of (x, y) (b, g, r) pairs and
    plots the color at the given coordinate.
    When the x value exceeds the width, the graph is erased
    and begins with an offset to x values such that drawing
    begins again at the left edge.
    This assumes x is monotonically increasing, like a time value.
    '''
    def __init__(self, res=(200, 200, 3)):
        self.img = np.zeros(res)
        self.prev = 0

    def clamp(self, val, lo, hi):
        if val < lo:
            val = lo
        elif val > hi:
            val = hi
        return int(val)

    def run(self, values):
        if values is None:
            return self.img

        for coord, col in values:
            x = coord[0] % self.img.shape[1]
            y = self.clamp(coord[1], 0, self.img.shape[0] - 1)
            self.img[y, x] = col

        if abs(self.prev - x) > self.img.shape[1] / 2:
            self.img = np.zeros_like(self.img)

        self.prev = x
            
        return self.img

    def shutdown(self):
        pass
