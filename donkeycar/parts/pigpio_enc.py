import pigpio
import time

class OdomDist(object):
    """
    Take a tick input from odometry and compute the distance travelled
    """
    def __init__(self, mm_per_tick, debug=False):
        self.mm_per_tick = mm_per_tick
        self.m_per_tick = mm_per_tick / 1000.0
        self.meters = 0
        self.last_time = time.time()
        self.meters_per_second = 0
        self.debug = debug
        self.prev_ticks = 0

    def run(self, ticks, throttle):
        """
        inputs => total ticks since start
        inputs => throttle, used to determine positive or negative vel
        return => total dist (m), current vel (m/s), delta dist (m)
        """
        new_ticks = ticks - self.prev_ticks
        self.prev_ticks = ticks

        #save off the last time interval and reset the timer
        start_time = self.last_time
        end_time = time.time()
        self.last_time = end_time
        
        #calculate elapsed time and distance traveled
        seconds = end_time - start_time
        distance = new_ticks * self.m_per_tick
        if throttle < 0.0:
            distance = distance * -1.0
        velocity = distance / seconds
        
        #update the odometer values
        self.meters += distance
        self.meters_per_second = velocity

        #console output for debugging
        if(self.debug):
            print('seconds:', seconds)
            print('delta:', distance)
            print('velocity:', velocity)

            print('distance (m):', self.meters)
            print('velocity (m/s):', self.meters_per_second)

        return self.meters, self.meters_per_second, distance


class PiPGIOEncoder():
    def __init__(self, pin, pi):
        self.pin = pin
        self.pi = pi
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
        self.cb = pi.callback(self.pin, pigpio.FALLING_EDGE, self._cb)
        self.count = 0

    def _cb(self, pin, level, tick):
        self.count += 1

    def run(self):
        return self.count

    def shutdown(self):
        if self.cb != None:
            self.cb.cancel()
            self.cb = None

        self.pi.stop()


if __name__ == "__main__":
    pi = pigpio.pi()
    e = PiPGIOEncoder(4, pi)
    while True:
        time.sleep(0.1)
        e.run()


