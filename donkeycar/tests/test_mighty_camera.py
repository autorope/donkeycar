"""Hardware-free coverage of the MightyCamera image part (plan commit 4)."""
from io import BytesIO
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from donkeycar.parts.camera import CameraError
from donkeycar.parts import mighty
from donkeycar.parts.mighty import (MightyCamera, MightyLink, MightyPose, RAW_BGR24, RAW_GRAY8,
                                    framerate_error, image_size_error, primary_image,
                                    size_fits, suggest_image_sizes, supported_framerate)

NATIVE = (640, 400)
URL = 'http://192.168.7.1'


def jpeg(width=640, height=400, split=None, value=128):
    """A grey JPEG; with split, columns left of it are black and the rest white."""
    pixels = np.full((height, width), value, np.uint8)
    if split is not None:
        pixels[:, :split] = 0
        pixels[:, split:] = 255
    out = BytesIO()
    Image.fromarray(pixels, 'L').convert('RGB').save(out, 'JPEG', quality=95)
    return {'kind': 'jpg', 'timestamp_ns': 1, 'channel': 'cam0', 'channel_alias': 'cam0',
            'is_reference': False, 'data': out.getvalue()}


class FakeClient:
    """Stands in for mighty_sdk.MightyClient: connect() delivers queued images."""
    def __init__(self, *args, **kwargs):
        self.image_callbacks = []
        self.on_connect_images = [jpeg()]
        self.connect = MagicMock(side_effect=self._connect)
        self.disconnect = MagicMock()
        self.unsubscribe_image = MagicMock()
        for name in ['on_pose', 'on_vio_state', 'on_reset', 'on_error']:
            setattr(self, name, MagicMock())

    def _connect(self):
        for image in self.on_connect_images:
            self.emit(image)

    def on_image(self, callback):
        self.image_callbacks.append(callback)
        return self.unsubscribe_image

    def emit(self, image):
        for callback in list(self.image_callbacks):
            callback(image)


class SizeRuleTests(unittest.TestCase):
    def test_sizes_with_the_camera_shape_fit(self):
        for size in [(8, 5), (160, 100), (320, 200), (640, 400)]:
            with self.subTest(size=size):
                self.assertTrue(size_fits(*size, NATIVE))
                self.assertIsNone(image_size_error(*size, NATIVE))

    def test_default_size_suggests_most_pixels_then_full_frame(self):
        self.assertEqual(suggest_image_sizes(160, 120, NATIVE),
                         [((192, 120), 'keeps your height'), (NATIVE, 'the full frame')])
        message = image_size_error(160, 120, NATIVE)
        self.assertEqual(message,
                         'MightyCamera cannot return IMAGE_W=160, IMAGE_H=120 without stretching: '
                         'the camera sends 640x400 (16:10). In myconfig.py set IMAGE_W = 192 and '
                         'IMAGE_H = 120 (keeps your height), or IMAGE_W = 640 and IMAGE_H = 400 '
                         '(the full frame). Any 16:10 size up to 640x400 works.')

    def test_candidate_rules(self):
        cases = {
            (200, 100): [((200, 125), 'keeps your width'), (NATIVE, 'the full frame')],
            (170, 110): [((176, 110), 'keeps your height'), (NATIVE, 'the full frame')],
            (1000, 120): [(NATIVE, 'the full frame')],
            (4, 2): [((8, 5), 'the smallest size'), (NATIVE, 'the full frame')],
            (163, 99): [((160, 100), 'the largest that fits your width'),
                        (NATIVE, 'the full frame')],
        }
        for request, expected in cases.items():
            with self.subTest(request=request):
                self.assertEqual(suggest_image_sizes(*request, NATIVE), expected)

    def test_tie_prefers_the_width_candidate(self):
        # Equal pixel counts means both candidates are the same size; the
        # width candidate's label is the one reported.
        self.assertEqual(suggest_image_sizes(163, 103, NATIVE)[0],
                         ((160, 100), 'the largest that fits your width'))

    def test_too_large_and_non_positive_are_rejected(self):
        self.assertIn("larger than the camera's frames", image_size_error(1280, 800, NATIVE))
        self.assertIn('IMAGE_W = 640 and IMAGE_H = 400 (the full frame)',
                      image_size_error(1280, 800, NATIVE))
        for size in [(0, 0), (-160, -100), (160, 0)]:
            with self.subTest(size=size):
                self.assertFalse(size_fits(*size, NATIVE))
                self.assertIsNotNone(image_size_error(*size, NATIVE))


class PrimaryImageTests(unittest.TestCase):
    def test_selection_matches_the_sdk(self):
        image = jpeg()
        self.assertIs(primary_image(image), image)
        self.assertIsNone(primary_image(dict(image, is_reference=True)))
        self.assertIsNone(primary_image(dict(image, dropped=True)))
        self.assertIsNone(primary_image({'kind': 'depth'}))
        self.assertIsNone(primary_image(None))
        right = dict(jpeg(), channel='cam1', channel_alias='right')
        left = dict(jpeg(), channel='cam0', channel_alias='left')
        self.assertIs(primary_image({'kind': 'stereo_jpg', 'left': right, 'right': left}), left)
        self.assertIs(primary_image({'kind': 'stereo_raw', 'left': right, 'right': {}}), right)


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.clients = []

        def make_client(*args, **kwargs):
            client = FakeClient()
            client.on_connect_images = list(self.initial)
            self.clients.append(client)
            return client

        self.initial = [jpeg()]
        self.sdk = SimpleNamespace(MightyClient=MagicMock(side_effect=make_client),
                                   MightyWebDevice=MagicMock())
        patcher = patch.dict('sys.modules', mighty_sdk=self.sdk)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.assertEqual, MightyLink._links, {})

    def camera(self, **kwargs):
        kwargs.setdefault('image_w', 160)
        kwargs.setdefault('image_h', 100)
        camera = MightyCamera(URL, warmup_secs=kwargs.pop('warmup_secs', 1.0), **kwargs)
        self.addCleanup(camera.shutdown)
        return camera

    def test_depth_three_is_rgb_at_the_configured_size(self):
        frame = self.camera(image_d=3).run_threaded()
        self.assertEqual(frame.shape, (100, 160, 3))
        self.assertEqual(frame.dtype, np.uint8)
        self.assertTrue((frame[..., 0] == frame[..., 1]).all())
        self.assertTrue((frame[..., 1] == frame[..., 2]).all())

    def test_depth_one_is_mono(self):
        frame = self.camera(image_d=1).run_threaded()
        self.assertEqual(frame.shape, (100, 160))

    def test_full_frame_when_size_is_none(self):
        camera = self.camera(image_w=None, image_h=None)
        self.assertEqual(camera.size, NATIVE)
        self.assertEqual(camera.run_threaded().shape, (400, 640, 3))

    def test_scaling_keeps_geometry(self):
        self.initial = [jpeg(split=320)]
        frame = self.camera(image_w=160, image_h=100, image_d=1).run_threaded()
        self.assertLess(frame[:, :78].max(), 30)
        self.assertGreater(frame[:, 82:].min(), 225)

    def test_newest_frame_wins(self):
        camera = self.camera(image_d=1)
        client = self.clients[0]
        for value in (10, 120, 240):
            client.emit(jpeg(value=value))
        self.assertTrue(camera.poll())
        self.assertAlmostEqual(float(camera.run_threaded().mean()), 240, delta=3)
        self.assertFalse(camera.poll())

    def test_run_polls_without_a_thread(self):
        camera = self.camera(image_d=1)
        self.clients[0].emit(jpeg(value=40))
        self.assertAlmostEqual(float(camera.run().mean()), 40, delta=3)

    def test_unsupported_size_fails_with_the_fix_and_releases(self):
        with self.assertRaises(CameraError) as caught:
            MightyCamera(URL, image_w=160, image_h=120, warmup_secs=1.0)
        self.assertIn('IMAGE_W = 192 and IMAGE_H = 120', str(caught.exception))
        self.clients[0].unsubscribe_image.assert_called_once()
        self.clients[0].disconnect.assert_called_once()

    def test_warmup_timeout_fails_and_releases(self):
        self.initial = []
        with self.assertRaisesRegex(CameraError, 'no image from http://192.168.7.1 within 0.05 s'):
            MightyCamera(URL, image_w=160, image_h=100, warmup_secs=0.05)
        self.clients[0].disconnect.assert_called_once()

    def test_raw_gray_and_bgr_frames(self):
        gray = {'kind': 'raw', 'width': 640, 'height': 400, 'format': RAW_GRAY8,
                'data': bytes([77]) * (640 * 400)}
        self.initial = [gray]
        self.assertEqual(int(self.camera(image_d=1).run_threaded()[0, 0]), 77)
        bgr = np.zeros((400, 640, 3), np.uint8)
        bgr[..., 0] = 200  # blue, in BGR order
        picture = mighty.open_image({'kind': 'raw', 'width': 640, 'height': 400,
                                     'format': RAW_BGR24, 'data': bgr.tobytes()})
        self.assertEqual(picture.getpixel((0, 0)), (0, 0, 200))

    def test_stereo_frames_publish_the_left_camera(self):
        left = dict(jpeg(value=30), channel_alias='left')
        right = dict(jpeg(value=220), channel_alias='right')
        self.initial = [{'kind': 'stereo_jpg', 'left': right, 'right': left}]
        frame = self.camera(image_d=1).run_threaded()
        self.assertAlmostEqual(float(frame.mean()), 30, delta=3)

    def test_size_change_mid_run_is_dropped_and_logged_once(self):
        camera = self.camera(image_d=1)
        before = camera.run_threaded().copy()
        with self.assertLogs('donkeycar.parts.mighty', 'ERROR') as logs:
            for _ in range(2):
                self.clients[0].emit(jpeg(width=320, height=240, value=250))
                self.assertFalse(camera.poll())
        self.assertEqual(len(logs.records), 1)
        self.assertIn('dropping them rather than stretching', logs.output[0])
        self.assertTrue((camera.run_threaded() == before).all())

    def test_stale_frames_warn_once(self):
        camera = self.camera()
        later = camera.received_at + 5
        with patch('donkeycar.parts.mighty.time.monotonic', return_value=later):
            with self.assertLogs('donkeycar.parts.mighty', 'WARNING') as logs:
                camera.poll()
                camera.poll()
        self.assertEqual(len(logs.records), 1)
        self.assertIsNotNone(camera.run_threaded())

    def test_shutdown_releases_and_shares_with_pose(self):
        with tempfile.TemporaryDirectory() as logs:
            pose = MightyPose(url=URL, log_directory=logs)
            camera = self.camera()
            self.assertIs(pose.client, camera.client)
            self.assertEqual(len(self.clients), 1)
            pose.link.connect()
            client = self.clients[0]
            client.connect.assert_called_once()
            camera.shutdown()
            camera.shutdown()
            client.unsubscribe_image.assert_called_once()
            client.disconnect.assert_not_called()
            pose.shutdown()
            client.disconnect.assert_called_once()

    def test_update_loop_stops(self):
        camera = self.camera()
        camera.running = False
        camera.update()

    def test_invalid_arguments(self):
        for kwargs in [dict(image_d=2), dict(warmup_secs=0), dict(stale_secs=float('nan'))]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MightyCamera(URL, **kwargs)

    def test_missing_sdk_names_the_install(self):
        with patch.dict('sys.modules', mighty_sdk=None):
            with self.assertRaisesRegex(ImportError, 'mighty-protocol'):
                MightyCamera(URL, image_w=160, image_h=100)


class FramerateRuleTests(unittest.TestCase):
    def test_rates_within_five_percent_of_the_measured_rate_pass(self):
        # 15 at 14.98 fps is Ed's case: it printed "sending 15.0 fps" and failed.
        for requested, measured in [(17, 17.8), (18, 17.8), (15, 17.8), (0.5, 17.8),
                                    (14, 14.0), (15, 14.98), (15, 14.3), (21, 20.0)]:
            with self.subTest(requested=requested, measured=measured):
                self.assertIsNone(framerate_error(requested, measured))

    def test_too_high_a_rate_suggests_the_largest_that_passes(self):
        self.assertEqual(framerate_error(20, 17.8),
                         'MightyCamera cannot deliver CAMERA_FRAMERATE = 20: the camera is sending '
                         '17.8 fps. The camera sets its own rate, and it drops to about 15 fps '
                         'while VIO runs. In myconfig.py set CAMERA_FRAMERATE = 18, or anything '
                         'lower.')
        self.assertIn('CAMERA_FRAMERATE = 14,', framerate_error(15, 14.2))
        self.assertIn('CAMERA_FRAMERATE = 15,', framerate_error(16, 14.5))

    def test_a_shown_rate_always_passes_as_its_own_suggestion(self):
        # Whatever rate the message shows (to 0.1 fps), the suggestion passes
        # and is never below the shown rate rounded down.
        for tenths in range(20, 400):  # below about 1 fps the message says to check the camera
            measured = tenths / 10 - 0.049
            suggestion = supported_framerate(measured)
            with self.subTest(measured=measured):
                self.assertIsNone(framerate_error(suggestion, measured))
                self.assertIsNotNone(framerate_error(suggestion + 1, measured))
                self.assertGreaterEqual(suggestion, int(round(measured, 1)))

    def test_a_stalled_camera_says_to_check_it(self):
        message = framerate_error(20, 0.4)
        self.assertIn('sending only 0.4 fps', message)
        self.assertIn('Check the camera connection', message)


class FramerateCameraTests(unittest.TestCase):
    """The frame-rate check and pacing, with a controllable clock (plan D14)."""
    def setUp(self):
        self.clients = []

        def make_client(*args, **kwargs):
            client = FakeClient()
            self.clients.append(client)
            return client

        self.sdk = SimpleNamespace(MightyClient=MagicMock(side_effect=make_client),
                                   MightyWebDevice=MagicMock())
        patch.dict('sys.modules', mighty_sdk=self.sdk).start()
        self.now = 100.0
        patch('donkeycar.parts.mighty.time.monotonic', side_effect=lambda: self.now).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.assertEqual, MightyLink._links, {})

    def camera(self, framerate, measured=17.8):
        with patch.object(MightyCamera, 'measure_fps', return_value=measured) as measure:
            camera = MightyCamera(URL, image_w=160, image_h=100, image_d=1,
                                  warmup_secs=1.0, framerate=framerate, fps_check_secs=0.25)
        measure.assert_called_once_with(0.25)
        self.addCleanup(camera.shutdown)
        return camera

    def emit(self, value=128, count=1, **changes):
        # Frames arrive during a window, never at the instant it opens.
        for _ in range(count):
            self.now += 1e-6
            self.clients[0].emit(dict(jpeg(value=value), **changes))

    def test_too_high_a_rate_fails_at_startup_and_releases(self):
        with self.assertRaisesRegex(CameraError, 'CAMERA_FRAMERATE = 18, or anything lower'):
            self.camera(framerate=20)
        self.clients[0].disconnect.assert_called_once()

    def test_supported_rate_starts(self):
        camera = self.camera(framerate=17)
        self.assertEqual(camera.measured_fps, 17.8)
        self.assertEqual(camera.run_threaded().shape, (100, 160))

    def test_measure_fps_uses_camera_timestamps_not_bursty_arrivals(self):
        # As on the car (F14): captured at 15 fps, handed over three at a time.
        camera = self.camera(framerate=10)
        self.now += 1  # leave the warm-up frame before the window

        def sleep(seconds):
            stamp = 5_000_000_000
            for burst in range(10):
                self.now += 0.2
                for _ in range(3):
                    self.emit(timestamp_ns=stamp)
                    stamp += 1_000_000_000 // 15
            self.now += seconds - 2.0

        with patch('donkeycar.parts.mighty.time.sleep', side_effect=sleep):
            self.assertAlmostEqual(camera.measure_fps(2.0), 15.0, places=3)

    def test_measure_fps_without_timestamps_counts_frames(self):
        camera = self.camera(framerate=10)
        self.now += 1

        def sleep(seconds):
            self.emit(count=30, timestamp_ns=0)
            self.now += seconds

        with patch('donkeycar.parts.mighty.time.sleep', side_effect=sleep):
            self.assertAlmostEqual(camera.measure_fps(2.0), 15.0, places=3)

    def test_measure_fps_with_too_few_frames_counts_them(self):
        camera = self.camera(framerate=10)
        self.now += 1  # leave the warm-up frame before the window

        def sleep(seconds):
            self.emit()
            self.now += seconds

        with patch('donkeycar.parts.mighty.time.sleep', side_effect=sleep):
            self.assertAlmostEqual(camera.measure_fps(2.0), 0.5, places=3)

    def test_publishes_at_most_framerate_and_keeps_early_frames(self):
        camera = self.camera(framerate=10)  # due every 0.09 s after a publish
        self.emit(value=40)
        self.now += 0.05
        self.assertFalse(camera.poll())
        self.emit(value=200)  # newer frame replaces the early one
        self.now += 0.04
        self.assertGreater(camera.seconds_until_due(self.now - 0.001), 0)
        self.assertTrue(camera.poll())
        self.assertAlmostEqual(float(camera.run_threaded().mean()), 200, delta=3)

    def test_a_camera_matching_framerate_loses_no_frames(self):
        camera = self.camera(framerate=15)
        published = 0
        for jitter in [0.0, -0.006, 0.006, -0.006, 0.0, 0.004, -0.005, 0.0]:
            self.now += 1 / 15 + jitter
            self.emit()
            published += camera.poll()
        self.assertEqual(published, 8)

    def test_no_framerate_means_no_pacing(self):
        with patch.object(MightyCamera, 'measure_fps') as measure:
            camera = MightyCamera(URL, image_w=160, image_h=100, warmup_secs=1.0)
        self.addCleanup(camera.shutdown)
        measure.assert_not_called()
        self.emit()
        self.assertTrue(camera.poll())
        self.emit()
        self.assertTrue(camera.poll())

    def test_slow_camera_warns_once_then_recovers(self):
        camera = self.camera(framerate=17)
        camera.poll()  # opens the first rate window
        with self.assertLogs('donkeycar.parts.mighty', 'INFO') as logs:
            for rate in (14, 14, 17):
                self.emit(count=rate * 5)
                self.now += 5
                camera.poll()
        warnings = [r for r in logs.records if r.levelname == 'WARNING']
        self.assertEqual(len(warnings), 1)
        self.assertIn('now sending 14.0 fps, below CAMERA_FRAMERATE = 17', warnings[0].getMessage())
        self.assertIn('Set CAMERA_FRAMERATE = 14 or lower', warnings[0].getMessage())
        self.assertTrue(any('frame rate back to 17.0 fps' in r.getMessage() for r in logs.records))

    def test_a_rate_just_under_framerate_does_not_warn(self):
        camera = self.camera(framerate=15)
        camera.poll()
        with patch.object(mighty.logger, 'warning') as warning:
            self.emit(count=74)  # 14.8 fps over the 5 s window
            self.now += 5
            camera.poll()
        warning.assert_not_called()

    def test_invalid_rate_arguments(self):
        for kwargs in [dict(framerate=0), dict(framerate=-5), dict(framerate=float('nan')),
                       dict(fps_check_secs=0), dict(fps_check_secs=float('inf'))]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MightyCamera(URL, **kwargs)


class SnapshotCliTests(unittest.TestCase):
    def setUp(self):
        self.sdk = SimpleNamespace(MightyClient=MagicMock(side_effect=lambda *a, **k: FakeClient()),
                                   MightyWebDevice=MagicMock())
        patcher = patch.dict('sys.modules', mighty_sdk=self.sdk)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.assertEqual, MightyLink._links, {})
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_snapshot_saves_frame_and_reports(self):
        out = os.path.join(self.temp.name, 'frame.jpg')
        with patch('builtins.print') as printed:
            code = mighty.main(['snapshot', '--out', out, '--seconds', '0.05',
                                '--width', '160', '--height', '100'])
        self.assertEqual(code, 0)
        with Image.open(out) as saved:
            self.assertEqual(saved.size, (160, 100))
        self.assertIn('Camera frames 640x400 (16:10); saved 160x100 depth 3', printed.call_args[0][0])

    def test_snapshot_full_frame_by_default(self):
        out = os.path.join(self.temp.name, 'full.jpg')
        with patch('builtins.print'):
            self.assertEqual(mighty.main(['snapshot', '--out', out, '--seconds', '0.05']), 0)
        with Image.open(out) as saved:
            self.assertEqual(saved.size, NATIVE)

    def test_snapshot_bad_size_prints_the_fix(self):
        out = os.path.join(self.temp.name, 'never.jpg')
        with patch('builtins.print') as printed:
            code = mighty.main(['snapshot', '--out', out, '--width', '160', '--height', '120'])
        self.assertEqual(code, 1)
        self.assertIn('IMAGE_W = 192 and IMAGE_H = 120', str(printed.call_args[0][0]))
        self.assertFalse(os.path.exists(out))

    def test_snapshot_framerate_check_prints_the_fix(self):
        out = os.path.join(self.temp.name, 'never.jpg')
        with patch('builtins.print') as printed, \
                patch.object(MightyCamera, 'measure_fps', return_value=14.8):
            code = mighty.main(['snapshot', '--out', out, '--width', '160', '--height', '100',
                                '--framerate', '20'])
        self.assertEqual(code, 1)
        self.assertIn('CAMERA_FRAMERATE = 15, or anything lower', str(printed.call_args[0][0]))
        self.assertFalse(os.path.exists(out))


if __name__ == '__main__':
    unittest.main()
