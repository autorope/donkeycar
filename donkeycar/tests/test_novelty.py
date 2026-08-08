import unittest
from unittest import mock

import numpy as np

from donkeycar.parts.novelty import (mahalanobis_diag, fit_diagonal_gaussian,
                                     FeatureNoveltyDetector)


class TestMahalanobisDiag(unittest.TestCase):

    def test_zero_at_mean(self):
        mean = np.zeros(5)
        var = np.ones(5)
        self.assertAlmostEqual(mahalanobis_diag(mean, mean, var), 0.0, places=6)

    def test_increases_with_distance(self):
        mean = np.zeros(5)
        var = np.ones(5)
        near = mahalanobis_diag(np.full(5, 0.1), mean, var)
        far = mahalanobis_diag(np.full(5, 5.0), mean, var)
        self.assertGreater(far, near)

    def test_active_dims_excludes_dimension(self):
        mean = np.zeros(3)
        var = np.ones(3)
        vec = np.array([0.0, 0.0, 100.0])  # huge deviation, only in dim 2
        active_all = np.array([True, True, True])
        active_excl_dim2 = np.array([True, True, False])
        dist_all = mahalanobis_diag(vec, mean, var, active_all)
        dist_excl = mahalanobis_diag(vec, mean, var, active_excl_dim2)
        self.assertAlmostEqual(dist_excl, 0.0, places=6)
        self.assertGreater(dist_all, dist_excl)

    def test_batched_input_returns_one_distance_per_row(self):
        mean = np.zeros(4)
        var = np.ones(4)
        batch = np.stack([np.zeros(4), np.ones(4)])
        distances = mahalanobis_diag(batch, mean, var)
        self.assertEqual(distances.shape, (2,))
        self.assertAlmostEqual(distances[0], 0.0, places=6)
        self.assertGreater(distances[1], 0.0)


class TestFitDiagonalGaussian(unittest.TestCase):

    def test_mean_and_var_match_numpy(self):
        rng = np.random.default_rng(0)
        data = rng.normal(loc=3.0, scale=2.0, size=(500, 5))
        stats = fit_diagonal_gaussian(data)
        np.testing.assert_allclose(stats['mean'], data.mean(axis=0), rtol=1e-9)
        np.testing.assert_allclose(stats['var'], data.var(axis=0), rtol=1e-9)

    def test_flags_near_constant_dimension_inactive(self):
        rng = np.random.default_rng(1)
        data = rng.normal(loc=0.0, scale=1.0, size=(500, 4))
        data[:, 2] = 5.0  # dead dimension: ~zero variance
        stats = fit_diagonal_gaussian(data)
        active = stats['active_dims']
        self.assertFalse(active[2])
        self.assertTrue(all(active[i] for i in (0, 1, 3)))


class _StubExtractor:
    """Stand-in for the generic-encoder feature extractor: returns a fixed
    feature vector and counts how many times it actually ran, so we can test
    the detector's rate-limiting without downloading a real ImageNet model."""
    def __init__(self, feat):
        self.feat = np.asarray(feat, dtype=np.float32)
        self.calls = 0

    def extract(self, img):
        self.calls += 1
        return self.feat


def _novelty_part_with_stub(feat_dim=5, interval=0.0):
    """A FeatureNoveltyDetector with a stub extractor + a minimal novelty_ood
    calibration block injected, bypassing encoder construction/download."""
    part = FeatureNoveltyDetector(None, interval=interval)
    part.calibration = {
        'mean': [0.0] * feat_dim,
        'var': [1.0] * feat_dim,
        'active_dims': [True] * feat_dim,
        'eps': 1e-6,
        'score_anchors': {'distance': [0.0, 10.0, 100.0],
                          'score': [2.0, 50.0, 98.0]},
    }
    part.extractor = _StubExtractor(np.full(feat_dim, 2.0))
    return part


class TestFeatureNoveltyDetectorScoring(unittest.TestCase):

    def test_run_computes_distance_and_score_from_encoder_features(self):
        part = _novelty_part_with_stub(feat_dim=5)
        # feat = 2.0 in each of 5 dims, mean 0 var 1 -> distance = 5 * 2^2 = 20
        score, raw, smoothed = part.run(np.zeros((8, 8, 3), np.uint8))
        self.assertAlmostEqual(raw, 20.0, places=4)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_no_calibration_means_no_score(self):
        part = FeatureNoveltyDetector(None)   # no calib, no extractor
        score, raw, smoothed = part.run(np.zeros((8, 8, 3), np.uint8))
        self.assertIsNone(score)
        self.assertEqual(raw, 0.0)


class TestFeatureNoveltyDetectorInterval(unittest.TestCase):
    # Rate-limiting matters here: this part rides alongside the driving pilot
    # on every frame, and the encoder pass is heavier than the old single
    # steering-model pass -- so an unthrottled loop adds real load / power draw.

    def setUp(self):
        self.img = np.zeros((8, 8, 3), np.uint8)

    def test_zero_interval_runs_encoder_every_frame(self):
        part = _novelty_part_with_stub(interval=0.0)
        part.run(self.img); part.run(self.img); part.run(self.img)
        self.assertEqual(part.extractor.calls, 3)

    def test_interval_skips_encoder_when_held(self):
        part = _novelty_part_with_stub(interval=1.0)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=100.0):
            part.run(self.img)
        self.assertEqual(part.extractor.calls, 1)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=100.5):
            part.run(self.img)   # within interval -> held, NO encoder pass
        self.assertEqual(part.extractor.calls, 1)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=101.5):
            part.run(self.img)   # past interval -> recompute
        self.assertEqual(part.extractor.calls, 2)

    def test_held_values_match_last_real_update(self):
        part = _novelty_part_with_stub(interval=1.0)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=100.0):
            _, raw1, smoothed1 = part.run(self.img)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=100.3):
            _, raw2, smoothed2 = part.run(self.img)
        self.assertEqual(raw1, raw2)
        self.assertEqual(smoothed1, smoothed2)

    def test_now_override_drives_the_interval_gate_without_mocking_time(self):
        # Not actually used by mc_calibrate (calibration computes novelty
        # features in one encoder batch, not via this Part's run() -- see
        # mc_calibrate._replay_ema), but the same now= override exists here
        # for symmetry with MCDropoutConfidence/TTAStabilityDetector and any
        # future caller that DOES want to replay this part directly.
        part = _novelty_part_with_stub(interval=1.0)
        part.run(self.img, now=100.0)
        self.assertEqual(part.extractor.calls, 1)
        part.run(self.img, now=100.5)   # < 1.0s since the last update -> held
        self.assertEqual(part.extractor.calls, 1)
        part.run(self.img, now=101.5)   # >= 1.0s since the last update
        self.assertEqual(part.extractor.calls, 2)

    def test_now_none_falls_back_to_wall_clock(self):
        part = _novelty_part_with_stub(interval=1.0)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=200.0):
            part.run(self.img)
        with mock.patch('donkeycar.parts.novelty.time.time', return_value=200.2):
            part.run(self.img)
        self.assertEqual(part.extractor.calls, 1)


if __name__ == '__main__':
    unittest.main()
