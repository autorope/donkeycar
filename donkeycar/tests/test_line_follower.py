"""Tests for the optional ROI-crop and mask-denoising controls on LineFollower.

Both controls default to a no-op, so the first test also pins that a config
without the new keys keeps the classic single-band behavior.
"""
from types import SimpleNamespace

import numpy as np
import pytest
from simple_pid import PID

from donkeycar.parts.line_follower import LineFollower

YELLOW = (255, 255, 0)  # RGB; the part converts with COLOR_RGB2HSV


def make_cfg(**overrides):
    """A minimal cfg with the keys LineFollower reads. New keys are omitted on
    purpose so getattr() defaults are exercised unless a test opts in."""
    cfg = SimpleNamespace(
        OVERLAY_IMAGE=False,
        SCAN_Y=0,
        SCAN_HEIGHT=240,
        COLOR_THRESHOLD_LOW=(0, 50, 50),
        COLOR_THRESHOLD_HIGH=(50, 255, 255),
        TARGET_PIXEL=None,
        TARGET_THRESHOLD=10,
        CONFIDENCE_THRESHOLD=0.001,
        THROTTLE_INITIAL=0.15,
        THROTTLE_STEP=0.05,
        THROTTLE_MAX=0.3,
        THROTTLE_MIN=0.15,
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def follower(**overrides):
    return LineFollower(PID(Kp=-0.01, Ki=0.0, Kd=-0.0001), make_cfg(**overrides))


def blank(height=240, width=320):
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_default_config_detects_line_and_is_backward_compatible():
    # cfg has no CROP_TOP_FRACTION / MASK_MORPH_KERNEL -> getattr defaults apply.
    image = blank()
    image[150:180, 196:205, :] = YELLOW  # stripe near column 200
    index, confidence, _mask = follower().get_i_color(image)
    assert 195 <= index <= 205
    assert confidence > 0


def test_crop_excludes_stronger_upper_clutter():
    image = blank()
    image[0:100, 48:53, :] = YELLOW      # tall clutter high in the frame (col ~50)
    image[150:180, 196:205, :] = YELLOW  # shorter real line low in the frame (col ~200)

    # Without a crop, the taller clutter wins the histogram.
    index_off, _c, _m = follower().get_i_color(image)
    assert 45 <= index_off <= 55

    # A crop at half height zeroes the clutter rows, so the real line wins.
    index_on, _c, _m = follower(CROP_TOP_FRACTION=0.5).get_i_color(image)
    assert 195 <= index_on <= 205


def test_morphology_removes_isolated_speckle_but_keeps_the_line():
    image = blank()
    image[150:180, 196:205, :] = YELLOW  # solid line
    image[10, 10, :] = YELLOW            # one isolated speckle pixel

    _i, _c, mask_off = follower().get_i_color(image)
    _i, _c, mask_on = follower(MASK_MORPH_KERNEL=5).get_i_color(image)

    assert mask_off[10, 10] > 0              # speckle present without denoising
    assert mask_on[10, 10] == 0              # open() removes the lone pixel
    assert mask_on[150:180, 196:205].sum() > 0  # the line survives


def test_none_image_returns_safe_zero_command():
    steering, throttle, *_rest = follower().run(None)
    assert steering == 0
    assert throttle == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
