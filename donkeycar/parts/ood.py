"""
Generic-encoder feature extraction for out-of-distribution (novelty) detection.

WHY THIS EXISTS (the diagnosis behind it): the original novelty detector
measured distance-from-training in the *steering model's* penultimate layer
(``dense_2``). But that model was trained only to predict a steering angle, so
it learned to discard everything that doesn't affect steering -- texture,
colour, scene semantics. Empirically, grass / carpet / open track all collapse
to nearly identical ``dense_2`` features (all mean "drive straight"), so the
novelty score barely moved for genuinely different scenes and only reacted to
gross changes like covering the camera. Measured z-scores from the training
distribution: grass +0.0, carpet -0.2, white-noise -0.3 (i.e. *less* novel
than a real track frame), vs +5.5 only for a blacked-out camera.

The fix is to measure novelty in the feature space of a *generic* image
encoder (an ImageNet-pretrained backbone) that was never trained to ignore
scene content, so it keeps the texture/semantics that distinguish grass from
track. With the same diagonal-Mahalanobis math, the same scenes then separate
by tens-to-hundreds of sigma (grass +116, carpet +92, noise +141).

This module provides a pluggable extractor interface so the *source* of the
features can change without touching the OOD math or calibration downstream:

  * ``CPUEncoderExtractor`` -- runs a small ImageNet backbone (MobileNetV2 by
    default) on the CPU. The portable default: works on any setup.
  * (future) a Hailo-NPU-backed extractor implementing the same ``extract`` /
    ``extract_batch`` interface, so the encoder forward pass moves off the Pi
    CPU. Not yet implemented -- see the project notes.

The extractor is deliberately independent of the steering pilot: novelty here
is a property of the *input scene*, not of the driving model.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Supported generic encoders: name -> (keras.applications ctor, preprocess,
# default input size). Kept small/Pi-friendly; MobileNetV2 pooled = 1280-dim.
_ENCODERS = {
    'mobilenet_v2': ('MobileNetV2', 'mobilenet_v2', 128),
    'mobilenet': ('MobileNet', 'mobilenet', 128),
}


def build_ood_encoder(name='mobilenet_v2', input_size=None, alpha=1.0):
    """
    Build a generic ImageNet feature-extractor model (no classification head,
    global-average-pooled) and its matching preprocessing function.

    :return: (keras.Model mapping (B,S,S,3) uint8-range floats -> (B, feat_dim),
              preprocess_fn, input_size)
    """
    import tensorflow as tf
    if name not in _ENCODERS:
        raise ValueError(f'Unknown OOD encoder {name!r}; options: '
                         f'{sorted(_ENCODERS)}')
    ctor_name, prep_mod, default_size = _ENCODERS[name]
    input_size = int(input_size or default_size)

    ctor = getattr(tf.keras.applications, ctor_name)
    kwargs = dict(weights='imagenet', include_top=False, pooling='avg',
                  input_shape=(input_size, input_size, 3))
    # alpha (width multiplier) is only accepted by the mobilenet family.
    try:
        model = ctor(alpha=alpha, **kwargs)
    except TypeError:
        model = ctor(**kwargs)

    prep = getattr(tf.keras.applications, prep_mod).preprocess_input
    logger.info(f'Built OOD encoder {name} (input={input_size}, '
                f'feat_dim={model.output_shape[-1]})')
    return model, prep, input_size


class CPUEncoderExtractor:
    """
    Extract generic-encoder features from camera frames on the CPU.

    ``extract(img)`` / ``extract_batch(imgs)`` take uint8 [0,255] (H,W,3)
    frames (any size -- resized internally) and return L2-comparable float
    feature vectors suitable for the downstream Mahalanobis / kNN scorer.

    :param name:       encoder key (see ``_ENCODERS``).
    :param input_size: square input the encoder is resized to. None -> the
                       encoder's default.
    :param model:      optional pre-built encoder Model (e.g. loaded from a
                       sidecar so the Pi needs no weight download). If given,
                       ``name``/``input_size`` must match how it was built.
    """

    def __init__(self, name='mobilenet_v2', input_size=None, alpha=1.0,
                 model=None):
        self.name = name
        if model is not None:
            import tensorflow as tf
            self.model = model
            self.input_size = int(model.input_shape[1])
            _, prep_mod, _ = _ENCODERS[name]
            self.preprocess = getattr(tf.keras.applications,
                                      prep_mod).preprocess_input
        else:
            self.model, self.preprocess, self.input_size = build_ood_encoder(
                name, input_size, alpha)
        self.feat_dim = int(self.model.output_shape[-1])

    def _prep_batch(self, imgs):
        from PIL import Image
        s = self.input_size
        batch = np.stack([
            np.asarray(Image.fromarray(im).resize((s, s)), dtype=np.float32)
            for im in imgs])
        return self.preprocess(batch)

    def extract_batch(self, imgs):
        """imgs: list/array of uint8 (H,W,3) -> (n, feat_dim) float32."""
        batch = self._prep_batch(imgs)
        return np.asarray(self.model(batch, training=False), dtype=np.float32)

    def extract(self, img):
        """img: uint8 (H,W,3) -> (feat_dim,) float32."""
        return self.extract_batch([img])[0]


def spatial_input_hw(frame_h, frame_w, short_side=224, stride=32):
    """
    Pick an encoder input (H, W) that preserves the camera frame's aspect
    ratio, with both sides multiples of the encoder's total stride.

    The pooled encoder used for the live novelty score squashes frames into a
    square, which is harmless when every location is averaged together. The
    SPATIAL map keeps per-location distances, so a squashed input would
    stretch the resulting heat map unevenly when it is drawn back over the
    frame. Sizing to the frame's own aspect avoids that.

    :param short_side: target size of the shorter side; the longer side is
                       scaled to match the frame's aspect ratio. Bigger =
                       finer grid (grid ~= size/stride) and slower.
    """
    frame_h, frame_w = int(frame_h), int(frame_w)
    aspect = frame_w / max(1, frame_h)

    def snap(v):
        return max(stride, int(round(v / stride)) * stride)

    if frame_w >= frame_h:
        h = snap(short_side)
        w = snap(short_side * aspect)
    else:
        w = snap(short_side)
        h = snap(short_side / aspect)
    return h, w


def build_ood_spatial_encoder(name='mobilenet_v2', input_hw=(224, 384),
                              alpha=1.0):
    """
    Same generic ImageNet encoder as ``build_ood_encoder``, but WITHOUT the
    global-average-pooling head, so the spatial feature grid is preserved.

    Averaging this model's output over its spatial axes reproduces the pooled
    model's output exactly, which is the point: the offline spatial novelty
    map and the live novelty score then live in the same feature space
    instead of two unrelated ones.

    :return: (keras.Model mapping (B,H,W,3) -> (B, gh, gw, feat_dim),
              preprocess_fn, (H, W))
    """
    import tensorflow as tf
    if name not in _ENCODERS:
        raise ValueError(f'Unknown OOD encoder {name!r}; options: '
                         f'{sorted(_ENCODERS)}')
    ctor_name, prep_mod, _ = _ENCODERS[name]
    h, w = int(input_hw[0]), int(input_hw[1])

    ctor = getattr(tf.keras.applications, ctor_name)
    kwargs = dict(weights='imagenet', include_top=False, pooling=None,
                  input_shape=(h, w, 3))
    try:
        model = ctor(alpha=alpha, **kwargs)
    except TypeError:
        model = ctor(**kwargs)

    prep = getattr(tf.keras.applications, prep_mod).preprocess_input
    logger.info(f'Built spatial OOD encoder {name} (input={h}x{w}, '
                f'grid={model.output_shape[1:3]}, '
                f'feat_dim={model.output_shape[-1]})')
    return model, prep, (h, w)


class SpatialEncoderExtractor:
    """
    Per-location generic-encoder features, for the offline novelty heat map.

    Mirrors ``CPUEncoderExtractor`` but keeps the spatial grid instead of
    averaging it away. Offline-only: nothing in the drive loop uses this, so
    the larger input size costs no live latency.
    """

    def __init__(self, name='mobilenet_v2', input_hw=(224, 384), alpha=1.0,
                 model=None):
        self.name = name
        if model is not None:
            import tensorflow as tf
            self.model = model
            self.input_hw = (int(model.input_shape[1]),
                             int(model.input_shape[2]))
            _, prep_mod, _ = _ENCODERS[name]
            self.preprocess = getattr(tf.keras.applications,
                                      prep_mod).preprocess_input
        else:
            self.model, self.preprocess, self.input_hw = \
                build_ood_spatial_encoder(name, input_hw, alpha)
        self.feat_dim = int(self.model.output_shape[-1])
        self.grid_hw = tuple(int(v) for v in self.model.output_shape[1:3])

    def _prep_batch(self, imgs):
        from PIL import Image
        h, w = self.input_hw
        batch = np.stack([
            np.asarray(Image.fromarray(im).resize((w, h)), dtype=np.float32)
            for im in imgs])
        return self.preprocess(batch)

    def extract_grid_batch(self, imgs):
        """imgs: list of uint8 (H,W,3) -> (n, gh, gw, feat_dim) float32."""
        batch = self._prep_batch(imgs)
        return np.asarray(self.model(batch, training=False), dtype=np.float32)

    def extract_grid(self, img):
        """img: uint8 (H,W,3) -> (gh, gw, feat_dim) float32."""
        return self.extract_grid_batch([img])[0]
