import unittest
from unittest import mock

import numpy as np
import tensorflow as tf

from donkeycar.parts.tta import photometric_batch, TTAStabilityDetector
from donkeycar.parts.mc_calibrate import build_calibration


def _tiny_pilot():
    """Minimal single-image-input, two-output (angle/throttle) model wrapped in
    a stub pilot exposing .interpreter.model / .interpreter.input_keys, the
    surface TTAStabilityDetector reaches for."""
    tf.random.set_seed(0)
    inp = tf.keras.Input((16, 16, 3), name='img_in')
    x = tf.keras.layers.Conv2D(4, 3, activation='relu')(inp)
    x = tf.keras.layers.Flatten()(x)
    angle = tf.keras.layers.Dense(1, name='angle')(x)
    throttle = tf.keras.layers.Dense(1, name='throttle')(x)
    model = tf.keras.Model(inp, [angle, throttle])

    class _Interp:
        def __init__(self, m):
            self.model = m
            self.input_keys = ['img_in']

    class _Pilot:
        def __init__(self, m):
            self.interpreter = _Interp(m)

    return _Pilot(model)


class TestPhotometricBatch(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(0)
        self.img = self.rng.random((16, 16, 3)).astype(np.float32)

    def test_shape_and_range(self):
        batch = photometric_batch(self.img, 8, 0.2, self.rng)
        self.assertEqual(batch.shape, (8, 16, 16, 3))
        self.assertGreaterEqual(batch.min(), 0.0)
        self.assertLessEqual(batch.max(), 1.0)

    def test_zero_strength_is_identity(self):
        batch = photometric_batch(self.img, 5, 0.0, self.rng)
        for m in range(5):
            np.testing.assert_allclose(batch[m], self.img, atol=1e-6)

    def test_higher_strength_gives_more_variance(self):
        weak = photometric_batch(self.img, 16, 0.05, np.random.default_rng(1))
        strong = photometric_batch(self.img, 16, 0.4, np.random.default_rng(1))
        self.assertGreater(strong.var(axis=0).mean(), weak.var(axis=0).mean())

    def test_geometry_is_preserved(self):
        # A bright top half vs dark bottom half must stay that way for every
        # augmented copy -- photometric augmentation never moves content.
        img = np.zeros((16, 16, 3), dtype=np.float32)
        img[:8] = 0.9
        img[8:] = 0.1
        batch = photometric_batch(img, 8, 0.2, np.random.default_rng(2))
        for m in range(8):
            self.assertGreater(batch[m, :8].mean(), batch[m, 8:].mean())


class TestTTAStabilityDetector(unittest.TestCase):

    def setUp(self):
        self.pilot = _tiny_pilot()
        self.img = (np.random.default_rng(3).random((16, 16, 3)) * 255).astype(np.uint8)

    def test_run_returns_three_values_and_nonneg_variance(self):
        part = TTAStabilityDetector(self.pilot, num_samples=8, strength=0.2,
                                    seed=0)
        stability, raw_var, smoothed_var = part.run(self.img)
        self.assertIsNone(stability)          # no calibration loaded
        self.assertGreaterEqual(raw_var, 0.0)
        self.assertGreaterEqual(smoothed_var, 0.0)

    def test_none_frame_passthrough(self):
        part = TTAStabilityDetector(self.pilot, seed=0)
        stability, raw_var, smoothed_var = part.run(None)
        self.assertIsNone(stability)
        self.assertEqual(raw_var, 0.0)

    def test_uncalibrated_skips_the_forward_pass_entirely(self):
        # Without a calibration block there's nothing to score against, so
        # the M-pass batch should never actually run (mirrors
        # FeatureNoveltyDetector) -- important on a Pi, where this would
        # otherwise burn M forward passes every frame for a number nobody
        # can read.
        part = TTAStabilityDetector(self.pilot, num_samples=8, seed=0)
        self.assertIsNone(part.calibration)
        calls = {'n': 0}
        real_model = part.model

        def counting_call(*a, **kw):
            calls['n'] += 1
            return real_model(*a, **kw)

        part.model = counting_call
        stability, raw_var, smoothed_var = part.run(self.img)
        self.assertEqual(calls['n'], 0)
        self.assertIsNone(stability)
        self.assertEqual(raw_var, 0.0)
        self.assertEqual(smoothed_var, 0.0)

    def test_always_measure_runs_the_pass_even_without_calibration(self):
        # Calibration is the one caller that MUST measure while uncalibrated
        # -- measuring those variances is how the 'tta' block gets built. If
        # the skip above applied there too, every collected variance would be
        # 0.0 and the resulting block would be degenerate.
        part = TTAStabilityDetector(self.pilot, num_samples=8, seed=0,
                                    always_measure=True)
        self.assertIsNone(part.calibration)
        calls = {'n': 0}
        real_model = part.model

        def counting_call(*a, **kw):
            calls['n'] += 1
            return real_model(*a, **kw)

        part.model = counting_call
        stability, raw_var, smoothed_var = part.run(self.img)
        self.assertEqual(calls['n'], 1)       # the M-pass batch DID run
        self.assertIsNone(stability)          # still no score without calib
        self.assertGreater(raw_var, 0.0)      # and a real variance came back

    def test_always_measure_defaults_off_so_live_driving_is_unchanged(self):
        part = TTAStabilityDetector(self.pilot, num_samples=8, seed=0)
        self.assertFalse(part.always_measure)

    def test_stability_uses_calibration_block_when_present(self):
        part = TTAStabilityDetector(self.pilot, num_samples=8, seed=0)
        # Attach a real tta block built from a synthetic variance distribution.
        rng = np.random.default_rng(4)
        calib = build_calibration(
            rng.gamma(2.0, 0.01, 200), num_passes=15, alpha=0.2,
            tta_variances=rng.gamma(2.0, 1e-4, 200),
            tta_num_samples=8, tta_strength=0.2, tta_alpha=0.2)
        part.calibration = calib['tta']
        part.run(self.img)
        score = part._score()
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)


class TestTTAStabilityDetectorInterval(unittest.TestCase):
    # TTA costs M forward passes per update -- the most expensive of the
    # three signals per update -- so an unthrottled live loop adds real load
    # (and, on power-constrained hardware like a Pi, real power draw) with no
    # way to turn it down. This is the interval knob that closes that gap.

    def setUp(self):
        self.pilot = _tiny_pilot()
        self.img = (np.random.default_rng(6).random((16, 16, 3)) * 255).astype(np.uint8)

    def _counting_part(self, interval):
        part = TTAStabilityDetector(self.pilot, num_samples=4,
                                    interval=interval, seed=0)
        # The interval-skip logic and the uncalibrated-skip logic are
        # independent gates on the same forward pass -- attach a minimal
        # calibration block so these tests exercise the interval gate alone.
        part.calibration = {
            'stability_anchors': {'variance': [0.0, 1.0], 'stability': [99.0, 5.0]},
        }
        calls = {'n': 0}
        real_model = part.model

        def counting_call(*a, **kw):
            calls['n'] += 1
            return real_model(*a, **kw)

        part.model = counting_call
        return part, calls

    def test_zero_interval_runs_forward_pass_every_frame(self):
        part, calls = self._counting_part(interval=0.0)
        part.run(self.img)
        part.run(self.img)
        part.run(self.img)
        self.assertEqual(calls['n'], 3)

    def test_interval_skips_forward_pass_when_held(self):
        part, calls = self._counting_part(interval=1.0)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=100.0):
            part.run(self.img)
        self.assertEqual(calls['n'], 1)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=100.5):
            part.run(self.img)   # within interval -> held, NO forward pass
        self.assertEqual(calls['n'], 1)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=101.5):
            part.run(self.img)   # past interval -> recompute
        self.assertEqual(calls['n'], 2)

    def test_held_values_match_last_real_update(self):
        part, _ = self._counting_part(interval=1.0)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=100.0):
            _, raw1, smoothed1 = part.run(self.img)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=100.3):
            _, raw2, smoothed2 = part.run(self.img)
        self.assertEqual(raw1, raw2)
        self.assertEqual(smoothed1, smoothed2)

    def test_now_override_drives_the_interval_gate_without_mocking_time(self):
        # mc_calibrate.calibrate_from_tub replays a tub through this part
        # passing now= from each frame's own recorded timestamp, so the
        # interval gate reflects the tub's real recorded pace rather than
        # however fast the replay loop happens to run. No time.time mocking
        # needed -- that's the point of the parameter.
        part, calls = self._counting_part(interval=1.0)
        part.run(self.img, now=100.0)
        self.assertEqual(calls['n'], 1)
        part.run(self.img, now=100.5)   # < 1.0s since the last update -> held
        self.assertEqual(calls['n'], 1)
        part.run(self.img, now=101.5)   # >= 1.0s since the last update
        self.assertEqual(calls['n'], 2)

    def test_now_none_falls_back_to_wall_clock(self):
        # Every other caller (the live drive loop, gradcam_uncertainty.py's
        # replay) doesn't pass now= at all -- must behave exactly as before.
        part, calls = self._counting_part(interval=1.0)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=200.0):
            part.run(self.img)
        with mock.patch('donkeycar.parts.tta.time.time', return_value=200.2):
            part.run(self.img)
        self.assertEqual(calls['n'], 1)


if __name__ == '__main__':
    unittest.main()
