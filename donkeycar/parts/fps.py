import time
import logging

logger = logging.getLogger(__name__)


class FrequencyLogger(object):
    """
    Log current, min and max of frequency value
    """

    def __init__(self, debug_interval=10):
        self.last_timestamp = None
        self.counter = 0
        self.fps = 0
        self.fps_list = []

        self.last_debug_timestamp = None
        self.debug_interval = debug_interval

    def run(self):
        if self.last_timestamp is None:
            self.last_timestamp = time.time()

        if time.time() - self.last_timestamp > 1:
            self.fps = self.counter
            self.fps_list.append(self.counter)
            self.counter = 0
            self.last_timestamp = time.time()
        else:
            self.counter += 1

        # Printing frequency info into shell
        if self.last_debug_timestamp is None:
            self.last_debug_timestamp = time.time()

        if time.time() - self.last_debug_timestamp > self.debug_interval:
            logger.info(f"current fps = {self.fps}")
            self.last_debug_timestamp = time.time()

        return self.fps, self.fps_list

    def shutdown(self):
        if self.fps_list:
            logger.info(f"fps (min/max) = {min(self.fps_list):2d} / {max(self.fps_list):2d}")
            logger.info(f"fps list = {self.fps_list}".format())
