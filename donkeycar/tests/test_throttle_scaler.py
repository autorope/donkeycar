import unittest
from unittest import mock

from donkeycar.parts.mc_dropout import ThrottleScaler


class TestThrottleScalerPassthrough(unittest.TestCase):

    def setUp(self):
        self.scaler = ThrottleScaler()

    def test_throttle_none_passes_through(self):
        self.assertIsNone(self.scaler.run(None, 10.0, 90.0))

    def test_both_signals_none_passes_through_unchanged(self):
        self.assertEqual(self.scaler.run(0.5, None, None), 0.5)

    def test_single_available_signal_still_scales(self):
        # novelty disabled/uncalibrated (None); confidence alone drives it
        result = self.scaler.run(1.0, 10.0, None)  # confidence critical
        self.assertAlmostEqual(result, self.scaler.min_scale)


class TestThrottleScalerTiers(unittest.TestCase):
    # defaults: confidence reduced<65 critical<25, novelty reduced>25 critical>65

    def setUp(self):
        self.scaler = ThrottleScaler(min_scale=0.4, stop_duration=1.0)

    def test_confidence_above_reduced_threshold_is_full_scale(self):
        self.assertEqual(self.scaler.run(1.0, 80.0, None), 1.0)

    def test_confidence_mid_reduced_tier_interpolates(self):
        result = self.scaler.run(1.0, 45.0, None)  # midpoint of 25..65
        self.assertAlmostEqual(result, 0.7, places=6)

    def test_novelty_below_reduced_threshold_is_full_scale(self):
        self.assertEqual(self.scaler.run(1.0, None, 10.0), 1.0)

    def test_novelty_mid_reduced_tier_interpolates(self):
        result = self.scaler.run(1.0, None, 45.0)  # midpoint of 25..65
        self.assertAlmostEqual(result, 0.7, places=6)

    def test_combined_signals_take_the_more_conservative_one(self):
        # confidence mid-reduced (scale 0.7), novelty critical (scale 0.4) -> 0.4 wins
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            result = self.scaler.run(1.0, 45.0, 80.0)
        self.assertAlmostEqual(result, 0.4, places=6)


class TestThrottleScalerTTASignal(unittest.TestCase):
    # TTA stability is "high is good" like confidence: reduced<65, critical<25

    def setUp(self):
        self.scaler = ThrottleScaler(min_scale=0.4, stop_duration=1.0)

    def test_tta_none_does_not_block_other_signals(self):
        # confidence full, novelty full, tta unavailable -> full throttle
        self.assertEqual(self.scaler.run(1.0, 90.0, 5.0, None), 1.0)

    def test_tta_alone_scales_when_fragile(self):
        # only TTA available and mid-reduced tier (midpoint of 25..65 -> 0.7)
        result = self.scaler.run(1.0, None, None, 45.0)
        self.assertAlmostEqual(result, 0.7, places=6)

    def test_tta_is_included_in_min_of_scales(self):
        # confidence full (1.0), but TTA critical (0.4) -> 0.4 wins
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            result = self.scaler.run(1.0, 90.0, 5.0, 10.0)
        self.assertAlmostEqual(result, 0.4, places=6)

    def test_all_signals_none_passes_through(self):
        self.assertEqual(self.scaler.run(0.5, None, None, None), 0.5)

    def test_sustained_tta_critical_forces_stop(self):
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            self.scaler.run(1.0, None, None, 10.0)
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=101.5):
            self.assertEqual(self.scaler.run(1.0, None, None, 10.0), 0.0)


class TestThrottleScalerSustainedStop(unittest.TestCase):

    def setUp(self):
        self.scaler = ThrottleScaler(min_scale=0.4, stop_duration=1.0)

    def test_critical_below_stop_duration_still_just_scales(self):
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            result = self.scaler.run(1.0, 10.0, None)
        self.assertAlmostEqual(result, 0.4, places=6)

    def test_critical_sustained_past_stop_duration_forces_zero(self):
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            self.scaler.run(1.0, 10.0, None)
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=101.5):
            result = self.scaler.run(1.0, 10.0, None)
        self.assertEqual(result, 0.0)

    def test_recovery_resets_the_critical_timer(self):
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            self.scaler.run(1.0, 10.0, None)  # goes critical
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.5):
            self.scaler.run(1.0, 80.0, None)  # recovers before stop_duration elapses
        self.assertIsNone(self.scaler.critical_since)
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=101.0):
            # critical again, but the timer restarted -- not yet sustained
            result = self.scaler.run(1.0, 10.0, None)
        self.assertAlmostEqual(result, 0.4, places=6)

    def test_handoff_between_signals_counts_as_continuous_critical(self):
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.0):
            self.scaler.run(1.0, 10.0, None)  # confidence critical starts the timer
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=100.6):
            # confidence recovers but novelty goes critical -- timer must not reset
            self.scaler.run(1.0, 80.0, 80.0)
        with mock.patch('donkeycar.parts.mc_dropout.time.time', return_value=101.2):
            result = self.scaler.run(1.0, 80.0, 80.0)
        self.assertEqual(result, 0.0)


if __name__ == '__main__':
    unittest.main()
