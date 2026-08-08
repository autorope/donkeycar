"""
MC-Dropout confidence estimation for DonkeyCar.

This part wraps an already-loaded KerasLinear pilot and, on every drive-loop
iteration, runs the model N times with dropout left *active* (Monte-Carlo
Dropout). The spread of the N steering predictions is used as an uncertainty
signal:

  * ``mean_steering`` / ``mean_throttle`` -- the averaged prediction. This
    becomes the command sent to the car (same behaviour as a normal single
    pass, just averaged over the stochastic sub-networks).
  * ``raw_variance``   -- variance of the N steering outputs for this frame.
  * ``smoothed_variance`` -- exponential moving average of ``raw_variance``
    over time, to damp frame-to-frame flicker.

IMPORTANT (scope / caveats):
  * This is a *relative*, per-model uncertainty signal, NOT a formally
    calibrated Bayesian probability. Turning ``smoothed_variance`` into a
    human-readable "confidence %" requires the separate calibration step
    (percentile thresholds collected from a representative drive).
  * Only the default linear architecture (``KerasLinear`` /
    ``default_n_linear``) is supported in v1. That model contains Dropout
    layers and *no* BatchNormalization, which is why calling it with
    ``training=True`` cleanly re-enables dropout without side effects.
  * MC-Dropout needs the full Keras interpreter. The TFLite / TensorRT
    inference paths cannot keep dropout stochastic and are not supported.
"""
import logging
import time

import numpy as np
import tensorflow as tf

from donkeycar.utils import normalize_image

logger = logging.getLogger(__name__)


class MCDropoutConfidence:
    """
    DonkeyCar Part. Drop-in replacement for a KerasLinear inference part that
    additionally emits an uncertainty signal.

    Run signature::

        angle, throttle, confidence, raw_variance, smoothed_variance = \
            part.run(img_arr)

    ``confidence`` is a 0-100 %% derived from the calibration file, or None if
    the model has no calibration yet.

    :param pilot:       a loaded KerasPilot (KerasLinear). Its underlying Keras
                        model is reused directly -- we do not reload weights.
    :param num_passes:  number of stochastic forward passes (N). Wired to
                        ``cfg.XAI_CONFIDENCE_PASSES``.
    :param alpha:       EMA smoothing factor in [0, 1]. Higher = more
                        responsive, lower = smoother. Wired to
                        ``cfg.XAI_CONFIDENCE_ALPHA``.
    :param calibration_path: path to a ``<model>.calib.json`` produced by
                        ``donkeycar.parts.mc_calibrate``. Optional.
    """

    def __init__(self, pilot, num_passes=15, alpha=0.2, calibration_path=None,
                 interval=0.0):
        self.pilot = pilot
        self.num_passes = int(num_passes)
        self.alpha = float(alpha)
        self.smoothed_variance = None  # lazily initialised on first frame

        # Minimum seconds between stochastic (N-pass) uncertainty updates.
        # 0 = update every frame. Between updates, a cheap single
        # deterministic pass still produces a fresh steering command each
        # loop iteration; only the uncertainty numbers are held.
        # NOTE: the EMA alpha applies per *update*, so with a longer interval
        # the variance is smoothed over fewer, more spaced-out samples.
        self.interval = float(interval)
        self.last_mc_time = None
        self.raw_variance = 0.0

        # Optional calibration: maps smoothed variance -> displayed confidence %.
        # Without it, the part still emits variance but confidence is None.
        self.calibration = None
        if calibration_path:
            try:
                from donkeycar.parts.mc_calibrate import load_calibration
                self.calibration = load_calibration(calibration_path)
                logger.info(f'MCDropoutConfidence: loaded calibration from '
                            f'{calibration_path}')
            except Exception as e:
                logger.warning(f'MCDropoutConfidence: could not load '
                               f'calibration {calibration_path} ({e}); '
                               f'confidence %% will be unavailable.')

        # Reach the raw Keras model. The interpreter must be the plain Keras
        # one -- TFLite/TensorRT interpreters have no callable Keras model and
        # cannot keep dropout stochastic.
        interpreter = getattr(pilot, 'interpreter', None)
        self.model = getattr(interpreter, 'model', None)
        if self.model is None or not callable(self.model):
            raise ValueError(
                'MCDropoutConfidence requires a Keras pilot with a callable '
                'model (the default KerasInterpreter). TFLite/TensorRT '
                'interpreters are not supported.')
        self.input_keys = list(interpreter.input_keys)

        # Sanity check: warn loudly if the model has no dropout, because then
        # every "stochastic" pass is identical and the signal is meaningless.
        n_dropout = sum(1 for layer in self.model.layers
                        if 'dropout' in layer.__class__.__name__.lower())
        if n_dropout == 0:
            logger.warning(
                'MCDropoutConfidence: the loaded model has NO dropout layers. '
                'The uncertainty signal will be identically zero. Retrain '
                'with a dropout-bearing architecture (e.g. the default '
                'linear model).')
        else:
            logger.info(f'MCDropoutConfidence: found {n_dropout} dropout '
                        f'layer(s); running N={self.num_passes} stochastic '
                        f'passes per frame, EMA alpha={self.alpha}.')

    def _stochastic_forward(self, img_arr, other_arr):
        """
        Run N forward passes with dropout active, batched into a single call.

        We replicate the input N times along the batch axis and do ONE
        ``model(..., training=True)`` call. Keras samples an independent
        dropout mask per batch element, so the N rows of the output are N
        genuine Monte-Carlo samples -- far cheaper than an N-iteration Python
        loop (~5x faster for N=15 in local timing).

        :return: (angle_samples, throttle_samples) as 1-D np arrays of len N.
        """
        norm_img = normalize_image(img_arr).astype(np.float32)
        # Batch of N identical images: shape (N, H, W, C).
        img_batch = np.repeat(norm_img[np.newaxis, ...], self.num_passes, axis=0)

        values = [img_batch]
        for arr in other_arr:
            a = np.asarray(arr, dtype=np.float32)
            values.append(np.repeat(a[np.newaxis, ...], self.num_passes, axis=0))

        input_dict = {k: tf.convert_to_tensor(v)
                      for k, v in zip(self.input_keys, values)}

        outputs = self.model(input_dict, training=True)
        # Linear model returns a list [angle (N,1), throttle (N,1)].
        angle_samples = np.asarray(outputs[0]).reshape(-1)
        throttle_samples = np.asarray(outputs[1]).reshape(-1)
        return angle_samples, throttle_samples

    def _confidence(self):
        """Displayed confidence % from the smoothed variance, or None if the
        model is uncalibrated."""
        if self.calibration is None or self.smoothed_variance is None:
            return None
        from donkeycar.parts.mc_calibrate import variance_to_confidence
        return variance_to_confidence(self.smoothed_variance, self.calibration)

    def run(self, img_arr, *other_arr, now=None):
        if img_arr is None:
            # Nothing to predict on yet; emit a neutral default. Downstream
            # code treats None gracefully.
            return 0.0, 0.0, self._confidence(), 0.0, \
                (self.smoothed_variance or 0.0)

        # Rate limiting: between uncertainty updates, drive on a cheap single
        # deterministic pass and hold the last uncertainty values.
        # `now` lets a caller replaying a tub (mc_calibrate.calibrate_from_tub)
        # drive this off the tub's own recorded timestamps instead of
        # wall-clock time, so a replay reproduces the same update cadence
        # XAI_CONFIDENCE_INTERVAL actually produces while driving, rather than
        # sampling every frame regardless of how it's configured. None (the
        # default, and every other caller) uses the real clock as before.
        now = now if now is not None else time.time()
        if (self.interval > 0 and self.last_mc_time is not None
                and (now - self.last_mc_time) < self.interval):
            angle, throttle = self.pilot.run(img_arr, *other_arr)
            return (float(angle), float(throttle), self._confidence(),
                    self.raw_variance, (self.smoothed_variance or 0.0))
        self.last_mc_time = now

        angle_samples, throttle_samples = \
            self._stochastic_forward(img_arr, other_arr)

        mean_steering = float(np.mean(angle_samples))
        mean_throttle = float(np.mean(throttle_samples))
        raw_variance = float(np.var(angle_samples))
        self.raw_variance = raw_variance

        # Exponential moving average of the variance.
        if self.smoothed_variance is None:
            self.smoothed_variance = raw_variance
        else:
            self.smoothed_variance = (
                self.alpha * raw_variance
                + (1.0 - self.alpha) * self.smoothed_variance)

        return (mean_steering, mean_throttle, self._confidence(),
                raw_variance, self.smoothed_variance)

    def shutdown(self):
        pass


class ThrottleScaler:
    """
    Feature 2: scale the pilot throttle down as MC-Dropout confidence drops,
    feature-space novelty rises, and/or TTA stability drops. The philosophy is
    "hesitate, don't guess": this only ever reduces throttle magnitude and
    NEVER touches steering.

    Each signal has its own reduced/critical thresholds (confidence and TTA
    stability are "high is good" signals, novelty a "high is bad" one -- see
    ``donkeycar.parts.novelty`` / ``donkeycar.parts.tta`` for why the three are
    complementary, not redundant). On any frame, each available signal is
    converted to a scale in ``[min_scale, 1.0]`` independently, and the
    **lower** (most conservative) is applied -- so a problem flagged by any one
    signal alone is enough to ease off the throttle, matching the intent that
    any failure mode (model disagreement, an unfamiliar scene, or fragility to
    input noise) warrants caution. A signal that's unavailable (feature
    disabled upstream, or model uncalibrated) is simply excluded from the
    comparison -- enabling only one of the three still works, scaling on that
    signal alone.

    Per-signal tiers (mirrored across the three, thresholds configurable):
      * confidence/TTA >= its reduced_threshold, or novelty <= its
        reduced_threshold -> that signal contributes full scale (1.0).
      * between its reduced/critical thresholds -> that signal's scale is
        linearly interpolated between 1.0 and ``min_scale``.
      * confidence/TTA < its critical_threshold, or novelty > its
        critical_threshold -> that signal is "critical": contributes
        ``min_scale``, and if *any* signal has been continuously critical for
        ``stop_duration`` seconds, throttle is forced to zero (stop).

    Passthrough (no change to throttle) when:
      * throttle is None, or
      * all of confidence, novelty and tta_stability are None.

    Run signature::

        scaled_throttle = part.run(throttle, confidence, novelty, tta_stability)

    ``tta_stability`` is optional (defaults None) and, like confidence, is a
    "high is good" signal. Any signal that is None (feature off / uncalibrated)
    is excluded from the min-of-scales comparison rather than blocking it.

    Intended to be added with ``run_condition='run_pilot'`` so it only affects
    autopilot throttle, giving zero behaviour change to manual driving.
    """

    def __init__(self, confidence_reduced_threshold=65.0,
                 confidence_critical_threshold=25.0,
                 novelty_reduced_threshold=25.0,
                 novelty_critical_threshold=65.0,
                 tta_reduced_threshold=65.0,
                 tta_critical_threshold=25.0,
                 min_scale=0.4, stop_duration=1.0):
        self.confidence_reduced_threshold = float(confidence_reduced_threshold)
        self.confidence_critical_threshold = float(confidence_critical_threshold)
        self.novelty_reduced_threshold = float(novelty_reduced_threshold)
        self.novelty_critical_threshold = float(novelty_critical_threshold)
        self.tta_reduced_threshold = float(tta_reduced_threshold)
        self.tta_critical_threshold = float(tta_critical_threshold)
        self.min_scale = float(min_scale)
        self.stop_duration = float(stop_duration)
        self.critical_since = None   # timestamp critical tier began, else None
        self._warned_no_signal = False
        logger.info(f'ThrottleScaler: confidence reduced<'
                    f'{confidence_reduced_threshold}% critical<'
                    f'{confidence_critical_threshold}%, novelty reduced>'
                    f'{novelty_reduced_threshold}% critical>'
                    f'{novelty_critical_threshold}%, TTA-stability reduced<'
                    f'{tta_reduced_threshold}% critical<'
                    f'{tta_critical_threshold}%, min_scale={min_scale}, '
                    f'stop_after={stop_duration}s')

    def _signal_scale(self, value, reduced_threshold, critical_threshold,
                      ascending):
        """
        Convert one signal's raw value to (scale, is_critical). `ascending`
        selects the "high is bad" (novelty) direction vs "high is good"
        (confidence) direction. Returns (None, False) if value is None.
        """
        if value is None:
            return None, False
        if ascending:
            if value <= reduced_threshold:
                return 1.0, False
            if value <= critical_threshold:
                span = critical_threshold - reduced_threshold
                frac = (value - reduced_threshold) / span if span > 0 else 0.0
                return 1.0 - (1.0 - self.min_scale) * frac, False
            return self.min_scale, True
        else:
            if value >= reduced_threshold:
                return 1.0, False
            if value >= critical_threshold:
                span = reduced_threshold - critical_threshold
                frac = (value - critical_threshold) / span if span > 0 else 0.0
                return self.min_scale + (1.0 - self.min_scale) * frac, False
            return self.min_scale, True

    def run(self, throttle, confidence, novelty, tta_stability=None):
        if throttle is None:
            return throttle

        conf_scale, conf_critical = self._signal_scale(
            confidence, self.confidence_reduced_threshold,
            self.confidence_critical_threshold, ascending=False)
        nov_scale, nov_critical = self._signal_scale(
            novelty, self.novelty_reduced_threshold,
            self.novelty_critical_threshold, ascending=True)
        # TTA stability is a "high is good" signal, same direction as confidence.
        tta_scale, tta_critical = self._signal_scale(
            tta_stability, self.tta_reduced_threshold,
            self.tta_critical_threshold, ascending=False)

        scales = [s for s in (conf_scale, nov_scale, tta_scale)
                  if s is not None]
        if not scales:
            # No usable signal -> do not interfere with driving.
            if not self._warned_no_signal:
                logger.warning('ThrottleScaler: no signal available (is '
                               'XAI_CONFIDENCE_ENABLED/XAI_NOVELTY_ENABLED/'
                               'XAI_TTA_ENABLED on, and the model '
                               'calibrated?); throttle passed through '
                               'unchanged.')
                self._warned_no_signal = True
            self.critical_since = None
            return throttle

        scale = min(scales)
        any_critical = conf_critical or nov_critical or tta_critical

        if any_critical:
            now = time.time()
            if self.critical_since is None:
                self.critical_since = now
            if now - self.critical_since >= self.stop_duration:
                return 0.0
        else:
            self.critical_since = None

        return throttle * scale

    def shutdown(self):
        pass
