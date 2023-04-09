import time
import unittest

from donkeycar.parts.tachometer import Tachometer
from donkeycar.parts.tachometer import AbstractEncoder
from donkeycar.parts.tachometer import EncoderMode
from donkeycar.parts.tachometer import InverseTachometer


class MockEncoder(AbstractEncoder):
    def __init__(self) -> None:
        self.ticks = 0
        super().__init__()
    def start_ticks(self):
        pass
    def stop_ticks(self):
        pass
    def poll_ticks(self, direction: int) -> int:
        """
        add a tick based on direction
        """
        assert((1==direction) or (0==direction) or (-1==direction))
        self.ticks += direction
        return self.ticks
    def get_ticks(self, encoder_index:int=0) -> int:
        return self.ticks

class MockTachometer(Tachometer):
    def __init__(self, ticks_per_revolution: float, direction_mode, debug=False):
        super().__init__(MockEncoder(), ticks_per_revolution=ticks_per_revolution, direction_mode=direction_mode, poll_delay_secs=0, debug=debug)


class TestTachometer(unittest.TestCase):
    
    def test_tachometer_forward_only(self):
        #
        # FORWARD_ONLY mode will ignore throttle
        # and just increase revolutions
        #
        tachometer = MockTachometer(
            ticks_per_revolution=10, 
            direction_mode=EncoderMode.FORWARD_ONLY)

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
            direction_mode=EncoderMode.FORWARD_REVERSE)

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
            direction_mode=EncoderMode.FORWARD_REVERSE_STOP)

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


class TestInverseTachometer(unittest.TestCase):

    def test_inverse_tachometer_forward(self):
        tachometer = InverseTachometer(meters_per_revolution=0.25)
        revolutions, _ = tachometer.run(distance=100)
        self.assertEqual(400, revolutions)
