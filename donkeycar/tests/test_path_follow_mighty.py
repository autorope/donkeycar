"""Construct the real template with hardware helpers mocked; never start driving."""
from contextlib import ExitStack
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from donkeycar.parts.mighty import MightyPose, MightyPoseTransform, PoseDriveGate, PoseRecordingGate
from donkeycar.parts.path import OriginOffset, CTE
from donkeycar.parts.open_path import LookAheadPilot

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
spec = importlib.util.spec_from_file_location('mighty_path_follow_test', TEMPLATES / 'path_follow.py')
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)


class VehicleGraph:
    def __init__(self):
        self.mem = {}
        self.parts = []
        self.start = MagicMock()

    def add(self, part, inputs=None, outputs=None, **kwargs):
        self.parts.append(dict(part=part, inputs=inputs or [], outputs=outputs or [], **kwargs))


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = SimpleNamespace(**runpy.run_path(str(TEMPLATES / 'cfg_path_follow.py')))
        self.cfg.HAVE_MIGHTY = True
        self.cfg.HAVE_GPS = False
        self.cfg.HAVE_T265 = self.cfg.HAVE_ODOM = False
        self.cfg.HAVE_SOMBRERO = self.cfg.HAVE_MQTT_TELEMETRY = False
        self.cfg.USE_SSD1306_128_32 = self.cfg.HAVE_CONSOLE_LOGGING = False
        self.cfg.USE_FUSION = False
        self.cfg.PATH_USE_LOOKAHEAD = True
        self.cfg.PATH_CLOSED = False
        self.cfg.PATH_FILENAME = str(Path(self.temp.name) / 'absent.csv')
        self.cfg.MIGHTY_LOG_DIRECTORY = self.temp.name
        for name in vars(self.cfg):
            if name.endswith('_BTN'):
                setattr(self.cfg, name, None)

    def build(self):
        vehicle = VehicleGraph()
        sdk = SimpleNamespace(MightyClient=MagicMock(), MightyWebDevice=MagicMock())
        fusion = SimpleNamespace(EKFFusion=MagicMock())
        with ExitStack() as stack:
            stack.enter_context(patch.dict('sys.modules', mighty_sdk=sdk,
                                           **{'donkeycar.parts.gps_imu_fusion': fusion}))
            stack.enter_context(patch.object(template.dk.vehicle, 'Vehicle', return_value=vehicle))
            for name in ['add_camera', 'add_drivetrain', 'add_user_controller', 'add_simulator', 'add_imu']:
                stack.enter_context(patch.object(template, name))
            serial = stack.enter_context(patch('donkeycar.parts.serial_port.SerialPort'))
            stack.enter_context(patch('donkeycar.parts.serial_port.SerialLineReader'))
            stack.enter_context(patch('donkeycar.parts.text_writer.CsvLogger'))
            with redirect_stdout(io.StringIO()):
                template.drive(self.cfg)
        for row in vehicle.parts:
            if isinstance(row['part'], MightyPose):
                self.addCleanup(row['part'].shutdown)
        return vehicle, serial

    def test_mighty_without_gps_drives_native_pose_and_safety_gates(self):
        vehicle, serial = self.build()
        serial.assert_not_called()
        self.assertFalse(any(key.startswith('gps/') for p in vehicle.parts for key in p['outputs']))
        reader = next(p for p in vehicle.parts if isinstance(p['part'], MightyPose))
        transform = next(p for p in vehicle.parts if isinstance(p['part'], MightyPoseTransform))
        self.assertEqual(transform['outputs'], ['pos/x', 'pos/y', 'pos/angle', 'mighty/valid'])
        origin = next(p for p in vehicle.parts if isinstance(p['part'], OriginOffset))
        self.assertLess(vehicle.parts.index(transform), vehicle.parts.index(origin))
        pilot = next(p for p in vehicle.parts if isinstance(p['part'], LookAheadPilot))
        self.assertEqual(pilot['inputs'][-2:], ['mighty/valid', 'pos/angle'])
        self.assertTrue(pilot['part'].require_heading)
        record = next(p for p in vehicle.parts if isinstance(p['part'], PoseRecordingGate))
        drive = next(p for p in vehicle.parts if isinstance(p['part'], PoseDriveGate))
        self.assertEqual(record['inputs'], ['recording', 'mighty/valid'])
        self.assertEqual(drive['inputs'][-1], 'mighty/valid')
        # Feed a raw pose through the constructed reader and transform.
        reader['part'].client.is_connected.return_value = True
        reader['part'].on_pose(dict(timestamp_ns=100, position_m=[3, 4, 0],
                                   orientation_xyzw=[0, 0, 0, 1], confidence=1))
        raw, fresh, _ = reader['part'].run_threaded()
        self.assertEqual(transform['part'].run(raw, fresh), (3, 4, 0, True))
        reader['part'].on_reset({})
        raw, fresh, _ = reader['part'].run_threaded()
        valid = transform['part'].run(raw, fresh)[3]
        self.assertFalse(record['part'].run(True, valid))
        for mode in ['local', 'local_angle']:
            self.assertEqual(drive['part'].run(mode, .3, .4, valid), (0, 0))
        self.assertEqual(drive['part'].run('user', .3, .4, valid), (.3, .4))

    def test_simultaneous_gps_is_separate_and_does_not_replay(self):
        self.cfg.HAVE_GPS = True
        self.cfg.GPS_NMEA_PATH = str(Path(self.temp.name) / 'gps.csv')
        vehicle, serial = self.build()
        serial.assert_called_once()
        outputs = [key for p in vehicle.parts for key in p['outputs']]
        self.assertIn('gps/utm/longitude', outputs)
        self.assertNotIn('gps/playing', outputs)
        pose_writers = [p for p in vehicle.parts if 'pos/x' in p['outputs']]
        self.assertEqual([type(p['part']) for p in pose_writers], [MightyPoseTransform, OriginOffset])

    def test_simultaneous_gps_fusion_cannot_overwrite_mighty(self):
        self.cfg.HAVE_GPS = self.cfg.USE_FUSION = True
        self.cfg.FUSION_DEBUG = False
        self.cfg.IMU_SENSOR = 'bno08x'
        vehicle, _ = self.build()
        outputs = [key for p in vehicle.parts for key in p['outputs']]
        self.assertIn('gps/fused/x', outputs)
        self.assertIn('gps/fused/yaw', outputs)
        pose_writers = [p for p in vehicle.parts if 'pos/x' in p['outputs']]
        self.assertEqual([type(p['part']) for p in pose_writers], [MightyPoseTransform, OriginOffset])

    def test_gps_only_keeps_existing_pid_and_playback(self):
        self.cfg.HAVE_MIGHTY = False
        self.cfg.HAVE_GPS = True
        self.cfg.PATH_USE_LOOKAHEAD = False
        self.cfg.PATH_CLOSED = True
        self.cfg.GPS_NMEA_PATH = str(Path(self.temp.name) / 'gps.csv')
        vehicle, serial = self.build()
        serial.assert_called_once()
        self.assertFalse(any(isinstance(p['part'], MightyPose) for p in vehicle.parts))
        self.assertTrue(any(type(p['part']) is CTE for p in vehicle.parts))
        self.assertTrue(any('gps/playing' in p['outputs'] for p in vehicle.parts))
        self.assertTrue(any(p['inputs'] == ['gps/utm/longitude', 'gps/utm/latitude']
                            and p['outputs'] == ['pos/x', 'pos/y'] for p in vehicle.parts))

    def test_legacy_config_fails_before_hardware_construction(self):
        self.cfg.GPS_SOURCE = 'mighty'
        with patch.object(template.dk.vehicle, 'Vehicle') as vehicle:
            with self.assertRaisesRegex(ValueError, 'HAVE_MIGHTY'):
                template.drive(self.cfg)
            vehicle.assert_not_called()


if __name__ == '__main__':
    unittest.main()
