import time
from typing import Tuple

from donkeycar.utilities.circular_buffer import CircularBuffer


class Odometer:
    """
    An Odometer takes the output of a Tachometer (revolutions) and
    turns those into a distance and velocity.  Velocity can be
    optionally smoothed across a given number of readings.
    """
    def __init__(self, distance_per_revolution:float, smoothing_count=1, debug=False):
        self.distance_per_revolution:float = distance_per_revolution
        self.timestamp:float = 0
        self.revolutions:int = 0
        self.running:bool = True
        self.queue = CircularBuffer(smoothing_count if smoothing_count >= 1 else 1)
        self.debug = debug

    def poll(self, revolutions, timestamp):
        if self.running:
            if timestamp is None:
                timestamp = time.time()
            distance = revolutions * self.distance_per_revolution

            # smooth velocity
            velocity = 0
            if self.queue.count > 0:
                lastDistance, lastVelocity, lastTimestamp = self.queue.tail()
                if timestamp > lastTimestamp:
                    velocity = (distance - lastDistance) / (timestamp - lastTimestamp)

            self.queue.enqueue((distance, velocity, timestamp))
            if self.debug and velocity != 0:
                print("odometry: d = {}, v = {}, ts = {}".format(distance, velocity, timestamp))

    def update(self):
        while(self.running):
            self.poll(self.revolutions, self.timestamp)

    def run_threaded(self, revolutions:int=0, timestamp:float=None) -> Tuple[float, float, float]:
        if self.running:
            self.revolutions = revolutions
            self.timestamp = timestamp if timestamp is not None else time.time()

            if self.queue.count > 0:
                return self.queue.head()
        return (0, 0, self.timestamp)

    def run(self, revolutions:int=0, timestamp:float=None) -> Tuple[float, float, float]:
        if self.running:
            self.poll(revolutions, timestamp)

            if self.queue.count > 0:
                return self.queue.head()
        return (0, 0, self.timestamp)

    def shutdown(self):
        self.running = False

