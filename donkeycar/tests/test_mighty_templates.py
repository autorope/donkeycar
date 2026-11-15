"""CAMERA_TYPE = "MIGHTY" in each template, with the Mighty SDK mocked (plan commits 5, 6 and 7-9)."""
import os
from tempfile import gettempdir
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import donkeycar as dk
from donkeycar.parts.camera import CameraError
from donkeycar.parts.mighty import MightyCamera, MightyLink
from donkeycar.templates import complete
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
        self.addCleanup(self.assertEqual, MightyLink._links, {})

    def car_config(self, template, **settings):
        """A car directory made by `donkey createcar`, with settings in myconfig.py."""
        path = custom_template(d2_path(gettempdir()), template=template)
        with open(os.path.join(path, 'myconfig.py'), 'wt') as myconfig:
            for name, value in settings.items():
                myconfig.write(f'{name} = {value!r}\n')
        return dk.load_config(os.path.join(path, 'config.py'))

    def mighty_parts(self, vehicle):
        return [row for row in vehicle.parts if isinstance(row['part'], MightyCamera)]


class CompleteTemplateTests(MightyTemplateCase):
    def config(self, **settings):
        settings = dict(dict(CAMERA_TYPE='MIGHTY', IMAGE_W=160, IMAGE_H=100,
                             CAMERA_FRAMERATE=15), **settings)
        return self.car_config('complete', **settings)

    def test_template_config_has_the_mighty_settings(self):
        cfg = self.config()
        self.assertEqual(cfg.MIGHTY_URL, URL)
        self.assertEqual(cfg.MIGHTY_CAMERA_WARMUP_SECS, 5.0)
        self.assertEqual(cfg.MIGHTY_CAMERA_FPS_CHECK_SECS, 2.0)

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
        self.sdk.MightyWebDevice.assert_called_once_with(base_url=URL)

    def test_settings_default_when_an_older_config_lacks_them(self):
        cfg = SimpleNamespace(DONKEY_GYM=False, CAMERA_TYPE='MIGHTY',
                              IMAGE_W=320, IMAGE_H=200, IMAGE_DEPTH=3)
        camera = complete.get_camera(cfg)
        self.addCleanup(camera.shutdown)
        self.assertEqual(camera.url, URL)
        self.assertEqual(camera.run_threaded().shape, (200, 320, 3))
        self.assertIsNone(camera.framerate)
        self.measure.assert_not_called()

    def test_template_default_framerate_fails_with_the_fix(self):
        cfg = self.config(CAMERA_FRAMERATE=20)
        with self.assertRaisesRegex(CameraError, 'sending 17.8 fps.*CAMERA_FRAMERATE = 17,'):
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

    def test_drive_runs_with_the_mighty_camera(self):
        cfg = self.config(USE_SSD1306_128_32=False, DRIVE_TRAIN_TYPE='None')
        cfg.MAX_LOOPS = 10
        complete.drive(cfg=cfg)
        [client] = self.clients
        client.connect.assert_called_once()
        client.unsubscribe_image.assert_called_once()
        client.disconnect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
