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
        self.distance = 0
        self.prev_distance = 0
        self.ave_velocity = []
        for i in range(10):
            self.ave_velocity.append(0)

    def run(self, ticks, throttle):
        """
        inputs => total ticks since start
        inputs => throttle, used to determine positive or negative vel
        return => total dist (m), current vel (m/s), delta dist (m)
        """


        #save off the last time interval and reset the timer
        start_time = self.last_time
        end_time = time.time()
        self.last_time = end_time
        
        #calculate elapsed time and distance traveled
        seconds = end_time - start_time
        self.distance = ticks * self.m_per_tick  #converted to meters here
        # if throttle < 0.0:
        #     print("throttle is negative")
        #     self.distance = self.distance * -1.0
        delta_distance = self.distance - self.prev_distance
        instant_velocity = delta_distance/seconds
        for i in range(9):  # do a moving average over a 1/2 second window (10 readings of a 20Hz feed)
            self.ave_velocity[9-i] = self.ave_velocity[8-i]  # move the time window down one
        self.ave_velocity[0] = instant_velocity  # stick the latest reading at the start
        velocity = sum(self.ave_velocity)/10  # moving average
        #update the odometer values
        self.meters += delta_distance
        self.meters_per_second = velocity
        self.prev_distance = self.distance
        #console output for debugging
        if(self.debug):
            print('distance (m):', round(self.meters,3))
            print('velocity (m/s):', round(self.meters_per_second,3))

        return self.meters, self.meters_per_second, self.distance


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


