import time
from typing import Tuple
import unittest

from donkeycar.parts.tachometer import Tachometer
from donkeycar.parts.tachometer import SerialPort


class MockTachometer(Tachometer):
    def poll_ticks(self):
        """
        add a tick based on direction
        """
        return self.ticks + self.direction


class MockSerialPort(SerialPort):
    def start(self, ):
        self.input = ""
        self.output = ""
        SerialPort.start(self)

    def stop(self):
        pass

    def buffered(self) -> int:
        """
        return: the number of buffered characters
        """
        return len(self.input)

    def read(self, count:int=0) -> Tuple[bool, str]:
        """
        if there are characters waiting, 
        then read them from the serial port
        bytes: number of bytes to read 
        return: tuple of
                bool: True if count bytes were available to read, 
                      false if not enough bytes were avaiable
                str: ascii string if count bytes read (may be blank), 
                     blank if count bytes are not available
        """
        input = ''
        waiting = self.buffered()
        if (waiting >= count):   # read the serial port and see if there's any data there
            input = self.input[0:count]
            self.buffer = self.input[count:]
        return ((waiting > 0), input)


    def readln(self) -> Tuple[bool, str]:
        """
        if there are characters waiting, 
        then read a line from the serial port.
        This will block until end-of-line can be read.
        The end-of-line is included in the return value.
        return: tuple of
                bool: True if line was read, false if not
                str: line if read (may be blank), 
                     blank if not read
        """
        #
        #
        input = ''
        waiting = self.buffered().find('\n"') + 1
        if (waiting > 0):   # read the serial port and see if there's any data there
            input = self.input[0:waiting]
            self.output = self.input[waiting:]
        return ((waiting > 0), input)
        
    def write(self, value:str):
        """
        write string to serial port
        """
        self.output = self.value

    def writeln(self, value:str):
        """
        write line to serial port
        """
        self.output = value + '\n'


class TestTachometer(unittest.TestCase):
    
    def test_tachometer_forward_only(self):
        #
        # FORWARD_ONLY mode will ignore throttle
        # and just increase revolutions
        #
        tachometer = MockTachometer(
            ticks_per_revolution=10, 
            direction_mode=Tachometer.FORWARD_ONLY)

        ts = time.time()
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4)

        ts += 1  # add one second and one revolution
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.2, revolutions, 4)

        ts += 1  # add one second, but stopped
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.3, revolutions, 4)

        ts += 1  # add one second and reverse one revolution
        revolutions, timestamp = tachometer.run(throttle=-1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.4, revolutions, 4) 

        ts += 1  # add one second, but stopped and coasting
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.5, revolutions, 4)


    def test_tachometer_forward_reverse(self):
        #
        # FORWARD_REVERSE mode will ignore zero throttle
        # and continue changing revolutions in the
        # current direction.  So if direction was
        # forward, then throttle=0 will continue forward,
        # if direction was reverse then throttle=0
        # will continue in reverse.
        #
        tachometer = MockTachometer(
            ticks_per_revolution=10, 
            direction_mode=Tachometer.FORWARD_REVERSE)

        ts = time.time()
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4)

        ts += 1  # add one second and one revolution
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.2, revolutions, 4)

        ts += 1  # add one second, but stopped
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.3, revolutions, 4)

        ts += 1  # add one second and reverse one revolution
        revolutions, timestamp = tachometer.run(throttle=-1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.2, revolutions, 4) 

        ts += 1  # add one second, but stopped and coasting
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4)


    def test_tachometer_forward_reverse_stop(self):
        #
        # FORWARD_REVERSE_STOP mode will honor the
        # throttle completely; 
        # positive throttle being forward, increasing revolutions
        # negative throttle being reverse, decreasing revolutions
        # zero throttle being stopped; no change in revolutions
        #
        tachometer = MockTachometer(
            ticks_per_revolution=10, 
            direction_mode=Tachometer.FORWARD_REVERSE_STOP)

        ts = time.time()
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4)

        ts += 1  # add one second and one revolution
        revolutions, timestamp = tachometer.run(throttle=1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.2, revolutions, 4)

        ts += 1  # add one second, but stopped
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.2, revolutions, 4)

        ts += 1  # add one second and reverse one revolution
        revolutions, timestamp = tachometer.run(throttle=-1, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4) 

        ts += 1  # add one second, but stopped
        revolutions, timestamp = tachometer.run(throttle=0, timestamp=ts)
        self.assertEqual(ts, timestamp)
        self.assertAlmostEqual(0.1, revolutions, 4)

