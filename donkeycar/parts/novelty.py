"""
Feature-space novelty (out-of-distribution) detection.

MC-Dropout variance (``donkeycar.parts.mc_dropout``) measures whether the
model's dropout sub-networks *agree* with each other -- an ambiguity signal.
It does NOT measure whether the current input looks anything like the data
the model was trained on: a scene the network has never seen can still get a
confident, low-variance (wrong) answer if its sub-networks happen to agree.
This module adds the complementary signal: how far the current frame is from
the training distribution, via Mahalanobis distance in a feature space.

WHICH feature space matters a lot. The live ``FeatureNoveltyDetector`` now
measures distance in a GENERIC image encoder's features (see
``donkeycar.parts.ood``), NOT the steering model's own ``dense_2`` layer. The
steering model is trained only to predict an angle, so it discards the scene
content (texture/colour/semantics) that distinguishes grass from track --
measuring novelty there barely responded to genuinely different scenes. The
generic encoder keeps that content, so the same Mahalanobis math actually
separates scenes. This module still owns the distance math; the feature
source moved to ``donkeycar.parts.ood``.

Consumers:
  * ``FeatureNoveltyDetector`` -- a live Part computing one scalar novelty
    score per frame from generic-encoder features (one encoder forward pass;
    no MC-Dropout stochasticity needed since this isn't measuring agreement).
  * ``donkeycar.parts.gradcam_uncertainty`` -- reuses ``mahalanobis_diag``
    directly on the steering model's ``conv2d_5`` features (pooled across
    space) to render a spatial "where is this unfamiliar" heatmap for offline
    analysis. NOTE: this offline spatial map still uses the steering model's
    features and so inherits the task-collapse limitation above; it is a
    lower-priority, coarse localisation aid, not the primary novelty signal.

Caveats (read before trusting the numbers):
  * **Diagonal covariance only.** Feature dimensions are treated as
    independent (per-dimension mean/variance, not a full covariance
    matrix). Cheap and numerically robust, but ignores correlations
    between features -- a combination of individually-normal feature
    values could still be jointly unusual and go undetected.
  * **Position-independent spatial pooling.** The spatial (conv2d_5)
    statistics pool every grid location across every calibration frame
    into one distribution, discarding *where* in the image a feature
    normally appears. This is simple and cheap, but can mask novelty in
    channels that have legitimate positional structure (e.g. a channel
    that reliably fires near the top of the frame for sky/horizon) --
    pooling folds that within-frame positional swing into the channel's
    "normal" variance, raising the bar for detecting genuine novelty
    there. A per-location (or coarse-grid) statistics model would fix
    this at the cost of real complexity; not done here.
  * **Dead-dimension handling.** A near-constant (e.g. dead ReLU) feature
    dimension has ~zero variance; naively dividing by it would let a
    single dimension dominate the whole distance. Dimensions are flagged
    "inactive" at calibration time (via a variance floor, relative to the
    typical variance across all dimensions) and excluded from the sum
    entirely, rather than papering over it with a global epsilon alone.
  * **Complementary, not a replacement, for MC-Dropout confidence.** A
    frame can be low-novelty (looks like training data) yet still
    high-variance (the model is internally torn about what to do), or
    the reverse (novel-looking, but the sub-networks still happen to
    agree). Read both signals together, not as substitutes.
  * **Model scope**: like the rest of this toolkit, only the default
    linear architecture (``KerasLinear``) with a callable Keras
    interpreter is supported -- not TFLite/TensorRT (their graphs cannot
    be reached by name to build the feature sub-model), and not other
    architectures (this module assumes layers named ``dense_2`` /
    ``conv2d_5`` from the default linear model).
"""
import logging
import os
import time

import numpy as np
import tensorflow as tf

from donkeycar.utils import normalize_image

logger = logging.getLogger(__name__)


def mahalanobis_diag(vec, mean, var, active_dims=None, eps=1e-6):
    """
    Diagonal-covariance Mahalanobis distance: sum((x_i - mean_i)^2 / (var_i + eps))
    over the active dimensions only.

    :param vec:         (..., d) array -- a single feature vector or a batch/
                        grid of them (any leading shape), last axis = features.
    :param mean:        (d,) array, per-dimension mean of the reference
                        (training) distribution.
    :param var:         (d,) array, per-dimension variance of the reference
                        distribution.
    :param active_dims: optional (d,) boolean array. Dimensions where False
                        are excluded from the sum entirely (see module
                        docstring on dead-dimension handling). Defaults to
                        all dimensions active.
    :param eps:         small constant added to variance for numerical safety
                        on the *active* dimensions (dead/near-zero-variance
                        dimensions should be excluded via active_dims instead
                        of relying on eps alone).
    :return:            scalar distance, or (...,) array of distances if vec
                        has leading batch/grid dimensions.
    """
    vec = np.asarray(vec, dtype=np.float64)
    mean = np.asarray(mean, dtype=np.float64)
    var = np.asarray(var, dtype=np.float64)
    if active_dims is None:
        active_dims = np.ones(mean.shape[0], dtype=bool)
    else:
        active_dims = np.asarray(active_dims, dtype=bool)

    diff_sq = (vec - mean) ** 2
    denom = var + eps
    terms = diff_sq / denom
    terms = terms * active_dims       # zero out inactive dimensions
    return terms.sum(axis=-1)


def fit_diagonal_gaussian(feature_matrix, min_var_frac=1e-3, abs_eps=1e-6):
    """
    Fit a diagonal Gaussian (per-dimension mean/variance) to a matrix of
    feature vectors, and flag dimensions too close to constant to trust.

    :param feature_matrix: (n_samples, d) array.
    :param min_var_frac:   a dimension is flagged "inactive" if its variance
                           is below `median(var) * min_var_frac` -- a floor
                           *relative* to this feature space's own typical
                           variance (an absolute constant would be the wrong
                           scale for different layers/models; see module
                           docstring).
    :param abs_eps:        absolute floor under the relative one, in case
                           every dimension happens to have tiny variance
                           (e.g. a degenerate/tiny calibration set).
    :return:               dict with 'mean', 'var', 'active_dims' (all lists,
                           JSON-serialisable), and 'eps' (float) -- the eps
                           to use for the active dimensions at scoring time.
    """
    feature_matrix = np.asarray(feature_matrix, dtype=np.float64)
    mean = feature_matrix.mean(axis=0)
    var = feature_matrix.var(axis=0)

    median_var = float(np.median(var))
    floor = max(median_var * min_var_frac, abs_eps)
    active_dims = var >= floor
    n_inactive = int((~active_dims).sum())
    if n_inactive:
        logger.info(f'fit_diagonal_gaussian: {n_inactive}/{len(var)} '
                    f'dimensions flagged inactive (variance < {floor:.3g}), '
                    f'excluded from distance calculation.')

    return {
        'mean': mean.tolist(),
        'var': var.tolist(),
        'active_dims': active_dims.tolist(),
        'eps': floor,
    }


class FeatureNoveltyDetector:
    """
    DonkeyCar Part. Computes a live "novelty" score for each frame: how far
    the frame sits from the training distribution, via diagonal-covariance
    Mahalanobis distance in the feature space of a GENERIC image encoder (see
    ``donkeycar.parts.ood``).

    IMPORTANT -- this used to measure distance in the steering model's own
    ``dense_2`` layer, but that feature space is task-collapsed: a model
    trained only to predict steering discards texture/colour/semantics, so
    grass, carpet and open track all mapped to nearly identical features and
    the score barely moved (it only reacted to gross changes like a covered
    camera). It now uses a separate ImageNet-pretrained encoder that keeps
    that scene content, which actually separates different scenes -- see the
    ``donkeycar.parts.ood`` module docstring for the measured before/after.

    Unlike ``MCDropoutConfidence``, this is a pure auxiliary observer -- it
    does NOT produce steering/throttle, and rides alongside whichever part
    already drives the car. One encoder forward pass per frame (no dropout
    stochasticity needed -- novelty is a distance-from-training measure). The
    encoder is independent of the steering pilot; the ``pilot`` argument is
    kept only for call-site compatibility and is not used.

    On slow/power-constrained hardware, ``interval`` rate-limits the encoder
    pass (mirroring ``MCDropoutConfidence``'s ``interval``). This part never
    drives, so between updates it holds the last score and skips the encoder
    pass entirely -- important, since the encoder is heavier than the old
    single steering-model pass.

    Run signature::

        score, raw_distance, smoothed_distance = part.run(img_arr)

    ``score`` is a 0-100 novelty % derived from the calibration file (see
    ``donkeycar.parts.mc_calibrate``), or ``None`` if the model has no
    calibration with a ``novelty_ood`` block, or the encoder could not be
    loaded.

    :param pilot:            kept for call-site compatibility; unused (novelty
                             now uses its own encoder, not the pilot's model).
    :param calibration_path: path to a ``<model>.calib.json`` with a
                             ``novelty_ood`` block, produced by
                             ``donkeycar.parts.mc_calibrate``. Optional.
    :param alpha:            EMA smoothing factor in [0, 1] for the raw
                             distance -- same role as MCDropoutConfidence's.
    :param interval:         minimum seconds between encoder passes. 0 (the
                             default) updates every frame. Between updates the
                             last score/distance is held and NO pass runs.
    """

    def __init__(self, pilot=None, calibration_path=None, alpha=0.2,
                 interval=0.0):
        self.alpha = float(alpha)
        self.smoothed_distance = None
        self.raw_distance = 0.0

        # Minimum seconds between updates. 0 = every frame. This part is a
        # pure observer (doesn't drive), so a held frame costs nothing --
        # no fallback pass needed, unlike MCDropoutConfidence.
        self.interval = float(interval)
        self.last_update_time = None

        self.extractor = None      # OOD feature extractor (generic encoder)
        self.calibration = None    # the 'novelty_ood' calib block

        if calibration_path:
            try:
                from donkeycar.parts.mc_calibrate import load_calibration
                calib = load_calibration(calibration_path)
                block = calib.get('novelty_ood')
                if block is None:
                    logger.warning(
                        f'FeatureNoveltyDetector: {calibration_path} has no '
                        f'"novelty_ood" stats (older calibration, or built '
                        f'before the encoder-based novelty fix); novelty will '
                        f'be unavailable -- re-run mc_calibrate to add it.')
                else:
                    self._load_encoder(block, calibration_path)
                    if self.extractor is not None:
                        self.calibration = block
                        logger.info(f'FeatureNoveltyDetector: loaded '
                                    f'encoder-based novelty calibration from '
                                    f'{calibration_path}')
            except Exception as e:
                logger.warning(f'FeatureNoveltyDetector: could not load '
                               f'calibration {calibration_path} ({e}); '
                               f'novelty score will be unavailable.')

    def _load_encoder(self, block, calibration_path):
        """Prefer the encoder sidecar saved next to the calibration (so a Pi
        driving offline needs no weight download); fall back to rebuilding the
        encoder from ImageNet weights (needs the cache/internet)."""
        from donkeycar.parts.ood import CPUEncoderExtractor
        ef = block.get('encoder_file')
        if ef and calibration_path:
            sidecar = os.path.join(
                os.path.dirname(os.path.abspath(calibration_path)), ef)
            if os.path.exists(sidecar):
                try:
                    m = tf.keras.models.load_model(sidecar, compile=False)
                    self.extractor = CPUEncoderExtractor(
                        block['encoder'], model=m)
                    logger.info(f'FeatureNoveltyDetector: loaded OOD encoder '
                                f'sidecar {sidecar}')
                    return
                except Exception as e:
                    logger.warning(f'FeatureNoveltyDetector: encoder sidecar '
                                   f'load failed ({e}); rebuilding from '
                                   f'ImageNet weights.')
        try:
            self.extractor = CPUEncoderExtractor(
                block['encoder'], block.get('input_size'),
                block.get('alpha', 1.0))
        except Exception as e:
            logger.warning(f'FeatureNoveltyDetector: could not build OOD '
                           f'encoder ({e}); novelty will be unavailable.')

    def run(self, img_arr, now=None):
        if img_arr is None:
            return self._score(), 0.0, (self.smoothed_distance or 0.0)

        # `now` lets a tub replay (mc_calibrate) drive the interval-throttle
        # off recorded timestamps instead of wall-clock time -- see
        # MCDropoutConfidence.run() for the full rationale.
        now = now if now is not None else time.time()
        if (self.interval > 0 and self.last_update_time is not None
                and (now - self.last_update_time) < self.interval):
            # Rate-limited: skip the encoder pass entirely and hold the last
            # values -- no fallback pass needed since this part never drives.
            return self._score(), self.raw_distance, \
                (self.smoothed_distance or 0.0)
        self.last_update_time = now

        if self.calibration is not None and self.extractor is not None:
            feat = self.extractor.extract(img_arr)
            mean = np.array(self.calibration['mean'])
            var = np.array(self.calibration['var'])
            active = np.array(self.calibration['active_dims'])
            eps = self.calibration['eps']
            raw_distance = float(
                mahalanobis_diag(feat, mean, var, active, eps))
        else:
            raw_distance = 0.0
        self.raw_distance = raw_distance

        if self.smoothed_distance is None:
            self.smoothed_distance = raw_distance
        else:
            self.smoothed_distance = (
                self.alpha * raw_distance
                + (1.0 - self.alpha) * self.smoothed_distance)

        return self._score(), raw_distance, self.smoothed_distance

    def _score(self):
        if self.calibration is None or self.smoothed_distance is None:
            return None
        from donkeycar.parts.mc_calibrate import novelty_distance_to_score
        return novelty_distance_to_score(self.smoothed_distance,
                                         self.calibration)

    def shutdown(self):
        pass
