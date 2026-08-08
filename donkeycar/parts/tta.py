"""
Test-Time Augmentation (TTA) stability -- a third live uncertainty signal.

MC-Dropout confidence (``donkeycar.parts.mc_dropout``) perturbs the model's
*weights* (dropout masks) and asks "do my sub-networks agree?". Novelty
(``donkeycar.parts.novelty``) perturbs nothing and asks "does this scene look
like training data?". TTA perturbs the *input image* and asks a third,
distinct question: "does my answer stay the same if the picture changes a
little?" -- i.e. robustness of the prediction to input noise, which neither of
the other two signals measures directly.

Mechanism: run the DETERMINISTIC model (dropout OFF, same weights every time)
on M lightly-augmented copies of the frame, and take the variance of the M
steering predictions. Low variance = the prediction is stable under input
perturbation = robust; high variance = fragile. The variance is EMA-smoothed
and mapped through the model's calibration to a 0-100 "stability %" (high =
robust), mirroring the confidence signal's machinery but with its own
calibration block (``calib['tta']``).

CRITICAL -- photometric augmentations ONLY. We perturb brightness, contrast,
gamma, and add a little gaussian noise: changes that do NOT move the road in
the image, so the *correct* steering answer is unchanged and any wobble in the
prediction is genuinely the model being fragile. We deliberately do NOT use
rotation / horizontal flip / large translation: those change the correct
answer (a flipped road really does turn the other way), which would conflate
"model is fragile" with "the scene genuinely changed". This keeps TTA a clean
"robustness to camera/lighting noise" signal. (Geometric TTA would require
applying the inverse transform to the output -- out of scope here.)

Like ``FeatureNoveltyDetector``, this is a pure auxiliary observer: it does
NOT produce steering/throttle and rides alongside whichever part drives the
car. M forward passes are batched into ONE deterministic call (same trick as
MC-Dropout), so it is cheap enough to run live -- but M passes every single
frame, unconditionally, is still real load on top of whatever else is
running (the driving pass, MC-Dropout's own N passes, novelty's single pass).
``XAI_TTA_INTERVAL`` rate-limits how often that M-pass update actually runs;
between updates the last score is held with ZERO forward passes (no fallback
pass needed, since this part never drives) -- the single biggest lever if
running multiple signals together is straining the hardware's power budget.

Model scope: like the rest of this toolkit, the default linear architecture
(``KerasLinear``) with a single image input and a callable Keras interpreter
-- not TFLite/TensorRT.
"""
import logging
import time

import numpy as np
import tensorflow as tf

from donkeycar.utils import normalize_image

logger = logging.getLogger(__name__)


def photometric_batch(norm_img, num_samples, strength, rng):
    """
    Build a batch of ``num_samples`` photometrically-augmented copies of a
    normalised image. Geometry is untouched (no spatial transform), so the
    correct steering answer is identical for every copy -- see the module
    docstring for why that matters.

    :param norm_img:    (H, W, C) float32 image in [0, 1].
    :param num_samples: M, the number of augmented copies.
    :param strength:    augmentation strength; brightness/contrast/gamma are
                        each jittered within +/- this fraction, gaussian noise
                        std is ``strength * 0.1``. 0 -> all copies identical.
    :param rng:         a ``numpy.random.Generator``.
    :return:            (M, H, W, C) float32 batch in [0, 1].
    """
    M = int(num_samples)
    imgs = np.repeat(norm_img[np.newaxis, ...], M, axis=0).astype(np.float32)

    # Per-sample photometric parameters, shaped to broadcast over (H, W, C).
    bright = rng.uniform(-strength, strength, (M, 1, 1, 1)).astype(np.float32)
    contrast = (1.0 + rng.uniform(-strength, strength,
                                  (M, 1, 1, 1))).astype(np.float32)
    gamma = (1.0 + rng.uniform(-strength, strength,
                               (M, 1, 1, 1))).astype(np.float32)

    # Contrast about each image's own mean, then a brightness shift.
    mean = imgs.mean(axis=(1, 2, 3), keepdims=True)
    imgs = (imgs - mean) * contrast + mean
    imgs = imgs + bright
    imgs = np.clip(imgs, 0.0, 1.0)
    # Gamma (safe on [0, 1]; gamma stays positive for strength < 1).
    imgs = np.power(imgs, gamma)
    # A little gaussian sensor noise.
    if strength > 0:
        imgs = imgs + rng.normal(0.0, strength * 0.1, imgs.shape).astype(np.float32)
    return np.clip(imgs, 0.0, 1.0)


class TTAStabilityDetector:
    """
    DonkeyCar Part. Computes a live "stability" score per frame: the variance
    of the deterministic model's steering prediction across M photometrically
    -augmented copies of the frame, EMA-smoothed and mapped to a 0-100 % (high
    = robust) via the model's ``calib['tta']`` block.

    Pure auxiliary observer (like ``FeatureNoveltyDetector``): does NOT drive.
    Each update costs M forward passes (batched into one call) -- more
    expensive per-update than novelty's single pass, so rate-limiting via
    ``interval`` matters more here on slow/power-constrained hardware. Between
    updates the last score is held and NO forward pass runs at all (no
    fallback pass needed, since this part never drives). Likewise, if the
    model has no calibration at all (``calibration_path`` missing/invalid),
    the M-pass batch is skipped entirely rather than computed and discarded --
    nothing consumes the raw variance without a calibration mapping, so there
    is no reason to pay for it.

    Run signature::

        stability, raw_variance, smoothed_variance = part.run(img_arr)

    ``stability`` is a 0-100 % (high = robust), or ``None`` if the model has no
    calibration, or a calibration made before TTA stats existed.

    :param pilot:            a loaded KerasPilot (KerasLinear); its underlying
                             Keras model is reused directly.
    :param calibration_path: path to a ``<model>.calib.json``. Optional.
    :param num_samples:      M, number of augmented copies per frame (~8).
    :param alpha:            EMA smoothing factor in [0, 1] for the variance.
    :param strength:         photometric augmentation strength (see
                             ``photometric_batch``).
    :param interval:         minimum seconds between updates (each an M-pass
                             batch). 0 (the default) updates every frame.
    :param seed:             optional RNG seed for reproducible augmentations.
    :param always_measure:   when True, run the M-pass batch even without a
                             calibration. Live driving leaves this False (an
                             uncalibrated variance has nothing to be scored
                             against, so paying M passes for it is waste);
                             ``mc_calibrate`` sets it True, since measuring
                             those variances is precisely how the calibration
                             gets built in the first place.
    """

    def __init__(self, pilot, calibration_path=None, num_samples=8,
                 alpha=0.2, strength=0.2, interval=0.0, seed=None,
                 always_measure=False):
        self.num_samples = int(num_samples)
        self.alpha = float(alpha)
        self.strength = float(strength)
        self.rng = np.random.default_rng(seed)
        self.smoothed_variance = None
        self.raw_variance = 0.0
        self.always_measure = bool(always_measure)

        # Minimum seconds between M-pass updates. 0 = every frame. Held
        # frames cost nothing (no forward pass at all) -- this part never
        # drives, unlike MCDropoutConfidence's interval fallback.
        self.interval = float(interval)
        self.last_update_time = None

        interpreter = getattr(pilot, 'interpreter', None)
        self.model = getattr(interpreter, 'model', None)
        if self.model is None or not callable(self.model):
            raise ValueError(
                'TTAStabilityDetector requires a Keras pilot with a callable '
                'model (the default KerasInterpreter). TFLite/TensorRT '
                'interpreters are not supported.')
        self.input_keys = list(interpreter.input_keys)
        if len(self.input_keys) > 1:
            logger.warning(
                'TTAStabilityDetector: model has multiple inputs %s; TTA '
                'supports single-image-input (linear) models only. Using the '
                'first input, others left unset may error.', self.input_keys)

        self.calibration = None
        if calibration_path:
            try:
                from donkeycar.parts.mc_calibrate import load_calibration
                calib = load_calibration(calibration_path)
                self.calibration = calib.get('tta')
                if self.calibration is None:
                    logger.warning(
                        f'TTAStabilityDetector: {calibration_path} has no '
                        f'"tta" stats (calibration made before TTA, or with '
                        f'XAI_TTA_ENABLED off); stability will be unavailable '
                        f'-- re-run mc_calibrate with XAI_TTA_ENABLED=True.')
                else:
                    logger.info(f'TTAStabilityDetector: loaded TTA calibration '
                                f'from {calibration_path}')
            except Exception as e:
                logger.warning(f'TTAStabilityDetector: could not load '
                               f'calibration {calibration_path} ({e}); '
                               f'stability will be unavailable.')

    def run(self, img_arr, now=None):
        if img_arr is None:
            return self._score(), 0.0, (self.smoothed_variance or 0.0)

        # `now` lets a tub replay (mc_calibrate) drive the interval-throttle
        # off recorded timestamps instead of wall-clock time -- see
        # MCDropoutConfidence.run() for the full rationale.
        now = now if now is not None else time.time()
        if (self.interval > 0 and self.last_update_time is not None
                and (now - self.last_update_time) < self.interval):
            # Rate-limited: skip the M-pass batch entirely and hold the last
            # values -- no fallback pass needed since this part never drives.
            return self._score(), self.raw_variance, \
                (self.smoothed_variance or 0.0)
        self.last_update_time = now

        if self.calibration is not None or self.always_measure:
            norm = normalize_image(img_arr).astype(np.float32)
            batch = photometric_batch(norm, self.num_samples, self.strength,
                                      self.rng)
            input_dict = {self.input_keys[0]: tf.convert_to_tensor(batch)}
            outputs = self.model(input_dict, training=False)  # DETERMINISTIC
            # Linear model returns [angle (M,1), throttle (M,1)].
            angle_samples = np.asarray(outputs[0]).reshape(-1)
            raw_variance = float(np.var(angle_samples))
        else:
            # No calibration to score against, and not explicitly asked to
            # measure anyway -- skip the M-pass batch entirely (mirrors
            # FeatureNoveltyDetector). Nothing consumes the raw variance
            # without a calibration mapping, so there's no reason to pay for
            # M forward passes just to produce a number nobody reads.
            # NOTE: calibration itself MUST pass always_measure=True, or the
            # variances it collects here would all be 0.0 and the resulting
            # 'tta' block would be degenerate.
            raw_variance = 0.0
        self.raw_variance = raw_variance

        if self.smoothed_variance is None:
            self.smoothed_variance = raw_variance
        else:
            self.smoothed_variance = (
                self.alpha * raw_variance
                + (1.0 - self.alpha) * self.smoothed_variance)

        return self._score(), raw_variance, self.smoothed_variance

    def _score(self):
        if self.calibration is None or self.smoothed_variance is None:
            return None
        from donkeycar.parts.mc_calibrate import tta_variance_to_stability
        return tta_variance_to_stability(self.smoothed_variance,
                                         self.calibration)

    def shutdown(self):
        pass
