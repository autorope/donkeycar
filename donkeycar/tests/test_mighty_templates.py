"""CAMERA_TYPE = "MIGHTY" in each template, with the Mighty SDK mocked (plan commits 5, 6 and 7-9)."""
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import donkeycar as dk
from donkeycar.parts.camera import CameraError
from donkeycar.parts.mighty import MightyCamera, MightyLink
from donkeycar.templates import complete, cv_control
from donkeycar.tests import test_mighty_camera as camera_tests
from donkeycar.tests.setup import custom_template, d2_path

URL = 'http://192.168.7.1'


class VehicleGraph:
    def __init__(self):
        self.parts = []

    def add(self, part, inputs=None, outputs=None, **kwargs):
        self.parts.append(dict(part=part, inputs=inputs or [], outputs=outputs or [], **kwargs))


MEASURED_FPS = 17.8


class MightyTemplateCase(unittest.TestCase):
    """Mocks the SDK with fake clients that deliver one 640x400 frame on connect.

    The startup frame-rate measurement is fixed at MEASURED_FPS.
    """
    def setUp(self):
        self.clients = []

        def make_client(*args, **kwargs):
            client = camera_tests.FakeClient()
            self.clients.append(client)
            return client

        self.sdk = SimpleNamespace(MightyClient=MagicMock(side_effect=make_client),
                                   MightyWebDevice=MagicMock())
        patcher = patch.dict('sys.modules', mighty_sdk=self.sdk)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.measure = patch.object(MightyCamera, 'measure_fps', return_value=MEASURED_FPS).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(MightyLink._links.clear)  # runs last: a failure cannot leak a link
        self.addCleanup(self.assertEqual, MightyLink._links, {})

    def car_config(self, template, **settings):
        """A fresh car directory made by `donkey createcar`, with settings in myconfig.py.

        Each test gets its own directory: a data tub left by another template
        has different fields and stops the tub writer.
        """
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = custom_template(d2_path(temp.name), template=template)
        with open(os.path.join(path, 'myconfig.py'), 'wt') as myconfig:
            for name, value in settings.items():
                myconfig.write(f'{name} = {value!r}\n')
        return dk.load_config(os.path.join(path, 'config.py'))

    def mighty_parts(self, vehicle):
        return [row for row in vehicle.parts if isinstance(row['part'], MightyCamera)]


class CompleteTemplateTests(MightyTemplateCase):
    def config(self, **settings):
        settings = dict(dict(CAMERA_TYPE='MIGHTY', IMAGE_W=160, IMAGE_H=100, IMAGE_DEPTH=1,
                             CAMERA_FRAMERATE=15), **settings)
        return self.car_config('complete', **settings)

    def test_template_config_has_the_mighty_settings(self):
        cfg = self.config()
        self.assertEqual(cfg.MIGHTY_URL, URL)
        self.assertEqual(cfg.MIGHTY_CAMERA_WARMUP_SECS, 5.0)
        self.assertEqual(cfg.MIGHTY_CAMERA_FPS_CHECK_SECS, 2.0)
        self.assertEqual(cfg.MIGHTY_READ_CHUNK_BYTES, 1024)

    def test_read_chunk_size_is_passed_through(self):
        camera = complete.get_camera(self.config(MIGHTY_READ_CHUNK_BYTES=4096))
        self.addCleanup(camera.shutdown)
        self.sdk.MightyWebDevice.assert_called_once_with(base_url=URL, read_chunk_size=4096)

    def test_get_camera_builds_a_mighty_camera_from_config(self):
        cfg = self.config(IMAGE_DEPTH=1, MIGHTY_CAMERA_WARMUP_SECS=2.5)
        camera = complete.get_camera(cfg)
        self.addCleanup(camera.shutdown)
        self.assertIsInstance(camera, MightyCamera)
        self.assertEqual(camera.url, URL)
        self.assertEqual(camera.size, (160, 100))
        self.assertEqual(camera.run_threaded().shape, (100, 160))
        self.assertEqual(camera.framerate, 15)
        self.measure.assert_called_once_with(2.0)
        self.sdk.MightyWebDevice.assert_called_once_with(base_url=URL, read_chunk_size=1024)

    def test_settings_default_when_an_older_config_lacks_them(self):
        cfg = SimpleNamespace(DONKEY_GYM=False, CAMERA_TYPE='MIGHTY',
                              IMAGE_W=320, IMAGE_H=200, IMAGE_DEPTH=1)
        camera = complete.get_camera(cfg)
        self.addCleanup(camera.shutdown)
        self.assertEqual(camera.url, URL)
        self.assertEqual(camera.link.read_chunk_size, 1024)
        self.assertEqual(camera.run_threaded().shape, (200, 320))
        self.assertIsNone(camera.framerate)
        self.measure.assert_not_called()

    def test_template_default_framerate_fails_with_the_fix(self):
        cfg = self.config(CAMERA_FRAMERATE=20)
        with self.assertRaisesRegex(CameraError, 'sending 17.8 fps.*CAMERA_FRAMERATE = 18,'):
            complete.get_camera(cfg)

    def test_fps_check_secs_is_passed_through(self):
        camera = complete.get_camera(self.config(MIGHTY_CAMERA_FPS_CHECK_SECS=0.5))
        self.addCleanup(camera.shutdown)
        self.measure.assert_called_once_with(0.5)

    def test_template_default_size_fails_with_the_fix(self):
        cfg = self.config(IMAGE_H=120)
        with self.assertRaisesRegex(CameraError, 'set IMAGE_W = 192 and IMAGE_H = 120'):
            complete.get_camera(cfg)

    def test_add_camera_publishes_cam_image_array(self):
        cfg = self.config(BGR2RGB=False)
        vehicle = VehicleGraph()
        complete.add_camera(vehicle, cfg, 'single')
        [row] = self.mighty_parts(vehicle)
        self.addCleanup(row['part'].shutdown)
        self.assertEqual(row['outputs'], ['cam/image_array'])
        self.assertTrue(row['threaded'])

    def test_template_defaults_give_every_fix_in_one_error(self):
        # complete's own defaults: 160x120, IMAGE_DEPTH 3, CAMERA_FRAMERATE 20.
        cfg = self.car_config('complete', CAMERA_TYPE='MIGHTY')
        self.assertEqual((cfg.IMAGE_W, cfg.IMAGE_H, cfg.IMAGE_DEPTH, cfg.CAMERA_FRAMERATE),
                         (160, 120, 3, 20))
        with self.assertRaises(CameraError) as caught:
            complete.get_camera(cfg)
        message = str(caught.exception)
        self.assertIn('3 settings in myconfig.py need changing', message)
        for fix in ['IMAGE_W = 192 and IMAGE_H = 120', 'set IMAGE_DEPTH = 1',
                    'CAMERA_FRAMERATE = 18,']:
            self.assertIn(fix, message)

    def test_drive_runs_with_the_mighty_camera(self):
        cfg = self.config(USE_SSD1306_128_32=False, DRIVE_TRAIN_TYPE='None')
        cfg.MAX_LOOPS = 10
        complete.drive(cfg=cfg)
        [client] = self.clients
        client.connect.assert_called_once()
        client.unsubscribe_image.assert_called_once()
        client.disconnect.assert_called_once()


class CvControlTemplateTests(MightyTemplateCase):
    def config(self, **settings):
        settings = dict(dict(CAMERA_TYPE='MIGHTY', IMAGE_W=320, IMAGE_H=200, IMAGE_DEPTH=1,
                             CAMERA_FRAMERATE=12), **settings)
        return self.car_config('cv_control', **settings)

    def test_template_config_has_the_mighty_settings(self):
        cfg = self.config()
        self.assertEqual(cfg.MIGHTY_URL, URL)
        self.assertEqual(cfg.MIGHTY_CAMERA_WARMUP_SECS, 5.0)
        self.assertEqual(cfg.MIGHTY_CAMERA_FPS_CHECK_SECS, 2.0)
        self.assertEqual(cfg.MIGHTY_READ_CHUNK_BYTES, 1024)

    def test_template_default_size_fails_with_the_fix(self):
        # cv_control's default 320x240 is 4:3.
        cfg = self.config(IMAGE_W=320, IMAGE_H=240)
        with self.assertRaisesRegex(CameraError, 'IMAGE_W = 384 and IMAGE_H = 240'):
            complete.get_camera(cfg)

    def test_drive_runs_with_the_mighty_camera(self):
        cfg = self.config(USE_SSD1306_128_32=False, DRIVE_TRAIN_TYPE='None')
        cfg.MAX_LOOPS = 10
        vehicle_class = dk.vehicle.Vehicle
        parts = []

        def record(*args, **kwargs):
            vehicle = vehicle_class(*args, **kwargs)
            add = vehicle.add
            vehicle.add = lambda part, *a, **k: (parts.append((part, k)), add(part, *a, **k))[1]
            return vehicle

        with patch.object(cv_control.dk.vehicle, 'Vehicle', side_effect=record):
            cv_control.drive(cfg)
        [(camera, options)] = [(p, k) for p, k in parts if isinstance(p, MightyCamera)]
        self.assertEqual(options['outputs'], ['cam/image_array'])
        self.assertEqual(camera.size, (320, 200))
        [client] = self.clients
        client.connect.assert_called_once()
        client.disconnect.assert_called_once()

    def test_mono_frames_never_match_the_default_line_colour(self):
        # Documents the config comment: LineFollower's default yellow HSV
        # range needs saturation >= 50, and the Mighty's frames are grey.
        import cv2
        import numpy as np
        cfg = self.config()
        camera = complete.get_camera(cfg)
        self.addCleanup(camera.shutdown)
        grey = camera.run_threaded()  # depth 1: the camera refuses 3 (D16)
        hsv = cv2.cvtColor(np.stack([grey] * 3, -1), cv2.COLOR_RGB2HSV)
        self.assertEqual(int(hsv[..., 1].max()), 0)
        mask = cv2.inRange(hsv, np.array(cfg.COLOR_THRESHOLD_LOW), np.array(cfg.COLOR_THRESHOLD_HIGH))
        self.assertEqual(int(mask.max()), 0)


if __name__ == '__main__':
    unittest.main()
