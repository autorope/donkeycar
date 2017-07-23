from datetime import datetime, timedelta
import donkey as dk
import re

class TeensyRCin:
    def __init__(self):
        self.inSteering = 0
        self.inThrottle = None

        self.sensor = dk.actuators.Teensy(0);

        self.on = True

    def update(self):
        rcin_pattern = re.compile('^I ([.0-9]+) ([.0-9]+)$')

        while self.on:
            start = datetime.now()

            l = self.sensor.teensy_readline()
            while l:
                m = rcin_pattern.match(l.decode('utf-8'))

                if m:
                    inSteering = float(m.group(1))
                    inThrottle = float(m.group(2))

                l = self.sensor.teensy_readline()

            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        return self.inSteering, self.inThrottle

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping TeensyRCin')
        time.sleep(.5)

