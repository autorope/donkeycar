"""Hardware-free coverage of raw Mighty acquisition and native pose conversion."""
import math
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from donkeycar.parts.mighty import MightyPose, MightyPoseTransform, PoseDriveGate, PoseRecordingGate


def body_pose(**changes):
    return dict(dict(timestamp_ns=1_000_000_000, position_m=[3, 4, 0],
                     orientation_xyzw=[0, 0, 0, 1], confidence=1,
                     pose_type='body', is_public=True), **changes)


class TransformTests(unittest.TestCase):
    def test_native_metres_and_rotation(self):
        self.assertEqual(MightyPoseTransform().run(body_pose(), True), (3, 4, 0, True))
        x, y, angle, valid = MightyPoseTransform(yaw=90).run(body_pose(), True)
        self.assertTrue(valid)
        self.assertAlmostEqual(x, -4)
        self.assertAlmostEqual(y, 3)
        self.assertAlmostEqual(angle, math.pi/2)

    def test_quaternion_normalization_and_forward_axis(self):
        pose = body_pose(orientation_xyzw=[0, 0, 2, 2])
        result = MightyPoseTransform(yaw=20, heading_offset=30).run(pose, True)
        self.assertAlmostEqual(result[2], math.radians(140))
        result = MightyPoseTransform(yaw=150).run(pose, True)
        self.assertAlmostEqual(result[2], math.radians(-120))

    def test_invalid_pose_never_publishes_coordinates(self):
        transform = MightyPoseTransform()
        invalid = (None, None, None, False)
        self.assertEqual(transform.run(body_pose(), False), invalid)
        for pose in [None, {}, body_pose(position_m=[1]),
                     body_pose(position_m=[math.nan, 0, 0]),
                     body_pose(confidence=.4), body_pose(confidence=math.inf),
                     body_pose(pose_type='camera'), body_pose(is_public=False),
                     body_pose(orientation_xyzw=None),
                     body_pose(orientation_xyzw=[0, 0, 0, 0]),
                     body_pose(orientation_xyzw=[0, 0, math.nan, 1]),
                     body_pose(orientation_xyzw=[0, math.sqrt(.5), 0, math.sqrt(.5)])]:
            with self.subTest(pose=pose):
                self.assertEqual(transform.run(pose, True), invalid)

    def test_invalid_configuration(self):
        for args in [dict(yaw=math.nan), dict(heading_offset=math.inf)]:
            with self.assertRaises(ValueError):
                MightyPoseTransform(**args)
        for max_age in [0, -1, math.inf, math.nan]:
            with self.assertRaises(ValueError):
                MightyPose(max_age=max_age)

    def test_pose_validity_gates_recording_and_both_auto_modes(self):
        record, drive = PoseRecordingGate(), PoseDriveGate()
        for valid in [True, False, None]:
            for recording in [True, False]:
                self.assertEqual(record.run(recording, valid), bool(recording and valid))
            for mode in ['local', 'local_angle']:
                self.assertEqual(drive.run(mode, .3, .4, valid), (.3, .4) if valid else (0, 0))
            self.assertEqual(drive.run('user', .3, .4, valid), (.3, .4))


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sdk = SimpleNamespace(MightyClient=MagicMock(), MightyWebDevice=MagicMock())
        with patch.dict('sys.modules', mighty_sdk=self.sdk):
            self.reader = MightyPose(log_directory=self.temp.name, high_rate_pose=True)
        self.addCleanup(self.reader.shutdown)
        self.reader.client.is_connected.return_value = True
        self.reader.client.stats.return_value = {}

    def test_raw_pose_and_transform_are_independent(self):
        pose = body_pose()
        self.reader.on_pose(pose)
        raw, fresh, timing = self.reader.run_threaded()
        self.assertEqual(raw, pose)
        self.assertTrue(fresh)
        self.assertEqual(timing['timestamp_ns'], pose['timestamp_ns'])
        self.assertEqual(MightyPoseTransform().run(raw, fresh), (3, 4, 0, True))
        pose['position_m'][0] = 100
        raw['position_m'][0] = 200
        self.assertEqual(self.reader.run_threaded()[0]['position_m'][0], 3)

    def test_missing_stale_disconnected_and_tracking_loss(self):
        self.assertEqual(self.reader.run_threaded()[:2], (None, False))
        with patch('donkeycar.parts.mighty.time.monotonic', return_value=10):
            self.reader.on_pose(body_pose())
            self.assertTrue(self.reader.run_threaded()[1])
        with patch('donkeycar.parts.mighty.time.monotonic', return_value=11):
            raw, fresh, _ = self.reader.run_threaded()
            self.assertFalse(fresh)
            self.assertEqual(MightyPoseTransform().run(raw, fresh), (None, None, None, False))
        self.reader.on_pose(body_pose(timestamp_ns=2_000_000_000))
        self.reader.client.is_connected.return_value = False
        self.assertEqual(self.reader.run_threaded()[:2], (None, False))
        self.reader.client.is_connected.return_value = True
        self.reader.on_state({'state': 4})
        self.assertEqual(self.reader.run_threaded()[:2], (None, False))
        self.reader.on_state({'state': 2})
        self.assertFalse(self.reader.run_threaded()[1])
        self.reader.on_pose(body_pose(timestamp_ns=3_000_000_000))
        self.assertTrue(self.reader.run_threaded()[1])

    def test_bad_new_pose_cannot_leave_previous_valid_output(self):
        transform = MightyPoseTransform()
        self.reader.on_pose(body_pose())
        self.reader.on_pose(body_pose(timestamp_ns=2_000_000_000, confidence=0))
        raw, fresh, _ = self.reader.run_threaded()
        self.assertFalse(transform.run(raw, fresh)[3])

    def test_callbacks_startup_and_shutdown(self):
        self.reader.client.on_pose.assert_called_once_with(self.reader.on_pose)
        self.reader.client.on_vio_state.assert_called_once_with(self.reader.on_state)
        self.reader.client.on_reset.assert_called_once_with(self.reader.on_reset)
        self.reader.client.start_vio.return_value = {'ok': True}
        self.reader.stop.set()
        self.reader.update()
        self.reader.client.connect.assert_called_once()
        self.reader.client.command.assert_called_once_with('high_rate_imu', b'on')
        self.reader.client.start_vio.assert_called_once()
        self.reader.shutdown()
        self.assertFalse(self.reader.timing.worker.is_alive())

    def test_no_vio_start_when_disabled(self):
        self.reader.start_vio = False
        self.reader.high_rate_pose = False
        self.reader.stop.set()
        self.reader.update()
        self.reader.client.start_vio.assert_not_called()
        self.reader.client.command.assert_called_once_with('high_rate_imu', b'status')


if __name__ == '__main__':
    unittest.main()
