import unittest
from unittest import mock

import numpy as np
import tensorflow as tf

from donkeycar.parts.mc_dropout import MCDropoutConfidence


def _tiny_dropout_pilot():
    """Minimal single-image-input, two-output (angle/throttle) model with a
    real Dropout layer, wrapped in a stub pilot exposing .interpreter.model /
    .interpreter.input_keys AND a .run() method -- the surface
    MCDropoutConfidence reaches for (the latter is used on held/interval
    frames, which fall back to a cheap single deterministic pass via
    pilot.run() rather than the N-pass stochastic batch)."""
    tf.random.set_seed(0)
    inp = tf.keras.Input((16, 16, 3), name='img_in')
    x = tf.keras.layers.Conv2D(4, 3, activation='relu')(inp)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
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

        def run(self, img_arr, *other_arr):
            from donkeycar.utils import normalize_image
            norm = normalize_image(img_arr).astype(np.float32)
            out = self.interpreter.model(
                {'img_in': tf.convert_to_tensor(norm[np.newaxis, ...])},
                training=False)
            return float(np.asarray(out[0]).reshape(-1)[0]), \
                float(np.asarray(out[1]).reshape(-1)[0])

    return _Pilot(model)


class TestMCDropoutConfidenceInterval(unittest.TestCase):
    # Mirrors TestTTAStabilityDetectorInterval / TestFeatureNoveltyDetector
    # Interval in test_tta.py / test_novelty.py -- MCDropoutConfidence is the
    # third of the three signals mc_calibrate.calibrate_from_tub now replays
    # at the tub's own recorded cadence via the same now= override.

    def setUp(self):
        self.pilot = _tiny_dropout_pilot()
        self.img = (np.random.default_rng(0).random((16, 16, 3))
                   * 255).astype(np.uint8)

    def _counting_part(self, interval):
        part = MCDropoutConfidence(self.pilot, num_passes=4,
                                   interval=interval)
        calls = {'n': 0}
        real_model = part.model

        def counting_call(*a, **kw):
            calls['n'] += 1
            return real_model(*a, **kw)

        part.model = counting_call
        return part, calls

    def test_zero_interval_runs_stochastic_pass_every_frame(self):
        part, calls = self._counting_part(interval=0.0)
        part.run(self.img); part.run(self.img); part.run(self.img)
        self.assertEqual(calls['n'], 3)

    def test_now_override_drives_the_interval_gate_without_mocking_time(self):
        part, calls = self._counting_part(interval=1.0)
        part.run(self.img, now=100.0)
        self.assertEqual(calls['n'], 1)
        part.run(self.img, now=100.5)   # < 1.0s since the last update -> held
        self.assertEqual(calls['n'], 1)
        part.run(self.img, now=101.5)   # >= 1.0s since the last update
        self.assertEqual(calls['n'], 2)

    def test_held_smoothed_variance_matches_last_real_update(self):
        part, _ = self._counting_part(interval=1.0)
        _, _, _, _, smoothed1 = part.run(self.img, now=100.0)
        _, _, _, _, smoothed2 = part.run(self.img, now=100.3)   # held
        self.assertEqual(smoothed1, smoothed2)

    def test_now_none_falls_back_to_wall_clock(self):
        part, calls = self._counting_part(interval=1.0)
        with mock.patch('donkeycar.parts.mc_dropout.time.time',
                        return_value=200.0):
            part.run(self.img)
        with mock.patch('donkeycar.parts.mc_dropout.time.time',
                        return_value=200.2):
            part.run(self.img)
        self.assertEqual(calls['n'], 1)


if __name__ == '__main__':
    unittest.main()
