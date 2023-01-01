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
        self.revolutions:float = 0
        self.running:bool = True
        self.queue = CircularBuffer(smoothing_count if smoothing_count >= 1 else 1)
        self.debug = debug
        self.reading = (0, 0, None) # distance, velocity, timestamp

    def poll(self, revolutions:int, timestamp:float=None):
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

            #
            # Assignment in Python is atomic and so it is threadsafe
            #
            self.reading = (distance, velocity, timestamp)

    def update(self):
        while(self.running):
            self.poll(self.revolutions, None)
            time.sleep(0)  # give other threads time

    def run_threaded(self, revolutions:float=0, timestamp:float=None) -> Tuple[float, float, float]:
        if self.running:
            self.revolutions = revolutions
            self.timestamp = timestamp if timestamp is not None else time.time()

            return self.reading
        return 0, 0, self.timestamp

    def run(self, revolutions:float=0, timestamp:float=None) -> Tuple[float, float, float]:
        if self.running:
            self.timestamp = timestamp if timestamp is not None else time.time()
            self.poll(revolutions, self.timestamp)

            return self.reading
        return 0, 0, self.timestamp

    def shutdown(self):
        self.running = False
