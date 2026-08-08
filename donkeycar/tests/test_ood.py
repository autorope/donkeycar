import unittest

import numpy as np
import tensorflow as tf

from donkeycar.parts.ood import build_ood_encoder, CPUEncoderExtractor


def _tiny_encoder(input_size=32, feat_dim=8):
    """A stand-in for the ImageNet backbone so tests never download weights:
    same interface (square image in, pooled vector out)."""
    inp = tf.keras.Input((input_size, input_size, 3))
    x = tf.keras.layers.Conv2D(feat_dim, 3, padding='same')(inp)
    out = tf.keras.layers.GlobalAveragePooling2D()(x)
    return tf.keras.Model(inp, out)


class TestBuildOodEncoder(unittest.TestCase):

    def test_unknown_encoder_raises(self):
        with self.assertRaises(ValueError):
            build_ood_encoder('not_a_real_encoder')


class TestCPUEncoderExtractor(unittest.TestCase):

    def setUp(self):
        # Inject a tiny model (name is a real key so preprocess resolves).
        self.ex = CPUEncoderExtractor('mobilenet_v2', model=_tiny_encoder(32, 8))

    def test_feat_dim_and_input_size_from_injected_model(self):
        self.assertEqual(self.ex.feat_dim, 8)
        self.assertEqual(self.ex.input_size, 32)

    def test_extract_single_shape(self):
        img = (np.random.default_rng(0).random((120, 160, 3)) * 255).astype(np.uint8)
        feat = self.ex.extract(img)
        self.assertEqual(feat.shape, (8,))
        self.assertTrue(np.all(np.isfinite(feat)))

    def test_extract_batch_shape(self):
        imgs = [(np.random.default_rng(i).random((120, 160, 3)) * 255).astype(np.uint8)
                for i in range(4)]
        feats = self.ex.extract_batch(imgs)
        self.assertEqual(feats.shape, (4, 8))

    def test_accepts_frames_of_any_size(self):
        # Resizing happens internally, so odd input sizes must not error.
        small = (np.random.default_rng(1).random((40, 60, 3)) * 255).astype(np.uint8)
        big = (np.random.default_rng(2).random((480, 640, 3)) * 255).astype(np.uint8)
        self.assertEqual(self.ex.extract(small).shape, (8,))
        self.assertEqual(self.ex.extract(big).shape, (8,))


if __name__ == '__main__':
    unittest.main()
