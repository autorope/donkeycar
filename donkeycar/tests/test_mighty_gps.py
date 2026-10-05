import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pynmea2
import utm

from donkeycar.parts.mighty_gps import (
    PoseGps, MightyGpsReader, GpsRecordingGate, GpsDriveGate, coordinate, rmc,
)


class TestMightyGps(unittest.TestCase):
    def setUp(self):
        self.gps = PoseGps(37, -122)

    def pose(self, **changes):
        return dict(position_m=[3, 4, 0], confidence=1, pose_type='body', **changes)

    def valid(self, connected=True):
        return pynmea2.parse(self.gps.sentence(connected), check=True).status == 'A'

    def test_rmc_checksum_and_hemispheres(self):
        parsed = pynmea2.parse(rmc(-37, -122), check=True)
        self.assertAlmostEqual(parsed.latitude, -37)
        self.assertAlmostEqual(parsed.longitude, -122)
        self.assertEqual(parsed.status, 'A')

    def test_coordinate_carry(self):
        self.assertEqual(coordinate(12.999999999999, True), ('1300.00000000', 'N'))

    def test_meter_scale_and_rotation(self):
        self.gps = PoseGps(37, -122, yaw=90)
        self.gps.on_pose(self.pose())
        parsed = pynmea2.parse(self.gps.sentence(), check=True)
        e, n, _, _ = utm.from_latlon(parsed.latitude, parsed.longitude)
        self.assertAlmostEqual(e - self.gps.east, -4, places=3)
        self.assertAlmostEqual(n - self.gps.north, 3, places=3)

    def test_no_pose_or_disconnect(self):
        self.assertFalse(self.valid())
        self.gps.on_pose(self.pose())
        self.assertTrue(self.valid())
        self.assertFalse(self.valid(False))

    def test_invalid_configuration(self):
        for kwargs in [{'yaw': math.nan}, {'max_age': 0}, {'max_age': math.inf}]:
            with self.assertRaises(ValueError):
                PoseGps(37, -122, **kwargs)

    def test_stale_pose(self):
        with patch('donkeycar.parts.mighty_gps.time.monotonic', return_value=1):
            self.gps.on_pose(self.pose())
        with patch('donkeycar.parts.mighty_gps.time.monotonic', return_value=2):
            self.assertFalse(self.valid())

    def test_bad_pose(self):
        for pose in [{}, {'position_m': [1]},
                     dict(position_m=[math.nan, 0, 0], confidence=1),
                     dict(position_m=[0, 0, 0], confidence=0.4),
                     dict(position_m=[0, 0, 0], confidence=1, pose_type='camera')]:
            self.gps.on_pose(self.pose())
            self.gps.on_pose(pose)
            self.assertFalse(self.valid())

    def test_tracking_reset_and_recovery(self):
        self.gps.on_pose(self.pose())
        self.gps.on_state({'state': 0})
        self.assertFalse(self.valid())
        self.gps.on_pose(self.pose())
        self.assertFalse(self.valid())
        self.gps.on_state({'state': 2})
        self.assertFalse(self.valid())
        self.gps.on_pose(self.pose())
        self.assertTrue(self.valid())

    def test_recording_gate(self):
        gate = GpsRecordingGate()
        for recording in [True, False]:
            for valid in [True, False, None]:
                self.assertEqual(gate.run(recording, valid), bool(recording and valid))

    def test_drive_gate(self):
        gate = GpsDriveGate()
        for mode in ['local', 'local_angle']:
            self.assertEqual(gate.run(mode, .3, .4, None), (0, 0))
            self.assertEqual(gate.run(mode, .3, .4, False), (0, 0))
            self.assertEqual(gate.run(mode, .3, .4, True), (.3, .4))
        self.assertEqual(gate.run('user', .3, .4, False), (.3, .4))

    def test_reader_callbacks_and_shutdown(self):
        cfg = SimpleNamespace(MIGHTY_GPS_LAT=37, MIGHTY_GPS_LON=-122,
                              MIGHTY_GPS_YAW=0, MIGHTY_GPS_MAX_AGE=.5,
                              MIGHTY_GPS_URL='http://camera', MIGHTY_GPS_START_VIO=True)
        sdk = SimpleNamespace(MightyClient=MagicMock(), MightyWebDevice=MagicMock())
        with patch.dict('sys.modules', mighty_sdk=sdk):
            reader = MightyGpsReader(cfg)
        reader.converter.on_pose(self.pose())
        reader.client.is_connected.return_value = True
        lines, valid = reader.run_threaded()
        self.assertTrue(valid)
        self.assertEqual(pynmea2.parse(lines[0][1], check=True).status, 'A')
        reader.shutdown()
        self.assertTrue(reader.stop.is_set())
        reader.client.disconnect.assert_called_once()
        reader.client.start_vio.return_value = {'ok': True}
        reader.update()
        reader.client.connect.assert_called_once()
        reader.client.start_vio.assert_called_once()


if __name__ == '__main__':
    unittest.main()
