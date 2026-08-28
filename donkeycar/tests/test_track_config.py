"""
Tests for the track description.

Validation is strict on purpose: a silently wrong lane width is a car in the
wall, so every rejection below must name the field that caused it.
"""

import pytest

from donkeycar.parts.track_config import (
    TrackConfig,
    TrackConfigError,
    default_track,
    find_track_file,
    load_track,
    parse_track,
)

GOOD = {
    "name": "Test track",
    "segment_length_inches": 36.0,
    "cross_length_inches": 12.0,
    "tape_width_inches": 1.0,
    "segment_count": 8,
    "continuous": True,
    "lanes": {"left": -12.0, "center": 0.0, "right": 12.0},
}


def write(tmp_path, text):
    path = tmp_path / "track.yml"
    path.write_text(text)
    return str(path)


# ------------------------------------------------------------------ happy path


def test_parses_a_complete_track():
    track = parse_track(dict(GOOD))
    assert track.segment_length_inches == 36.0
    assert track.cross_length_inches == 12.0
    assert track.segment_count == 8
    assert track.continuous is True
    assert track.lane_names() == ["center", "left", "right"]


def test_optional_fields_have_sensible_defaults():
    minimal = {
        "segment_length_inches": 36.0,
        "cross_length_inches": 12.0,
        "continuous": False,
        "lanes": {"center": 0.0},
    }
    track = parse_track(minimal)
    assert track.tape_width_inches == 1.0
    assert track.tape_color == "yellow"
    assert track.cross_colors == ["red", "blue"]
    assert track.segment_count is None


def test_shipped_example_track_is_valid():
    """The file `donkey createcar` copies must itself parse."""
    import donkeycar

    example = f"{donkeycar.__path__[0]}/templates/track.yml"
    track = load_track(example)
    assert track.lane_names() == ["center", "left", "right"]


def test_round_trips_through_the_tool_shape():
    track = parse_track(dict(GOOD))
    payload = track.to_dict()
    assert payload["segment_length_inches"] == 36.0
    assert payload["lanes"]["right"] == 12.0
    assert payload["continuous"] is True


# ------------------------------------------------------------------- schema


def test_no_traffic_feature_list_is_accepted():
    """
    Features are discovered visually. An unknown section is an error rather
    than a silently ignored one, so a file that tries to list them fails loudly.
    """
    raw = dict(GOOD)
    raw["features"] = [{"kind": "stop_sign", "segment": 2}]
    with pytest.raises(TrackConfigError, match="unknown field"):
        parse_track(raw)


def test_typo_in_a_field_name_is_rejected():
    raw = dict(GOOD)
    raw["segment_lenght_inches"] = raw.pop("segment_length_inches")
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    assert "segment_lenght_inches" in str(exc.value)


@pytest.mark.parametrize("missing", sorted(["segment_length_inches", "cross_length_inches", "continuous", "lanes"]))
def test_missing_required_field_names_it(missing):
    raw = dict(GOOD)
    del raw[missing]
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    assert missing in str(exc.value)


@pytest.mark.parametrize("key", ["segment_length_inches", "cross_length_inches", "tape_width_inches"])
def test_non_positive_lengths_are_rejected(key):
    raw = dict(GOOD)
    raw[key] = -5.0
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    assert key in str(exc.value)
    assert "positive" in str(exc.value)


@pytest.mark.parametrize("key", ["segment_length_inches", "cross_length_inches"])
def test_non_numeric_lengths_are_rejected(key):
    raw = dict(GOOD)
    raw[key] = "three feet"
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    assert key in str(exc.value)


def test_continuous_must_be_a_boolean():
    raw = dict(GOOD)
    raw["continuous"] = "yes"
    with pytest.raises(TrackConfigError, match="continuous"):
        parse_track(raw)


def test_segment_count_must_be_a_positive_whole_number():
    raw = dict(GOOD)
    raw["segment_count"] = 0
    with pytest.raises(TrackConfigError, match="segment_count"):
        parse_track(raw)
    raw["segment_count"] = 2.5
    with pytest.raises(TrackConfigError, match="segment_count"):
        parse_track(raw)


# -------------------------------------------------------------------- lanes


def test_lanes_cannot_be_empty():
    raw = dict(GOOD)
    raw["lanes"] = {}
    with pytest.raises(TrackConfigError, match="at least one lane"):
        parse_track(raw)


def test_lane_offset_must_be_a_number():
    raw = dict(GOOD)
    raw["lanes"] = {"left": "twelve"}
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    assert "left" in str(exc.value)


def test_duplicate_lane_names_are_rejected():
    """YAML cannot repeat a key, but a case difference reads as a duplicate."""
    raw = dict(GOOD)
    raw["lanes"] = {"Left": -12.0, "left": -6.0}
    with pytest.raises(TrackConfigError, match="duplicate lane"):
        parse_track(raw)


def test_unknown_lane_lookup_lists_the_real_ones():
    track = parse_track(dict(GOOD))
    with pytest.raises(TrackConfigError) as exc:
        track.offset_inches("shoulder")
    message = str(exc.value)
    assert "shoulder" in message
    assert "center" in message and "left" in message and "right" in message


def test_known_lane_lookup():
    track = parse_track(dict(GOOD))
    assert track.offset_inches("right") == 12.0
    assert track.offset_inches("center") == 0.0


# --------------------------------------------------------------- file layer


def test_loads_from_a_file(tmp_path):
    path = write(
        tmp_path,
        """
segment_length_inches: 36
cross_length_inches: 12
continuous: true
lanes:
  center: 0
  wide_right: 18
""",
    )
    track = load_track(path)
    assert track.continuous is True
    assert track.offset_inches("wide_right") == 18.0


def test_swapping_the_file_changes_the_description(tmp_path):
    """A different track must need no code change."""
    first = load_track(
        write(tmp_path, "segment_length_inches: 36\ncross_length_inches: 12\ncontinuous: false\nlanes: {center: 0}\n")
    )
    second = load_track(
        write(tmp_path, "segment_length_inches: 24\ncross_length_inches: 6\ncontinuous: true\nlanes: {center: 0}\n")
    )
    assert first.segment_length_inches == 36.0
    assert second.segment_length_inches == 24.0
    assert second.continuous is True


def test_malformed_yaml_is_reported_with_the_path(tmp_path):
    path = write(tmp_path, "segment_length_inches: [unclosed\n")
    with pytest.raises(TrackConfigError) as exc:
        load_track(path)
    assert path in str(exc.value)


def test_empty_file_is_rejected(tmp_path):
    with pytest.raises(TrackConfigError, match="empty"):
        load_track(write(tmp_path, "\n"))


def test_non_mapping_file_is_rejected(tmp_path):
    with pytest.raises(TrackConfigError, match="mapping"):
        load_track(write(tmp_path, "- just\n- a\n- list\n"))


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(TrackConfigError, match="Could not read"):
        load_track(str(tmp_path / "nope.yml"))


def test_find_track_file(tmp_path):
    assert find_track_file(None) is None
    assert find_track_file(str(tmp_path)) is None
    (tmp_path / "track.yml").write_text("x")
    assert find_track_file(str(tmp_path)) == str(tmp_path / "track.yml")


def test_default_track_is_usable():
    track = default_track()
    assert isinstance(track, TrackConfig)
    assert track.offset_inches("center") == 0.0
