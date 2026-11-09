import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from donkeycar.parts.mighty_gps import PoseGps
from donkeycar.parts.mighty_gps import MightyGpsReader
from donkeycar.parts.mighty_timing import MightyTiming


class PoseOrderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.timing = MightyTiming(self.temp.name)
        self.reader = MightyGpsReader.__new__(MightyGpsReader)
        import threading
        self.reader.pose_lock = threading.Lock()
        self.reader.timing = self.timing
        self.reader.converter = PoseGps(37, -122)

    def tearDown(self):
        self.timing.close()
        self.temp.cleanup()

    def pose(self, stamp, x=0):
        return dict(timestamp_ns=stamp, position_m=[x, 0, 0], confidence=1,
                    orientation_xyzw=[0, 0, 0, 1], pose_type='body', is_public=True)

    def test_late_duplicate_and_missing_cannot_replace_pose_or_refresh_age(self):
        with patch('donkeycar.parts.mighty_gps.time.monotonic', return_value=100):
            self.reader.on_pose(self.pose(1_000_000_000, 1))
        with patch('donkeycar.parts.mighty_gps.time.monotonic', return_value=101):
            for stamp in [900_000_000, 1_000_000_000, None, math.nan, math.inf]:
                self.reader.on_pose(self.pose(stamp, 99))
            self.assertEqual(self.reader.converter.latest[0], 1)
            self.assertEqual(self.reader.converter.latest[2], 100)
            self.assertIsNone(self.reader.converter.sample()[1])
        self.assertEqual(self.timing.snapshot()['timestamp_ns'], 1_000_000_000)

    def test_late_packet_keeps_baseline_and_reports_delay(self):
        with patch('donkeycar.parts.mighty_timing.time.monotonic', return_value=100):
            self.timing.pose(self.pose(1_000_000_000))
        with patch('donkeycar.parts.mighty_timing.time.monotonic', return_value=100.1):
            self.assertFalse(self.timing.pose(self.pose(700_000_000)))
        self.assertEqual(self.timing.minimum_offset, 99)
        with patch('donkeycar.parts.mighty_timing.time.monotonic', return_value=100.2):
            self.assertTrue(self.timing.pose(self.pose(1_100_000_000)))
        self.assertAlmostEqual(self.timing.latest['excess_delay_ms'], 100)
        self.timing.close()
        rows=[json.loads(line) for line in self.timing.path.read_text().splitlines()]
        self.assertFalse(rows[1]['accepted'])
        self.assertAlmostEqual(rows[1]['excess_delay_ms'], 400)

    def test_explicit_reset_allows_new_clock_epoch_after_tracking_resumes(self):
        self.reader.on_pose(self.pose(10_000_000_000))
        self.reader.on_reset({'reason': 'reset'})
        self.assertIsNone(self.reader.converter.latest)
        self.reader.on_state({'state': 2})
        self.reader.on_pose(self.pose(100, 2))
        self.assertEqual(self.reader.converter.latest[0], 2)
        self.assertEqual(self.timing.newest_stamp, 100)

    def test_lost_tracking_does_not_clear_watermark(self):
        self.reader.on_pose(self.pose(1000))
        self.reader.on_state({'state': 4})
        self.reader.on_state({'state': 2})
        self.reader.on_pose(self.pose(900))
        self.assertIsNone(self.reader.converter.latest)
        self.assertEqual(self.timing.newest_stamp, 1000)

    def test_initialization_resets_once_and_internal_stream_is_ignored(self):
        self.reader.on_pose(self.pose(1000))
        self.reader.on_state({'state': 1})
        epoch = self.timing.epoch
        self.reader.on_state({'state': 1})
        self.assertEqual(self.timing.epoch, epoch)
        self.reader.on_state({'state': 2})
        self.reader.on_pose(dict(self.pose(9999), is_public=False))
        self.reader.on_pose(self.pose(100, 3))
        self.assertEqual(self.reader.converter.latest[0], 3)


if __name__ == '__main__':
    unittest.main()
