"""
Tests for `donkey calibrate-color`.

Scenes are synthesised, so the whole pipeline -- sampling, clustering,
proposing, evaluating -- runs with no camera and no saved frames.
"""

import cv2
import numpy as np
import pytest

from donkeycar.management.calibrate_color import (
    ColorStats,
    Threshold,
    auto_region,
    auto_region_all,
    detect_overlay_rows,
    dominant_hue_cluster,
    evaluate,
    load_frames,
    measure,
    parse_region,
    propose,
    region_pixels,
    to_hsv,
)

W, H = 320, 240
TAPE_RGB = (230, 200, 30)  # a yellow close to real tape
CONE_RGB = (235, 90, 20)  # orange, the thing that widened the window


def scene(tape_col=150, tape_w=30, cone=False, overlay_rows=None, dark=False):
    """A carpet-ish background with a vertical tape stripe, in BGR like cv2.imread."""
    rng = np.random.default_rng(0)
    img = rng.integers(40, 70, size=(H, W, 3), dtype=np.uint8)  # dull grey carpet
    if not dark:
        img[:, tape_col - tape_w // 2 : tape_col + tape_w // 2] = TAPE_RGB[::-1]
    if cone:
        img[120:200, 20:50] = CONE_RGB[::-1]
    if overlay_rows:
        top, bottom = overlay_rows
        # the real overlay writes a pure black/white mask into those rows
        band = rng.integers(0, 2, size=(bottom - top + 1, W), dtype=np.uint8) * 255
        img[top : bottom + 1] = np.stack([band] * 3, axis=-1)
    return img


# ---------------------------------------------------------------- conversion


def test_hsv_conversion_matches_the_follower():
    """
    LineFollower is handed RGB and converts with RGB2HSV. Reading a file gives
    BGR, so skipping the BGR->RGB step puts every hue in the wrong place.
    """
    bgr = scene()
    hsv = to_hsv(bgr)
    tape = hsv[120, 150]
    expected = cv2.cvtColor(np.uint8([[TAPE_RGB]]), cv2.COLOR_RGB2HSV)[0][0]
    assert abs(int(tape[0]) - int(expected[0])) <= 2


# ------------------------------------------------------------------ overlay


def test_detects_a_burned_in_overlay_band():
    assert detect_overlay_rows(scene(overlay_rows=(100, 119))) == (100, 119)


def test_no_overlay_in_a_clean_frame():
    assert detect_overlay_rows(scene()) is None


def test_overlay_rows_are_excluded_from_sampling():
    """Those rows are the follower's own mask; measuring them measures itself."""
    bgr = scene(overlay_rows=(100, 119))
    pixels = auto_region(to_hsv(bgr), skip_rows=(100, 119))
    assert pixels.size > 0  # tape is still found below the band


# ------------------------------------------------------------------ sampling


def test_finds_the_tape_without_being_told_where():
    pixels = auto_region(to_hsv(scene()))
    assert pixels.size > 0
    assert 20 <= int(np.median(pixels[:, 0])) <= 35


def test_region_sampling():
    pixels = region_pixels(to_hsv(scene(tape_col=150)), (140, 150, 20, 40))
    assert pixels.shape[0] == 20 * 40


def test_dominant_cluster_rejects_a_second_colour():
    """
    A cone is saturated and bright too. Without clustering it drags the hue
    floor down until the window admits everything -- which is the bug this
    command exists to fix.
    """
    hsv = to_hsv(scene(cone=True))
    strong = auto_region(hsv)
    assert int(np.percentile(strong[:, 0], 1)) < 15, "expected the cone to widen the raw sample"

    clustered = dominant_hue_cluster(strong)
    assert int(np.percentile(clustered[:, 0], 1)) >= 15, "clustering should drop the cone"


def test_clustering_is_global_not_per_frame():
    """
    Clustering each frame and then pooling re-widens the window: a frame whose
    dominant colour is a cone contributes its own cluster.
    """
    frames = [("tape.jpg", scene()), ("cones.jpg", scene(tape_col=150, cone=True))]
    pixels, contributors = auto_region_all(frames)
    assert len(contributors) == 2
    assert int(np.percentile(pixels[:, 0], 1)) >= 15


def test_frames_without_tape_are_reported_not_fatal():
    frames = [("dark.jpg", scene(dark=True)), ("good.jpg", scene())]
    pixels, contributors = auto_region_all(frames)
    assert contributors == ["good.jpg"]
    assert pixels.size > 0


def test_no_tape_anywhere_returns_nothing():
    pixels, contributors = auto_region_all([("dark.jpg", scene(dark=True))])
    assert contributors == []
    assert pixels.size == 0


# ------------------------------------------------------------------ proposing


def test_measure_rejects_an_empty_sample():
    with pytest.raises(ValueError, match="No pixels to measure"):
        measure(np.empty((0, 3), dtype=np.uint8))


def test_proposed_window_brackets_the_measured_colour():
    stats = measure(dominant_hue_cluster(auto_region(to_hsv(scene()))))
    threshold = propose(stats)
    assert threshold.low[0] <= stats.h_lo
    assert threshold.high[0] >= stats.h_hi
    # the S/V floors sit below the dimmest tape seen, with a little slack
    assert threshold.low[1] < stats.s_lo
    assert threshold.low[2] < stats.v_lo
    assert threshold.high[1] == 255 and threshold.high[2] == 255


def test_hue_margin_is_adjustable():
    stats = ColorStats(pixels=100, h_lo=25, h_mid=27, h_hi=29, s_lo=200, s_mid=250, v_lo=200, v_mid=220)
    assert propose(stats, hue_margin=5).low[0] == 20
    assert propose(stats, hue_margin=15).low[0] == 10


def test_hue_stays_inside_opencvs_range():
    """OpenCV hue is 0-179; a margin must not push the window outside it."""
    stats = ColorStats(pixels=10, h_lo=2, h_mid=3, h_hi=178, s_lo=200, s_mid=250, v_lo=200, v_mid=220)
    threshold = propose(stats, hue_margin=20)
    assert threshold.low[0] == 0
    assert threshold.high[0] == 179


def test_config_lines_are_pasteable():
    text = Threshold(low=(18, 100, 100), high=(35, 255, 255)).as_config()
    assert "COLOR_THRESHOLD_LOW  = (18, 100, 100)" in text
    assert "COLOR_THRESHOLD_HIGH = (35, 255, 255)" in text


# ----------------------------------------------------------------- evaluating


def test_a_good_threshold_locks_onto_the_tape():
    hsv = to_hsv(scene(tape_col=150))
    threshold = propose(measure(dominant_hue_cluster(auto_region(hsv))))
    result = evaluate(hsv, threshold, scan_y=120, scan_height=40, name="t")
    assert result.matched
    # A perfectly uniform synthetic stripe gives a flat histogram, and argmax
    # returns the first maximum -- the left edge. What matters is that the peak
    # lands on the tape, not exactly at its centre.
    assert 135 <= result.peak_col <= 165, result.peak_col
    assert result.concentration > 60


def test_a_loose_threshold_scatters():
    """
    Coverage alone says nothing. The stock window matches far more of the frame
    but spreads it, which is how the histogram peak ends up on a person.
    """
    hsv = to_hsv(scene(tape_col=150, cone=True))
    loose = Threshold(low=(0, 50, 50), high=(50, 255, 255))
    tight = propose(measure(dominant_hue_cluster(auto_region(hsv))))
    a = evaluate(hsv, loose, scan_y=120, scan_height=60, name="loose")
    b = evaluate(hsv, tight, scan_y=120, scan_height=60, name="tight")
    assert a.coverage > b.coverage
    assert b.concentration > a.concentration


def test_no_tape_is_reported_rather_than_a_made_up_peak():
    hsv = to_hsv(scene(dark=True))
    threshold = Threshold(low=(18, 100, 100), high=(35, 255, 255))
    result = evaluate(hsv, threshold, scan_y=120, scan_height=40, name="dark")
    assert result.status == "no-tape"
    assert result.peak_col is None


def test_an_occluded_band_is_distinguished_from_absent_tape():
    """
    Blaming the threshold for a scan band that is entirely under the overlay
    would send someone tuning the wrong thing.
    """
    bgr = scene(overlay_rows=(100, 139))
    result = evaluate(
        to_hsv(bgr),
        Threshold((18, 100, 100), (35, 255, 255)),
        scan_y=100,
        scan_height=40,
        name="covered",
        skip_rows=(100, 139),
    )
    assert result.status == "occluded"
    assert "cannot evaluate" in result.describe()


# ----------------------------------------------------------------- arguments


@pytest.mark.parametrize("text", ["1,2,3", "a,b,c,d", "1,2,0,4", "1,2,3,-1", ""])
def test_bad_regions_are_rejected(text):
    with pytest.raises(ValueError):
        parse_region(text)


def test_good_region_parses():
    assert parse_region("10,20,30,40") == (10, 20, 30, 40)


def test_missing_images_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="No readable images"):
        load_frames(str(tmp_path / "*.jpg"))


def test_loads_frames(tmp_path):
    cv2.imwrite(str(tmp_path / "a.jpg"), scene())
    cv2.imwrite(str(tmp_path / "b.jpg"), scene())
    frames = load_frames(str(tmp_path / "*.jpg"))
    assert [n for n, _ in frames] == ["a.jpg", "b.jpg"]


def test_registered_as_a_donkey_command():
    from donkeycar.management.base import CalibrateColor

    assert hasattr(CalibrateColor, "run")
