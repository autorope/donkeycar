import time
from typing import Tuple

from donkeycar.utilities.circular_buffer import CircularBuffer


class Odometer:
    """
    An Odometer takes the output of a Tachometer (revolutions) and
    turns those into a distance and velocity.  Velocity can be
    optionally smoothed across a given number of readings.
    """
    def __init__(self, distance_per_revolution:float, smoothing_count=1):
        self.distance_per_revolution:float = distance_per_revolution
        self.distance:float = 0
        self.velocity:float = 0
        self.timestamp:float = 0
        self.running:bool = True
        self.queue = CircularBuffer(smoothing_count if smoothing_count >= 1 else 1)

    def poll(self, revolutions:int, timestamp:float=None):
        if self.running:
            if timestamp is None:
                timestamp = time.time()
            distance = revolutions * self.distance_per_revolution

            # smooth velocity
            if self.queue.count > 0:
                lastDistance, lastTimestamp = self.queue.tail()
                self.velocity = (distance - lastDistance) / (timestamp - lastTimestamp)

            self.distance = distance
            self.timestamp = timestamp
            self.queue.enqueue((self.distance, self.timestamp))

    def update(self, revolutions:int, timestamp:float=None):
        while(self.running):
            self.poll(revolutions, timestamp)

    def run_threaded(self) -> Tuple[float, float, float]:
        if self.running:
            return (self.distance, self.velocity, self.timestamp)
        return 0

    def run(self, revolutions:int, timestamp:float=None) -> Tuple[float, float, float]:
        self.poll(revolutions, timestamp)
        return self.run_threaded()

    def shutdown(self):
        self.running = False

