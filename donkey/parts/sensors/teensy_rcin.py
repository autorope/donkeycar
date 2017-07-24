from datetime import datetime, timedelta
import donkey as dk
import re
import time

class TeensyRCin:
    def __init__(self):
        self.inSteering = 0.0
        self.inThrottle = 0.0

        self.sensor = dk.parts.Teensy(0);

        TeensyRCin.LEFT_ANGLE = -1
        TeensyRCin.RIGHT_ANGLE = 1
        TeensyRCin.MIN_THROTTLE = -1
        TeensyRCin.MAX_THROTTLE =  1

        TeensyRCin.LEFT_PULSE = 460
        TeensyRCin.RIGHT_PULSE = 276
        TeensyRCin.MAX_PULSE = 460
        TeensyRCin.MIN_PULSE = 276


        self.on = True

    def update(self):
        rcin_pattern = re.compile('^I ([.0-9]+) ([.0-9]+)$')

        while self.on:
            start = datetime.now()

            l = self.sensor.teensy_readline()

            while l:
                print("mw TeensyRCin line= " + l.decode('utf-8'))
                m = rcin_pattern.match(l.decode('utf-8'))

                if m:
                    i = float(m.group(1)) / (1000 * 1000) # in seconds
                    inSteering = utils.map_range(i * (self.sensor.frequency * 4096),
                                                 TeensyRCin.LEFT_PULSE, TeensyRCin.RIGHT_PULSE,
                                                 TeensyRCin.LEFT_ANGLE, TeensyRCin.RIGHT_ANGLE)

                    i = float(m.group(2)) / (1000 * 1000) # in seconds
                    inThrottle = utils.map_range(i * (self.sensor.frequency * 4096),
                                                 TeensyRCin.MIN_PULSE, TeensyRCin.MAX_PULSE,
                                                 TeensyRCin.MIN_THROTTLE, TeensyRCin.MAX_THROTTLE)

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

