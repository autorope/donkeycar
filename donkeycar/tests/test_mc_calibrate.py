import json
import os
import shutil
import tempfile
import unittest

import numpy as np

from donkeycar.parts.mc_calibrate import (
    build_calibration, variance_to_confidence, novelty_distance_to_score,
    tta_variance_to_stability, _make_strictly_increasing,
    missing_calibration_reason, _replay_ema, _record_timestamps_sec,
)


class TestConfidenceCalibration(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(42)
        variances = rng.gamma(shape=2.0, scale=0.01, size=1000)  # always > 0
        self.calib = build_calibration(variances, num_passes=15, alpha=0.2)

    def test_confidence_is_monotonically_decreasing_with_variance(self):
        xs = self.calib['confidence_anchors']['variance']
        samples = np.linspace(xs[0], xs[-1], 50)
        scores = [variance_to_confidence(v, self.calib) for v in samples]
        for a, b in zip(scores, scores[1:]):
            self.assertGreaterEqual(a, b - 1e-9)

    def test_confidence_clamps_outside_anchor_range(self):
        below_range = variance_to_confidence(-1.0, self.calib)
        above_range = variance_to_confidence(1e6, self.calib)
        self.assertAlmostEqual(below_range, 99.0, places=6)  # min-variance anchor
        self.assertAlmostEqual(above_range, 5.0, places=6)   # max-variance anchor


class TestNoveltyCalibration(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(7)
        variances = rng.gamma(shape=2.0, scale=0.01, size=500)
        feats = rng.normal(size=(500, 64))
        self.calib = build_calibration(variances, num_passes=15, alpha=0.2,
                                       ood_features=feats,
                                       ood_encoder='mobilenet_v2',
                                       ood_input_size=128)
        self.block = self.calib['novelty_ood']

    def test_novelty_block_is_built(self):
        self.assertIn('novelty_ood', self.calib)

    def test_novelty_is_monotonically_increasing_with_distance(self):
        xs = self.block['score_anchors']['distance']
        samples = np.linspace(xs[0], xs[-1], 50)
        scores = [novelty_distance_to_score(d, self.block) for d in samples]
        for a, b in zip(scores, scores[1:]):
            self.assertLessEqual(a, b + 1e-9)

    def test_novelty_clamps_outside_anchor_range(self):
        below_range = novelty_distance_to_score(-1.0, self.block)
        above_range = novelty_distance_to_score(1e6, self.block)
        self.assertAlmostEqual(below_range, 2.0, places=6)   # min-distance anchor
        self.assertAlmostEqual(above_range, 98.0, places=6)  # max-distance anchor

    def test_no_features_means_no_novelty_blocks(self):
        rng = np.random.default_rng(8)
        variances = rng.gamma(shape=2.0, scale=0.01, size=100)
        calib = build_calibration(variances, num_passes=15, alpha=0.2)
        self.assertNotIn('novelty_ood', calib)
        self.assertNotIn('novelty_ood_spatial', calib)

    def test_spatial_block_records_its_encoder_geometry(self):
        # The offline heat map has to rebuild an extractor with exactly the
        # input size it was fitted at, or the per-location distances mean
        # nothing -- so the geometry travels with the block.
        rng = np.random.default_rng(9)
        variances = rng.gamma(shape=2.0, scale=0.01, size=200)
        calib = build_calibration(variances, num_passes=15, alpha=0.2,
                                  ood_spatial_features=rng.normal(
                                      size=(400, 32)),
                                  ood_encoder='mobilenet_v2',
                                  ood_spatial_input_hw=(224, 384))
        block = calib['novelty_ood_spatial']
        self.assertEqual(block['input_hw'], [224, 384])
        self.assertEqual(block['encoder'], 'mobilenet_v2')
        self.assertEqual(block['feat_dim'], 32)
        # and it still scores like every other novelty block
        xs = block['score_anchors']['distance']
        scores = [novelty_distance_to_score(d, block)
                  for d in np.linspace(xs[0], xs[-1], 20)]
        for a, b in zip(scores, scores[1:]):
            self.assertLessEqual(a, b + 1e-9)

    def test_legacy_task_collapsed_blocks_are_no_longer_written(self):
        # novelty_global (dense_2) was never read by anything once novelty
        # moved to a generic encoder, and novelty_spatial (conv2d_5) has been
        # replaced by the encoder-space map. Neither should reappear.
        rng = np.random.default_rng(10)
        calib = build_calibration(rng.gamma(2.0, 0.01, 100), num_passes=15,
                                  alpha=0.2,
                                  ood_features=rng.normal(size=(100, 16)),
                                  ood_encoder='mobilenet_v2',
                                  ood_input_size=128)
        self.assertNotIn('novelty_global', calib)
        self.assertNotIn('novelty_spatial', calib)


class TestTTACalibration(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(11)
        variances = rng.gamma(shape=2.0, scale=0.01, size=500)
        tta_variances = rng.gamma(shape=2.0, scale=1e-4, size=500)
        self.calib = build_calibration(variances, num_passes=15, alpha=0.2,
                                       tta_variances=tta_variances,
                                       tta_num_samples=8, tta_strength=0.2,
                                       tta_alpha=0.2)
        self.block = self.calib['tta']

    def test_tta_block_is_built_with_metadata(self):
        self.assertIn('tta', self.calib)
        self.assertEqual(self.block['num_samples'], 8)
        self.assertEqual(self.block['strength'], 0.2)

    def test_stability_is_monotonically_decreasing_with_variance(self):
        xs = self.block['stability_anchors']['variance']
        samples = np.linspace(xs[0], xs[-1], 50)
        scores = [tta_variance_to_stability(v, self.block) for v in samples]
        for a, b in zip(scores, scores[1:]):
            self.assertGreaterEqual(a, b - 1e-9)

    def test_stability_clamps_outside_anchor_range(self):
        below = tta_variance_to_stability(-1.0, self.block)
        above = tta_variance_to_stability(1e6, self.block)
        self.assertAlmostEqual(below, 99.0, places=6)  # min-variance anchor
        self.assertAlmostEqual(above, 5.0, places=6)   # max-variance anchor

    def test_no_tta_variances_means_no_tta_block(self):
        rng = np.random.default_rng(12)
        calib = build_calibration(rng.gamma(2.0, 0.01, 100), num_passes=15,
                                  alpha=0.2)
        self.assertNotIn('tta', calib)


class TestAugmentationProvenance(unittest.TestCase):
    """The 'augmentation' block records how the novelty baselines were fit
    (clean-only vs widened with training-style augmented frames), so a
    calibration can be told apart from an older one after the fact."""

    def _variances(self, n=200, seed=21):
        return np.random.default_rng(seed).gamma(shape=2.0, scale=0.01, size=n)

    def test_absent_when_not_supplied_keeps_older_calibrations_valid(self):
        calib = build_calibration(self._variances(), num_passes=15, alpha=0.2)
        self.assertNotIn('augmentation', calib)

    def test_recorded_verbatim_when_supplied(self):
        info = {'applied': True, 'augmentations': ['SHADOW', 'GAMMA'],
                'passes': 2, 'stride': 12, 'n_augmented_samples': 1500,
                'n_clean_samples': 9221, 'scope': 'novelty baselines only'}
        calib = build_calibration(self._variances(), num_passes=15, alpha=0.2,
                                  augmentation_info=info)
        self.assertEqual(calib['augmentation'], info)

    def test_does_not_disturb_the_confidence_calibration(self):
        """Provenance is metadata: adding it must not move any number the
        confidence signal reads."""
        v = self._variances()
        plain = build_calibration(v, num_passes=15, alpha=0.2)
        with_info = build_calibration(v, num_passes=15, alpha=0.2,
                                      augmentation_info={'applied': False})
        self.assertEqual(plain['percentiles'], with_info['percentiles'])
        self.assertEqual(plain['confidence_anchors'],
                         with_info['confidence_anchors'])
        self.assertEqual(plain['n_frames'], with_info['n_frames'])
        self.assertEqual(plain['tiers'], with_info['tiers'])

    def test_n_frames_counts_clean_frames_only(self):
        """Augmented samples are pooled into the novelty feature matrices but
        never into the variance distribution, so the reported frame count
        must still describe the replay, not the enlarged feature set."""
        rng = np.random.default_rng(31)
        variances = rng.gamma(shape=2.0, scale=0.01, size=300)
        # 300 clean frames, but 900 novelty feature vectors (clean + augmented)
        feats = rng.normal(size=(900, 64))
        calib = build_calibration(variances, num_passes=15, alpha=0.2,
                                  ood_features=feats,
                                  ood_encoder='mobilenet_v2',
                                  ood_input_size=128,
                                  augmentation_info={'applied': True,
                                                     'n_augmented_samples': 600})
        self.assertEqual(calib['n_frames'], 300)
        self.assertIn('novelty_ood', calib)


class TestMissingCalibrationReason(unittest.TestCase):
    """A calib.json can exist while lacking the block a given signal needs
    (e.g. written before that signal shipped). Checking only for the file
    would leave that signal silently blank on the dashboard -- no panel and
    no 'not calibrated' banner, indistinguishable from the feature being off.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = os.path.join(self.tmp, 'model.calib.json')

    def _write(self, calib):
        with open(self.path, 'w') as f:
            json.dump(calib, f)
        return self.path

    def test_absent_file_is_reported_for_every_signal(self):
        missing = os.path.join(self.tmp, 'nope.calib.json')
        for signal in ('confidence', 'novelty', 'tta'):
            reason = missing_calibration_reason(missing, signal)
            self.assertIsNotNone(reason)
            self.assertIn("doesn't exist", reason)

    def test_present_block_reports_no_reason(self):
        self._write({'confidence_anchors': {}, 'novelty_ood': {}, 'tta': {}})
        for signal in ('confidence', 'novelty', 'tta'):
            self.assertIsNone(missing_calibration_reason(self.path, signal))

    def test_file_present_but_block_missing_is_still_reported(self):
        # The realistic case: an older calibration with confidence+novelty
        # but no TTA block.
        self._write({'confidence_anchors': {}, 'novelty_ood': {}})
        self.assertIsNone(missing_calibration_reason(self.path, 'confidence'))
        self.assertIsNone(missing_calibration_reason(self.path, 'novelty'))
        tta_reason = missing_calibration_reason(self.path, 'tta')
        self.assertIsNotNone(tta_reason)
        self.assertIn('tta', tta_reason)

    def test_unreadable_file_is_reported_rather_than_raising(self):
        with open(self.path, 'w') as f:
            f.write('{not valid json')
        reason = missing_calibration_reason(self.path, 'confidence')
        self.assertIsNotNone(reason)
        self.assertIn('could not be read', reason)


class TestMakeStrictlyIncreasing(unittest.TestCase):

    def test_nudges_duplicate_values_strictly_increasing(self):
        xs = _make_strictly_increasing([1.0, 1.0, 1.0, 2.0])
        for a, b in zip(xs, xs[1:]):
            self.assertLess(a, b)

    def test_already_increasing_values_are_unchanged(self):
        xs = _make_strictly_increasing([1.0, 2.0, 3.0])
        self.assertEqual(xs, [1.0, 2.0, 3.0])


class TestReplayEma(unittest.TestCase):
    """_replay_ema reproduces, over an already-computed sequence, exactly the
    hold-between-updates + EMA-fold logic MCDropoutConfidence/
    FeatureNoveltyDetector/TTAStabilityDetector apply live in run()."""

    def test_interval_zero_updates_every_entry_like_a_plain_ema(self):
        values = [1.0, 2.0, 3.0, 4.0]
        ts = [0.0, 1.0, 2.0, 3.0]
        out = _replay_ema(values, ts, alpha=0.5, interval=0.0)
        expected = [1.0, 1.5, 2.25, 3.125]   # standard EMA fold, alpha=0.5
        np.testing.assert_allclose(out, expected)

    def test_first_value_seeds_the_ema_unsmoothed(self):
        out = _replay_ema([7.0, 7.0], [0.0, 0.1], alpha=0.2, interval=0.0)
        self.assertEqual(out[0], 7.0)

    def test_held_entries_repeat_the_last_smoothed_value(self):
        # updates at t=0 and t=1 (>=1s apart); the entries at t=0.2 and t=0.5
        # arrive too soon (interval=1.0) and must just repeat the t=0 value.
        values = [10.0, 10.0, 10.0, 20.0]
        ts = [0.0, 0.2, 0.5, 1.0]
        out = _replay_ema(values, ts, alpha=0.5, interval=1.0)
        self.assertEqual(out[0], out[1])
        self.assertEqual(out[1], out[2])
        # the update at t=1.0 folds 20.0 in (not just repeats 10.0)
        self.assertAlmostEqual(out[3], 0.5 * 20.0 + 0.5 * 10.0)

    def test_none_timestamps_updates_every_entry_regardless_of_interval(self):
        # No _timestamp_ms on the tub -- caller is expected to pass interval=0
        # in that case (mc_calibrate does), but the function itself is also
        # safe if interval>0 is passed with timestamps=None: nothing can ever
        # look "too soon" without a clock, so every entry updates.
        values = [1.0, 5.0, 1.0, 5.0]
        out = _replay_ema(values, None, alpha=0.5, interval=1.0)
        # not constant -- proves entries after the first actually updated
        self.assertNotEqual(out[1], out[0])
        self.assertNotEqual(out[2], out[1])

    def test_matches_feature_novelty_detector_semantics(self):
        # Cross-check against FeatureNoveltyDetector's own EMA formula
        # (self.smoothed = alpha*raw + (1-alpha)*smoothed, first = raw) over
        # an unthrottled (interval=0) sequence.
        rng = np.random.default_rng(3)
        values = rng.gamma(2.0, 1.0, size=25)
        alpha = 0.2
        expected = []
        sm = None
        for v in values:
            sm = v if sm is None else alpha * v + (1 - alpha) * sm
            expected.append(sm)
        out = _replay_ema(values, list(range(len(values))), alpha, 0.0)
        np.testing.assert_allclose(out, expected)


class TestRecordTimestampsSec(unittest.TestCase):

    class _FakeRecord:
        def __init__(self, ts_ms):
            self.underlying = {'_timestamp_ms': ts_ms}

    def test_converts_ms_to_seconds_in_order(self):
        records = [self._FakeRecord(0), self._FakeRecord(500),
                  self._FakeRecord(1500)]
        self.assertEqual(_record_timestamps_sec(records), [0.0, 0.5, 1.5])

    def test_any_missing_timestamp_returns_none(self):
        records = [self._FakeRecord(0), self._FakeRecord(None)]
        self.assertIsNone(_record_timestamps_sec(records))


class TestNoveltyAnchorDistances(unittest.TestCase):
    """The live 'novelty_ood' block must be percentile-anchored on whatever
    distances it's given via ood_anchor_distances (the calibration replay's
    own EMA-smoothed sequence) rather than the raw per-vector distances of
    ood_features -- see _build_novelty_block's docstring for why scoring a
    smoothed value against raw-fitted anchors silently mismatches."""

    def test_anchors_reflect_the_passed_distances_not_the_raw_ones(self):
        rng = np.random.default_rng(5)
        feats = rng.normal(size=(300, 16))
        # A synthetic "smoothed" sequence with an artificially narrow spread
        # relative to the raw feature-implied distances, mirroring how a real
        # EMA-smoothed sequence has less spread than the raw one it smooths.
        narrow_distances = np.full(300, 3.0)  # every entry identical

        calib_raw = build_calibration(
            rng.gamma(2.0, 0.01, 100), num_passes=15, alpha=0.2,
            ood_features=feats, ood_encoder='mobilenet_v2', ood_input_size=128)
        calib_anchored = build_calibration(
            rng.gamma(2.0, 0.01, 100), num_passes=15, alpha=0.2,
            ood_features=feats, ood_encoder='mobilenet_v2', ood_input_size=128,
            ood_anchor_distances=narrow_distances)

        raw_anchors = calib_raw['novelty_ood']['score_anchors']['distance']
        forced_anchors = calib_anchored['novelty_ood']['score_anchors']['distance']
        # With every anchor_distance identical (3.0), min/p50/p80/p97/max
        # collapse to the same nudged-apart value near 3.0 -- nothing like
        # the spread of the real per-vector distances used for `calib_raw`.
        self.assertNotEqual(raw_anchors, forced_anchors)
        for x in forced_anchors:
            self.assertAlmostEqual(x, 3.0, places=6)

    def test_mean_var_active_dims_unaffected_by_anchor_distances(self):
        # anchor_distances only changes what the PERCENTILES are fit on, not
        # the Gaussian itself -- that still describes ood_features.
        rng = np.random.default_rng(6)
        feats = rng.normal(size=(200, 8))
        calib_raw = build_calibration(
            rng.gamma(2.0, 0.01, 50), num_passes=15, alpha=0.2,
            ood_features=feats, ood_encoder='mobilenet_v2', ood_input_size=128)
        calib_anchored = build_calibration(
            rng.gamma(2.0, 0.01, 50), num_passes=15, alpha=0.2,
            ood_features=feats, ood_encoder='mobilenet_v2', ood_input_size=128,
            ood_anchor_distances=np.ones(200) * 7.0)
        self.assertEqual(calib_raw['novelty_ood']['mean'],
                         calib_anchored['novelty_ood']['mean'])
        self.assertEqual(calib_raw['novelty_ood']['var'],
                         calib_anchored['novelty_ood']['var'])

    def test_spatial_block_is_never_affected_by_anchor_distances(self):
        # novelty_ood_spatial has no smoothing/interval concept -- passing
        # ood_anchor_distances must only touch the live pooled block.
        rng = np.random.default_rng(7)
        feats = rng.normal(size=(100, 8))
        spatial_feats = rng.normal(size=(400, 8))
        calib = build_calibration(
            rng.gamma(2.0, 0.01, 50), num_passes=15, alpha=0.2,
            ood_features=feats, ood_encoder='mobilenet_v2', ood_input_size=128,
            ood_anchor_distances=np.ones(100) * 9.0,
            ood_spatial_features=spatial_feats, ood_encoder_file=None,
            ood_spatial_input_hw=(224, 384))
        spatial_anchors = calib['novelty_ood_spatial']['score_anchors']['distance']
        # not collapsed to ~9.0 like the pooled block would be
        self.assertFalse(all(abs(x - 9.0) < 1e-6 for x in spatial_anchors))


if __name__ == '__main__':
    unittest.main()
