import unittest

import numpy as np
import tensorflow as tf

from donkeycar.parts.gradcam_uncertainty import GradCamUncertainty
from donkeycar.parts.salient import VanillaGradientSaliency, IntegratedGradients


def _tiny_model():
    """A minimal conv->flatten->linear-output model standing in for the
    linear pilot: has a Conv2D (for Grad-CAM) and an output layer whose name
    contains 'out' (for the saliency activation-linearisation helper)."""
    tf.random.set_seed(0)
    inp = tf.keras.Input((16, 16, 3))
    x = tf.keras.layers.Conv2D(4, 3, activation='relu', name='conv')(inp)
    x = tf.keras.layers.Flatten()(x)
    out = tf.keras.layers.Dense(1, name='n_outputs0')(x)
    return tf.keras.Model(inp, out)


class TestGradCamPlusPlus(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)
        self.model = _tiny_model()
        self.engine = GradCamUncertainty(self.model, num_passes=4)
        self.img_u8 = (np.random.rand(16, 16, 3) * 255).astype(np.uint8)
        self.norm = np.random.rand(16, 16, 3).astype(np.float32)

    def test_attention_maps_pp_shape_and_range(self):
        maps = self.engine.attention_maps_pp(self.norm)
        self.assertEqual(maps.shape[0], 4)  # one per pass
        self.assertTrue(np.all(np.isfinite(maps)))
        self.assertGreaterEqual(maps.min(), 0.0)
        self.assertLessEqual(maps.max(), 1.0 + 1e-6)

    def test_attention_pp_map_upsampled_to_image_size(self):
        m = self.engine.attention_pp_map(self.img_u8)
        self.assertEqual(m.shape, self.img_u8.shape[:2])
        self.assertTrue(np.all(np.isfinite(m)))
        self.assertGreaterEqual(m.min(), 0.0)
        self.assertLessEqual(m.max(), 1.0 + 1e-6)

    def test_pp_is_not_identical_to_plain_gradcam(self):
        # Grad-CAM++ must not degenerate into plain Grad-CAM (the regression
        # gotcha the implementation guards against).
        mean_map, _, _ = self.engine.uncertainty_map(self.img_u8)
        pp_map = self.engine.attention_pp_map(self.img_u8)
        self.assertGreater(np.abs(pp_map - mean_map).mean(), 1e-6)


class TestIntegratedGradients(unittest.TestCase):

    def setUp(self):
        np.random.seed(1)
        self.model = _tiny_model()
        self.engine = IntegratedGradients(self.model, steps=16)
        self.norm = np.random.rand(16, 16, 3).astype(np.float32)

    def test_shape_and_range(self):
        m = self.engine.saliency_map(self.norm)
        self.assertEqual(m.shape, self.norm.shape[:2])
        self.assertTrue(np.all(np.isfinite(m)))
        self.assertGreaterEqual(m.min(), 0.0)
        self.assertLessEqual(m.max(), 1.0 + 1e-6)

    def test_zero_when_baseline_equals_input(self):
        # IG axiom: with baseline == input, (input - baseline) == 0, so every
        # attribution is exactly zero -- a deterministic sanity check.
        engine = IntegratedGradients(self.model, steps=8, baseline=self.norm)
        m = engine.saliency_map(self.norm)
        self.assertTrue(np.allclose(m, 0.0))

    def test_step_count_is_configurable(self):
        few = IntegratedGradients(self.model, steps=4).saliency_map(self.norm)
        many = IntegratedGradients(self.model, steps=48).saliency_map(self.norm)
        self.assertEqual(few.shape, many.shape)
        self.assertTrue(np.all(np.isfinite(few)))
        self.assertTrue(np.all(np.isfinite(many)))


if __name__ == '__main__':
    unittest.main()
