"""
Offline Grad-CAM "uncertainty map" tool (Feature 3 of the uncertainty toolkit).

For frames of a recorded tub, this tool runs Grad-CAM once per MC-Dropout
pass (same N stochastic passes as the live confidence signal) and computes
the *pixel-wise variance* of the N attention maps. Regions where the model's
attention is inconsistent across dropout sub-networks are rendered as a
heatmap overlay -- a spatial answer to "where was the model uncertain?".

This is offline-only by design: each analysed frame costs one batched
forward + backward pass (N Grad-CAMs share a single gradient tape), which is
fine for post-drive analysis but too heavy for the 20Hz drive loop.

Frame selection (feasibility): by default only the top-K most uncertain
frames are analysed, ranked by the steering variance either logged in the
tub (``pilot/smoothed_variance``, written when driving with
XAI_CONFIDENCE_ENABLED enabled)
or recomputed by replaying the tub through the MC-Dropout part. ``--all``
forces every frame (use only for short drives).

If the model's calibration also has novelty (Mahalanobis distance) stats --
see ``donkeycar.parts.mc_calibrate`` / ``donkeycar.parts.novelty`` -- a
per-frame novelty distance/score is added to every timeline entry (cheap, a
single forward pass, computed for ALL frames), and a third, independent
spatial "novelty map" overlay is rendered for the analysed frames, showing
*where* in the image the features look unlike anything in training data --
a different question from the attention/uncertainty overlays above.

Each analysed frame also gets two pixel-level overlays (see
``donkeycar.parts.salient``): vanilla-gradient saliency (a single raw input
gradient -- noisy) and Integrated Gradients (path-integrated, axiomatic,
cleaner). Both take gradients against full-resolution input pixels rather than
the coarse conv2d_5 grid -- complementary lenses to the Grad-CAM maps above.
A Grad-CAM++ attention map (sharper, multi-region variant of the mean
attention) is rendered too.

Output (consumed by the Feature 4 viewer):
    <out>/
      data.json            -- timeline of variance/confidence/novelty for ALL
                              frames, plus an entry per analysed frame
      images/<idx>_orig.jpg      -- camera frame
      images/<idx>_unc.png       -- uncertainty-map overlay (attention variance)
      images/<idx>_attn.png      -- mean-attention overlay (where it looked)
      images/<idx>_attnpp.png    -- Grad-CAM++ attention overlay (sharper)
      images/<idx>_novelty.png   -- novelty overlay (where features are
                                   unlike training data); only if the model's
                                   calibration has novelty stats
      images/<idx>_saliency.png  -- vanilla-gradient pixel saliency overlay
      images/<idx>_ig.png        -- Integrated Gradients pixel attribution

Usage:
    python -m donkeycar.parts.gradcam_uncertainty \
        --tub data/ --model models/mypilot.h5 [--top-k 50] [--all] \
        [--percentile 90] [--limit N] [--start N] [--passes 15] \
        [--ig-steps 32] [--out dir]

Caveats: linear model only (same scope as the live signal); the variance map
inherits MC-Dropout's blind spots -- it measures disagreement between dropout
sub-networks, not distance from the training distribution. The novelty map
is the complementary signal (distance from training distribution) and
inherits its own blind spots -- see donkeycar.parts.novelty's module
docstring (diagonal-covariance approximation, position-independent spatial
pooling). The saliency map is noisier and less spatially decisive than
Grad-CAM -- see donkeycar.parts.salient's module docstring.
"""
import argparse
import json
import logging
import os
import time

import numpy as np
import tensorflow as tf
from PIL import Image

logger = logging.getLogger(__name__)


class GradCamUncertainty:
    """
    Computes N stochastic Grad-CAM maps per frame (dropout active, one map
    per MC-Dropout pass) and reduces them to a mean-attention map and a
    pixel-wise variance ("uncertainty") map.

    All N maps are produced in a single batched forward+backward pass: the
    image is replicated N times, dropout gives each batch row an independent
    sub-network, and the gradient of the summed steering output w.r.t. the
    conv features yields each row's own Grad-CAM weights (rows are
    independent, so d(sum steer_i)/d(feat_j) == d(steer_j)/d(feat_j)).
    """

    def __init__(self, model, num_passes=15, conv_layer_name=None):
        self.model = model
        self.num_passes = int(num_passes)

        if conv_layer_name:
            conv_layer = model.get_layer(conv_layer_name)
        else:
            conv_layer = self._last_conv_layer(model)
        logger.info(f'GradCamUncertainty: using conv layer '
                    f'"{conv_layer.name}" {conv_layer.output.shape}, '
                    f'N={self.num_passes}')

        # Steering is the first model output (n_outputs0 on the linear model).
        self.grad_model = tf.keras.Model(
            model.inputs, [conv_layer.output, model.outputs[0]])

    @staticmethod
    def _last_conv_layer(model):
        for layer in reversed(model.layers):
            if isinstance(layer, tf.keras.layers.Conv2D):
                return layer
        raise ValueError('No Conv2D layer found in model; Grad-CAM needs a '
                         'convolutional architecture.')

    def attention_maps(self, norm_img):
        """
        :param norm_img: float32 image, [0,1], shape (H, W, C)
        :return: np array (N, h, w) of per-pass Grad-CAM maps, each
                 normalised to [0, 1] by its own max (so the variance across
                 maps measures *shape* disagreement, not magnitude).
        """
        batch = tf.convert_to_tensor(
            np.repeat(norm_img[np.newaxis, ...], self.num_passes, axis=0))

        with tf.GradientTape() as tape:
            features, steering = self.grad_model(batch, training=True)
            target = tf.reduce_sum(steering)
        grads = tape.gradient(target, features)          # (N, h, w, c)

        # Grad-CAM: channel weights = spatially-pooled gradients.
        weights = tf.reduce_mean(grads, axis=(1, 2), keepdims=True)
        cams = tf.nn.relu(tf.reduce_sum(weights * features, axis=-1))
        cams = cams.numpy()                              # (N, h, w)

        # Per-map max-normalisation; guard all-zero maps.
        maxes = cams.reshape(self.num_passes, -1).max(axis=1)
        maxes[maxes == 0] = 1.0
        return cams / maxes[:, None, None]

    def attention_maps_pp(self, norm_img):
        """
        Grad-CAM++ variant of :meth:`attention_maps`. Same batched N-pass
        structure and same ``grad_model``; only the per-location weighting
        changes.

        Plain Grad-CAM pools the gradient with a flat spatial *average*, so
        every location in a channel counts equally -- which can wash out the
        map when several separate regions each matter (e.g. both lane lines).
        Grad-CAM++ replaces that average with a *weighted* one: each location's
        gradient is scaled by an ``alpha`` coefficient built from higher-order
        gradient terms, so locations that individually push the prediction
        hardest count for more. The result is sharper and more complete when
        attention is genuinely multi-region.

        Derivation note (regression output): the textbook Grad-CAM++ alphas
        assume a classification score of the form ``exp(logit)``, whose 2nd/3rd
        derivatives supply the higher-order terms. Our steering head is a raw
        linear regression, so those analytic derivatives are zero and a literal
        port would degenerate back to plain Grad-CAM. We therefore use the
        common practical approximation (as in the reference Grad-CAM++
        implementations): estimate the higher-order terms from powers of the
        *first-order* gradient and the activations directly --
        ``alpha = g^2 / (2 g^2 + (sum_ab A_ab) g^3)`` -- which stays
        non-degenerate because the steering gradient w.r.t. conv2d_5 varies
        across space (the flatten+dense head is position-dependent).

        :param norm_img: float32 image, [0,1], shape (H, W, C)
        :return: np array (N, h, w) of per-pass Grad-CAM++ maps, each
                 max-normalised to [0, 1] (like :meth:`attention_maps`).
        """
        batch = tf.convert_to_tensor(
            np.repeat(norm_img[np.newaxis, ...], self.num_passes, axis=0))

        with tf.GradientTape() as tape:
            features, steering = self.grad_model(batch, training=True)
            target = tf.reduce_sum(steering)
        grads = tape.gradient(target, features)          # (N, h, w, c)

        grads2 = grads ** 2
        grads3 = grads ** 3
        # sum of activations per channel (the (sum_ab A_ab) term), broadcast
        # back over the spatial grid.
        global_sum = tf.reduce_sum(features, axis=(1, 2), keepdims=True)
        denom = 2.0 * grads2 + global_sum * grads3
        denom = tf.where(tf.abs(denom) > 1e-10, denom, tf.ones_like(denom))
        alphas = grads2 / denom
        # Per-channel weights: alpha-weighted sum of the positive gradients.
        weights = tf.reduce_sum(alphas * tf.nn.relu(grads),
                                axis=(1, 2), keepdims=True)
        cams = tf.nn.relu(tf.reduce_sum(weights * features, axis=-1))
        cams = cams.numpy()                              # (N, h, w)

        maxes = cams.reshape(self.num_passes, -1).max(axis=1)
        maxes[maxes == 0] = 1.0
        return cams / maxes[:, None, None]

    def attention_pp_map(self, img_arr):
        """
        Mean Grad-CAM++ attention map for a frame, upsampled to image size and
        normalised to [0,1] -- the ++ analogue of the mean-attention map that
        :meth:`uncertainty_map` returns as ``mean_map``.

        :param img_arr: uint8 [0,255] camera frame (H, W, C)
        :return: (H, W) float map in [0,1].
        """
        from donkeycar.utils import normalize_image
        norm = normalize_image(img_arr).astype(np.float32)
        cams = self.attention_maps_pp(norm)
        mean_map = cams.mean(axis=0)

        h, w = img_arr.shape[:2]
        up = _resize_map(mean_map, w, h)
        if up.max() > 0:
            up = up / up.max()
        return up

    def uncertainty_map(self, img_arr):
        """
        :param img_arr: uint8 [0,255] camera frame (H, W, C)
        :return: (mean_map, var_map) both float (H, W) upsampled to image
                 size; mean_map in [0,1], var_map normalised to [0,1] with
                 its raw peak value returned as third element.
        """
        from donkeycar.utils import normalize_image
        norm = normalize_image(img_arr).astype(np.float32)
        cams = self.attention_maps(norm)

        mean_map = cams.mean(axis=0)
        var_map = cams.var(axis=0)
        raw_peak = float(var_map.max())

        h, w = img_arr.shape[:2]
        mean_up = _resize_map(mean_map, w, h)
        var_up = _resize_map(var_map, w, h)
        if raw_peak > 0:
            var_up = var_up / var_up.max()
        if mean_up.max() > 0:
            mean_up = mean_up / mean_up.max()
        return mean_up, var_up, raw_peak

    def novelty_map(self, img_arr, mean, var, active_dims=None, eps=1e-6,
                    extractor=None):
        """
        Spatial Mahalanobis-distance "novelty" map: how far each grid
        location's feature vector is from the training distribution (see
        donkeycar.parts.novelty). Needs no dropout stochasticity and no
        gradient -- a single plain forward pass -- since novelty is a
        distance-from-training-distribution measure, not an agreement measure.

        Features come from the GENERIC ImageNet encoder, the same space the
        live novelty score is measured in, evaluated on the RAW frame. The
        steering model's own conv features were used here originally, but
        that space is task-collapsed (a network trained only to predict
        steering discards the texture/colour that tells grass from track),
        and it sees transformed pixels, so the heat map and the percentage
        beside it were answering different questions.

        :param img_arr:  uint8 [0,255] RAW camera frame (H, W, C)
        :param mean, var, active_dims, eps: the fitted 'novelty_ood_spatial'
                                            calibration block's stats.
        :param extractor: a donkeycar.parts.ood.SpatialEncoderExtractor.
        :return: (map01, raw_peak) -- map01 is (H, W) upsampled to image
                 size and normalised to [0,1]; raw_peak is the pre-
                 normalisation peak distance (for the readout/debugging).
        """
        from donkeycar.parts.novelty import mahalanobis_diag

        feat = extractor.extract_grid(img_arr)            # (gh, gw, c)

        dist_grid = mahalanobis_diag(feat, mean, var, active_dims, eps)
        raw_peak = float(dist_grid.max())

        h, w = img_arr.shape[:2]
        up = _resize_map(dist_grid, w, h)
        if raw_peak > 0:
            up = up / up.max()
        return up, raw_peak


def _resize_map(map2d, width, height):
    """Bilinear upsample a float map to (height, width)."""
    img = Image.fromarray(map2d.astype(np.float32), mode='F')
    return np.asarray(img.resize((width, height), Image.BILINEAR))


def _jet(x):
    """Simple jet colormap: float map [0,1] -> float RGB (H, W, 3)."""
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def overlay_heatmap(img_arr, map01, strength=0.6):
    """
    Blend a [0,1] heat map over a uint8 image; the map value doubles as the
    per-pixel alpha so cold regions stay as plain camera image.
    """
    base = img_arr.astype(np.float32) / 255.0
    heat = _jet(map01)
    alpha = (map01 * strength)[..., None]
    out = base * (1 - alpha) + heat * alpha
    return (out * 255).astype(np.uint8)


def _model_input_processor(cfg):
    """
    Build the raw-frame -> model-input mapping for this config.

    TRANSFORMATIONS (crop, trapeze, colour-space, high-pass, ...) apply at
    both training and inference, so anything measuring the MODEL's behaviour
    has to see transformed pixels or it is describing a network state that
    never occurs while driving. Mask-style transforms keep image dimensions,
    so getting this wrong produces no error -- just wrong numbers and
    misleading heat maps. Mirrors BatchSequence.image_processor in
    pipeline/training.py (minus the training-only augmentation step).

    Returns an identity function when nothing is configured.
    """
    tfm = list(getattr(cfg, 'TRANSFORMATIONS', None) or [])
    post = list(getattr(cfg, 'POST_TRANSFORMATIONS', None) or [])
    if not tfm and not post:
        return lambda img: img
    from donkeycar.parts.image_transformations import ImageTransformations
    transformation = ImageTransformations(cfg, 'TRANSFORMATIONS')
    post_transformation = ImageTransformations(cfg, 'POST_TRANSFORMATIONS')
    return lambda img: post_transformation.run(transformation.run(img))


def _model_input_differs(img, disp):
    """True if the transformation pipeline actually changed the pixels, so
    an unchanged pipeline doesn't double every frame on disk for nothing."""
    if img is None or disp is None:
        return False
    if img.shape != disp.shape:
        return True
    return not np.array_equal(img, disp)


def _as_displayable(img):
    """Coerce a model input to something a browser can render as a jpg.

    Transformations are free to emit shapes a viewer can't show directly,
    e.g. single-channel output (RGB2GRAY, CANNY). Those are displayed as-is
    rather than being reinterpreted, which is the honest thing to show --
    it IS what the network receives.
    """
    arr = np.asarray(img)
    if arr.dtype != np.uint8:
        finite = np.isfinite(arr)
        lo = float(arr[finite].min()) if finite.any() else 0.0
        hi = float(arr[finite].max()) if finite.any() else 1.0
        span = max(hi - lo, 1e-6)
        arr = np.clip((arr - lo) / span * 255.0, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        return np.dstack([arr] * 3)
    if arr.ndim == 3 and arr.shape[2] == 1:
        return np.dstack([arr[:, :, 0]] * 3)
    if arr.ndim == 3 and arr.shape[2] > 3:
        return arr[:, :, :3]
    return arr


def _fit_map_to(map2d, img_arr):
    """Resize a heat map to an image's dimensions, for the case where the
    model input and the frame we draw on aren't the same size (e.g. a RESIZE
    transformation). A no-op in the common mask-transform case."""
    h, w = img_arr.shape[:2]
    if map2d.shape[:2] == (h, w):
        return map2d
    return _resize_map(map2d, w, h)


def _collect_variances(records, pilot, cfg, num_passes, alpha,
                       progress_callback=None):
    """
    Get a per-frame smoothed steering-variance list, preferring values
    logged in the tub (drives recorded with XAI_CONFIDENCE_ENABLED
    enabled), else replaying the frames through the MC-Dropout part.

    Entries are ``None`` for frames whose value is genuinely unknown (logged
    by a drive where the pilot wasn't running for part of it); callers must
    treat those as missing rather than as a variance of zero.

    :param pilot:             an already-loaded KerasLinear, so a single
                              analysis run doesn't deserialise the model once
                              per collection stage.
    :param progress_callback: optional ``callback(stage, current, total)``,
                              called as frames are processed (stage='variance').
                              Used by the GUI launcher to show progress; safe
                              to omit for CLI use.
    """
    logged = [r.underlying.get('pilot/smoothed_variance') for r in records]
    n_logged = sum(v is not None for v in logged)
    if n_logged >= 0.5 * len(records) and n_logged > 0:
        logger.info(f'Using logged uncertainty for {n_logged}/{len(records)} '
                    f'frames.')
        if progress_callback:
            progress_callback('variance', len(records), len(records))
        # Frames the pilot wasn't running for stay None (unknown), NOT 0.0 --
        # 0.0 is the lowest possible variance, i.e. an assertion of maximum
        # confidence, which would both misreport them in the timeline and
        # guarantee they are never picked by --top-k.
        return list(logged)

    logger.info(f'No logged uncertainty in tub; replaying {len(records)} '
                f'frames through MC-Dropout (N={num_passes})...')
    from donkeycar.parts.mc_dropout import MCDropoutConfidence
    part = MCDropoutConfidence(pilot, num_passes=num_passes, alpha=alpha)
    to_model = _model_input_processor(cfg)   # confidence probes the model
    smoothed = []
    total = len(records)
    for i, record in enumerate(records):
        smoothed.append(part.run(to_model(record.image()))[4])
        if (i + 1) % 200 == 0:
            logger.info(f'  {i + 1}/{total} frames')
        if progress_callback:
            progress_callback('variance', i + 1, total)
    return smoothed


def _collect_novelty(records, model_path, cfg, calib, progress_callback=None):
    """
    Get a per-frame smoothed novelty (Mahalanobis) distance list, preferring
    values logged in the tub, else replaying through FeatureNoveltyDetector.
    Returns a list of raw floats (distances, NOT scores) the same length as
    `records`, or None if no 'novelty_ood' calibration is available at all
    (nothing to score against). Distances are in the generic-encoder feature
    space, so they must be scored with the 'novelty_ood' anchors.

    :param progress_callback: optional ``callback(stage, current, total)``,
                              called as frames are processed (stage='novelty').
    """
    if calib is None or calib.get('novelty_ood') is None:
        return None

    logged = [r.underlying.get('pilot/smoothed_novelty_distance')
             for r in records]
    n_logged = sum(v is not None for v in logged)
    if n_logged >= 0.5 * len(records) and n_logged > 0:
        logger.info(f'Using logged novelty distance for {n_logged}/'
                    f'{len(records)} frames.')
        if progress_callback:
            progress_callback('novelty', len(records), len(records))
        # None means unknown (pilot wasn't running for that frame), not a
        # distance of zero -- see _collect_variances.
        return list(logged)

    logger.info(f'No logged novelty distance in tub; replaying '
                f'{len(records)} frames through FeatureNoveltyDetector...')
    from donkeycar.parts.mc_calibrate import default_calib_path
    from donkeycar.parts.novelty import FeatureNoveltyDetector
    # No pilot needed: novelty scores with its own generic ImageNet encoder,
    # and FeatureNoveltyDetector's `pilot` argument is unused.
    part = FeatureNoveltyDetector(calibration_path=default_calib_path(model_path))
    smoothed = []
    total = len(records)
    for i, record in enumerate(records):
        # RAW frame on purpose -- novelty measures scene familiarity in a
        # frozen ImageNet encoder, and TRANSFORMATIONS strip the colour and
        # texture that encoder depends on. Matches the live wiring in
        # templates/complete.py and the calibration in mc_calibrate.py.
        smoothed.append(part.run(record.image())[2])
        if (i + 1) % 200 == 0:
            logger.info(f'  {i + 1}/{total} frames')
        if progress_callback:
            progress_callback('novelty', i + 1, total)
    return smoothed


def _collect_tta(records, pilot, model_path, cfg, calib,
                 progress_callback=None):
    """
    Get a per-frame smoothed TTA (test-time augmentation) steering-variance
    list, preferring values logged in the tub, else replaying through
    TTAStabilityDetector. Returns a list the same length as `records` (with
    ``None`` for frames whose value is unknown), or None if the model's
    calibration has no 'tta' block.

    :param pilot:             an already-loaded KerasLinear (see
                              ``_collect_variances``).
    :param progress_callback: optional ``callback(stage, current, total)``,
                              called as frames are processed (stage='tta').
    """
    if calib is None or calib.get('tta') is None:
        return None

    logged = [r.underlying.get('pilot/smoothed_tta_variance') for r in records]
    n_logged = sum(v is not None for v in logged)
    if n_logged >= 0.5 * len(records) and n_logged > 0:
        logger.info(f'Using logged TTA variance for {n_logged}/'
                    f'{len(records)} frames.')
        if progress_callback:
            progress_callback('tta', len(records), len(records))
        # None means unknown (pilot wasn't running for that frame), not a
        # variance of zero -- see _collect_variances.
        return list(logged)

    logger.info(f'No logged TTA variance in tub; replaying {len(records)} '
                f'frames through TTAStabilityDetector...')
    from donkeycar.parts.mc_calibrate import default_calib_path
    from donkeycar.parts.tta import TTAStabilityDetector
    part = TTAStabilityDetector(
        pilot, calibration_path=default_calib_path(model_path),
        num_samples=getattr(cfg, 'XAI_TTA_SAMPLES', 8),
        alpha=getattr(cfg, 'XAI_TTA_ALPHA', 0.2),
        strength=getattr(cfg, 'XAI_TTA_STRENGTH', 0.2), seed=0)
    to_model = _model_input_processor(cfg)   # TTA probes the model
    smoothed = []
    total = len(records)
    for i, record in enumerate(records):
        smoothed.append(part.run(to_model(record.image()))[2])
        if (i + 1) % 200 == 0:
            logger.info(f'  {i + 1}/{total} frames')
        if progress_callback:
            progress_callback('tta', i + 1, total)
    return smoothed


def analyze_tub(cfg, tub_path, model_path, out_dir, num_passes=15, alpha=0.2,
                top_k=50, percentile=None, analyze_all=False, limit=None,
                start=None, export_frames=False, ig_steps=32,
                progress_callback=None, verify_preprocessing=True):
    """
    Run the full Feature 3 pipeline on one tub. Returns the data.json dict.

    :param start:             skip this many records from the start of the
                              tub before considering any frames -- combined
                              with ``limit``, lets you scope to a specific
                              range of the drive (e.g. ``start=1000,
                              limit=1000`` looks at records 1000-1999).
                              None/0 (default) starts from the first record.
    :param limit:             only consider this many records after ``start``.
                              None (default) considers the rest of the tub.
    :param ig_steps:          number of Riemann-sum steps for the Integrated
                              Gradients overlay (offline pixel attribution).
    :param progress_callback: optional ``callback(stage, current, total)``,
                              called throughout the three stages in order
                              ('variance', 'novelty', 'gradcam'). Used by the
                              GUI launcher (``donkeycar.parts.uncertainty_viewer``)
                              to show live progress; harmless to omit for CLI use.
    :param verify_preprocessing: raise if ``cfg``'s TRANSFORMATIONS /
                              POST_TRANSFORMATIONS / ROI_CROP_*
                              don't match what ``model_path`` was actually
                              trained with (per its ``.preprocessing.json``
                              sidecar). ``cfg`` here comes from ``--config``
                              (CLI) or the launcher's config, and nothing
                              otherwise ties it to the model being analysed --
                              every heat map and the ``model_input`` layer
                              would be silently computed on the wrong pixels.
                              Set False only when the caller has deliberately
                              chosen a different pipeline than the model was
                              trained with (e.g. the launcher's transformations
                              override) and knows that.
    """
    from donkeycar.parts.keras import KerasLinear
    from donkeycar.parts.mc_calibrate import (default_calib_path,
                                              load_calibration,
                                              variance_to_confidence,
                                              novelty_distance_to_score)
    from donkeycar.parts.salient import (VanillaGradientSaliency,
                                         IntegratedGradients)
    from donkeycar.pipeline.types import TubDataset

    t0 = time.time()
    model_path = os.path.expanduser(model_path)
    tub_path = os.path.expanduser(tub_path)

    # Load the pilot once and share it across every stage below -- each
    # collection stage used to deserialise the same .h5 again for itself.
    pilot = KerasLinear()
    pilot.load(model_path)

    # Reconcile config image size with the model's own input shape BEFORE
    # building the dataset -- records are resized per cfg, so a mismatch here
    # surfaces later as an unreadable Keras shape error mid-forward-pass.
    # This deliberately treats the model file as the authority and rewrites
    # cfg (warning loudly), so a model can be analysed without tracking down
    # the exact config.py it was trained with.
    from donkeycar.parts.mc_calibrate import check_model_image_size
    check_model_image_size(model_path, cfg, model=pilot.interpreter.model)

    if verify_preprocessing:
        from donkeycar.parts.image_transformations import \
            check_preprocessing_metadata
        # Resolution is excluded because the call above just SET cfg's
        # IMAGE_W/IMAGE_H from this very model -- comparing them here could
        # only ever agree, so leaving them in would look like a check while
        # being incapable of failing. check_model_image_size already reports
        # any disagreement it reconciled. Everything the model file cannot
        # self-describe (the crop geometry and the transformation step list)
        # is still enforced strictly.
        check_preprocessing_metadata(
            cfg, model_path, context="this analysis's config",
            skip_keys=('image_width', 'image_height'))

    dataset = TubDataset(config=cfg, tub_paths=[tub_path])
    records = dataset.get_records()
    if start or limit:
        s = start or 0
        e = (s + limit) if limit else None
        records = records[s:e]
    if not records:
        raise ValueError(f'No records found in {tub_path}')

    # Per-frame uncertainty timeline (logged or replayed). Entries can be
    # None where the tub has no value for that frame.
    variances = _collect_variances(records, pilot, cfg, num_passes, alpha,
                                   progress_callback=progress_callback)

    # Confidence % (and novelty stats, if present) from the model's calibration.
    calib = None
    calib_path = default_calib_path(model_path)
    if os.path.exists(calib_path):
        calib = load_calibration(calib_path)
        logger.info(f'Loaded calibration {calib_path}')
    else:
        logger.warning(f'No calibration at {calib_path}; timeline will have '
                       f'variance only.')

    def conf(v):
        if calib is None or v is None:
            return None
        return variance_to_confidence(v, calib)

    # Per-frame novelty (out-of-distribution) timeline -- cheap, every frame,
    # independent of the Grad-CAM frame selection below. None if the model's
    # calibration has no novelty stats at all (older calibration).
    novelty_distances = _collect_novelty(records, model_path, cfg, calib,
                                         progress_callback=progress_callback)

    def nov_score(d):
        if calib is None or calib.get('novelty_ood') is None or d is None:
            return None
        return novelty_distance_to_score(d, calib['novelty_ood'])

    # Per-frame TTA (test-time augmentation) stability timeline -- cheap-ish,
    # every frame, independent of the Grad-CAM frame selection. None if the
    # model's calibration has no 'tta' block.
    tta_variances = _collect_tta(records, pilot, model_path, cfg, calib,
                                 progress_callback=progress_callback)

    def tta_stability(var):
        if calib is None or calib.get('tta') is None or var is None:
            return None
        from donkeycar.parts.mc_calibrate import tta_variance_to_stability
        return tta_variance_to_stability(var, calib['tta'])

    # Record WHY any signal is absent, so the viewer can say so instead of
    # just silently omitting a line from the graph. A missing signal and a
    # signal that happens to be flat look identical otherwise.
    from donkeycar.parts.mc_calibrate import missing_calibration_reason
    signals_unavailable = []
    for key, label, signal in (('confidence', 'Confidence', 'confidence'),
                               ('novelty_score', 'Novelty', 'novelty'),
                               ('tta_stability', 'TTA stability', 'tta')):
        reason = missing_calibration_reason(calib_path, signal)
        if reason:
            signals_unavailable.append(
                {'key': key, 'label': label, 'reason': reason})
            logger.info(f'{label} will not appear in the timeline: {reason}')

    timeline = []
    for i, (record, v) in enumerate(zip(records, variances)):
        nd = novelty_distances[i] if novelty_distances is not None else None
        tv = tta_variances[i] if tta_variances is not None else None
        timeline.append({
            'index': record.underlying.get('_index'),
            'timestamp_ms': record.underlying.get('_timestamp_ms'),
            'variance': float(v) if v is not None else None,
            'confidence': conf(v),
            'novelty_distance': nd,
            'novelty_score': nov_score(nd),
            'tta_variance': tv,
            'tta_stability': tta_stability(tv),
            # image filename inside the tub's images/ dir, so the viewer can
            # show the camera frame for non-analysed frames when the tub is
            # available locally.
            'tub_image': record.underlying.get('cam/image_array'),
        })

    # Optionally export every camera frame so the analysis dir is fully
    # self-contained (playback works with just this folder, no tub needed --
    # useful when copying results off a cluster). ~5-8 KB per frame.
    if export_frames:
        frames_dir = os.path.join(out_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        logger.info(f'Exporting {len(records)} camera frames to {frames_dir}')
        for record, entry in zip(records, timeline):
            name = f"{entry['index']:06d}.jpg"
            Image.fromarray(record.image()).save(
                os.path.join(frames_dir, name))
            entry['image'] = f'frames/{name}'

    # Select frames to analyse. Frames with an unknown variance are ranked
    # and thresholded on nothing at all -- they are simply not candidates for
    # the uncertainty-driven modes, rather than being treated as variance 0
    # (which would rank them as the MOST certain frames in the drive).
    known = [i for i, v in enumerate(variances) if v is not None]
    if len(known) < len(records):
        logger.warning(
            f'{len(records) - len(known)}/{len(records)} frames have no '
            f'uncertainty value (the pilot was not running for them); they '
            f'stay in the timeline but are excluded from frame selection.')
    if analyze_all:
        selected = list(range(len(records)))
    elif percentile is not None:
        if not known:
            raise ValueError('No frame has an uncertainty value, so a '
                             'percentile cannot be computed. Use --all, or '
                             'analyse a tub recorded with the pilot running.')
        thresh = float(np.percentile([variances[i] for i in known], percentile))
        selected = [i for i in known if variances[i] >= thresh]
        logger.info(f'{len(selected)} frames at/above p{percentile} '
                    f'(variance >= {thresh:.6f})')
    else:
        # most uncertain first, among the frames that have a value
        order = sorted(known, key=lambda i: variances[i], reverse=True)
        selected = order[:top_k]
    logger.info(f'Analysing {len(selected)} of {len(records)} frames.')

    # Build the Grad-CAM and vanilla-gradient-saliency engines on the raw
    # Keras model (two independent, complementary attribution methods), reusing
    # the pilot loaded at the top rather than deserialising it again.
    from donkeycar.utils import normalize_image
    engine = GradCamUncertainty(pilot.interpreter.model, num_passes=num_passes)
    saliency_engine = VanillaGradientSaliency(pilot.interpreter.model)
    ig_engine = IntegratedGradients(pilot.interpreter.model, steps=ig_steps)

    # Spatial novelty stats, if this model's calibration has them. Needs the
    # generic encoder (kept unpooled) rather than the steering model, so the
    # heat map is measured in the same space as the novelty percentage.
    novelty_spatial = calib.get('novelty_ood_spatial') if calib else None
    ns_extractor = None
    if novelty_spatial is not None:
        try:
            from donkeycar.parts.ood import SpatialEncoderExtractor
            ns_extractor = SpatialEncoderExtractor(
                novelty_spatial.get('encoder', 'mobilenet_v2'),
                input_hw=tuple(novelty_spatial['input_hw']),
                alpha=novelty_spatial.get('alpha', 1.0))
            ns_mean = np.array(novelty_spatial['mean'])
            ns_var = np.array(novelty_spatial['var'])
            ns_active = np.array(novelty_spatial['active_dims'])
            ns_eps = novelty_spatial['eps']
        except Exception as e:
            logger.warning(f'Could not build the spatial novelty encoder '
                           f'({e}); the novelty heat map will be skipped.')
            novelty_spatial = None
    elif calib is not None:
        logger.info('No "novelty_ood_spatial" block in this calibration '
                    '(built before the encoder-space map, or the encoder was '
                    'unavailable); novelty heat map will be skipped.')

    images_dir = os.path.join(out_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    frames = {}
    to_model = _model_input_processor(cfg)
    model_input_available = False
    for n, i in enumerate(sorted(selected)):
        record = records[i]
        # Two images per frame, on purpose:
        #   disp  -- the raw camera frame, what a human recognises.
        #   img   -- what the model is actually fed (transformed). Every
        #            gradient/attribution is computed against this, or it
        #            would be explaining behaviour on input the model never
        #            sees while driving.
        # Heat maps therefore come back in img's coordinates. Every
        # transformation available here preserves the frame's geometry (CROP
        # and TRAPEZE mask rather than resize), so a map drawn on the raw
        # frame lands on the right pixels; it is also saved drawn directly on
        # img (the '_mi' variants) whenever the transformation changed the
        # pixels, so the model's own view can be inspected.
        disp = record.image()
        img = to_model(disp)
        idx = record.underlying.get('_index', i)

        model_view = _as_displayable(img)
        # Only worth a second copy of every map when the model input actually
        # differs; otherwise the two overlays would be identical images.
        want_mi = _model_input_differs(img, disp)
        model_input_available = model_input_available or want_mi

        def save_map(map_model_space, suffix, key, entry):
            """Save one heat map twice: on the raw frame, and drawn directly
            on the model input."""
            raw_map = _fit_map_to(map_model_space, disp)
            name = f'{idx:06d}_{suffix}.png'
            Image.fromarray(overlay_heatmap(disp, raw_map)).save(
                os.path.join(images_dir, name))
            entry[key] = f'images/{name}'
            if want_mi:
                mi_map = _fit_map_to(map_model_space, model_view)
                mi_name = f'{idx:06d}_{suffix}_mi.png'
                Image.fromarray(overlay_heatmap(model_view, mi_map)).save(
                    os.path.join(images_dir, mi_name))
                entry[key + '_mi'] = f'images/{mi_name}'

        mean_map, var_map, raw_peak = engine.uncertainty_map(img)
        orig_name = f'{idx:06d}_orig.jpg'
        Image.fromarray(disp).save(os.path.join(images_dir, orig_name))

        frame_entry = {
            'orig': f'images/{orig_name}',
            'variance': (float(variances[i])
                         if variances[i] is not None else None),
            'confidence': conf(variances[i]),
            'attention_variance_peak': raw_peak,
        }
        save_map(var_map, 'unc', 'overlay', frame_entry)
        save_map(mean_map, 'attn', 'attention', frame_entry)

        # The model input itself, saved whenever it differs from the raw
        # frame, so the transformation pipeline can be eyeballed directly.
        if want_mi:
            model_input_name = f'{idx:06d}_model_input.jpg'
            Image.fromarray(model_view).save(
                os.path.join(images_dir, model_input_name))
            frame_entry['model_input'] = f'images/{model_input_name}'

        # Grad-CAM++ attention (sharper, multi-region variant of 'attention').
        save_map(engine.attention_pp_map(img), 'attnpp', 'attention_pp',
                 frame_entry)

        if novelty_spatial is not None:
            # RAW frame: novelty is measured on untransformed pixels, matching
            # the live detector and the timeline's novelty %. Its map is
            # therefore already in raw coordinates - it must NOT be projected,
            # and there is no model-input variant to show.
            nov_map, nov_peak = engine.novelty_map(
                disp, ns_mean, ns_var, ns_active, ns_eps,
                extractor=ns_extractor)
            nov_map = _fit_map_to(nov_map, disp)
            nov_name = f'{idx:06d}_novelty.png'
            Image.fromarray(overlay_heatmap(disp, nov_map)).save(
                os.path.join(images_dir, nov_name))
            frame_entry['novelty'] = f'images/{nov_name}'
            frame_entry['novelty_map_peak'] = nov_peak

        norm_img = normalize_image(img).astype(np.float32)
        save_map(saliency_engine.saliency_map(norm_img), 'saliency',
                 'saliency', frame_entry)
        # Integrated Gradients: cleaner, axiomatic pixel attribution.
        save_map(ig_engine.saliency_map(norm_img), 'ig',
                 'integrated_gradients', frame_entry)

        frames[str(idx)] = frame_entry
        if (n + 1) % 10 == 0:
            logger.info(f'  analysed {n + 1}/{len(selected)} frames')
        if progress_callback:
            progress_callback('gradcam', n + 1, len(selected))

    data = {
        'model': os.path.basename(model_path),
        'tub': tub_path,
        'num_passes': num_passes,
        'alpha': alpha,
        'n_records': len(records),
        'n_analyzed': len(selected),
        'frames_exported': bool(export_frames),
        # True when TRANSFORMATIONS actually changed the pixels, so a
        # '<layer>_mi' variant drawn on the model input also exists.
        'model_input_available': model_input_available,
        'created': time.strftime('%Y-%m-%d %H:%M:%S'),
        'note': ('Attention-variance maps from MC-Dropout Grad-CAM. '
                 'Relative per-model signal, not a calibrated probability.'),
        'timeline': timeline,
        'frames': frames,
        'signals_unavailable': signals_unavailable,
    }
    with open(os.path.join(out_dir, 'data.json'), 'w') as f:
        json.dump(data, f)
    dataset.close()
    logger.info(f'Done in {time.time() - t0:.1f}s -> {out_dir} '
                f'({len(selected)} frames analysed)')
    return data


def main(args=None):
    import donkeycar as dk

    parser = argparse.ArgumentParser(
        prog='gradcam_uncertainty',
        description='Offline Grad-CAM uncertainty maps for a recorded tub.')
    parser.add_argument('--tub', required=True, help='tub path to analyse')
    parser.add_argument('--model', required=True, help='path to .h5 model')
    parser.add_argument('--config', default=None, help='path to config.py')
    parser.add_argument('--out', default=None,
                        help='output dir (default <tub>/gradcam_analysis)')
    parser.add_argument('--passes', type=int, default=None,
                        help='MC-Dropout passes (default cfg or 15)')
    parser.add_argument('--top-k', type=int, default=50,
                        help='analyse the K most uncertain frames (default)')
    parser.add_argument('--percentile', type=float, default=None,
                        help='instead analyse frames >= this variance '
                             'percentile (e.g. 90)')
    parser.add_argument('--ig-steps', type=int, default=None,
                        help='Integrated Gradients Riemann steps '
                             '(default cfg XAI_IG_STEPS or 32)')
    parser.add_argument('--all', action='store_true',
                        help='analyse every frame (short drives only)')
    parser.add_argument('--limit', type=int, default=None,
                        help='only consider N records (from --start, or the '
                             'beginning of the tub)')
    parser.add_argument('--start', type=int, default=None,
                        help='skip this many records from the start of the '
                             'tub before considering any frames -- combine '
                             'with --limit for a specific range, e.g. '
                             '--start 1000 --limit 1000 for records 1000-1999')
    parser.add_argument('--export-frames', action='store_true',
                        help='also copy every camera frame into the output '
                             'dir so playback in the viewer works without '
                             'the tub present (self-contained results)')
    parsed = parser.parse_args(args)

    from donkeycar.parts.image_transformations import \
        load_config_and_myconfig
    cfg = load_config_and_myconfig(parsed.config)

    num_passes = parsed.passes or getattr(cfg, 'XAI_CONFIDENCE_PASSES', 15)
    alpha = getattr(cfg, 'XAI_CONFIDENCE_ALPHA', 0.2)
    ig_steps = parsed.ig_steps or getattr(cfg, 'XAI_IG_STEPS', 32)
    out_dir = parsed.out or os.path.join(os.path.expanduser(parsed.tub),
                                         'gradcam_analysis')

    data = analyze_tub(cfg, parsed.tub, parsed.model, out_dir,
                       num_passes=num_passes, alpha=alpha,
                       top_k=parsed.top_k, percentile=parsed.percentile,
                       analyze_all=parsed.all, limit=parsed.limit,
                       start=parsed.start,
                       export_frames=parsed.export_frames, ig_steps=ig_steps)
    print(f"\nGrad-CAM uncertainty analysis complete:")
    print(f"  frames in drive : {data['n_records']}")
    print(f"  frames analysed : {data['n_analyzed']}")
    print(f"  output          : {out_dir}")
    print(f"\nView it with:")
    print(f"  python -m donkeycar.parts.uncertainty_viewer "
          f"--analysis {out_dir}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
