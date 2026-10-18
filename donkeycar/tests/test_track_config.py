"""
Tests for the track description.

Validation is strict on purpose: a silently wrong lane width is a car in the
wall, so every rejection below must name the field that caused it.
"""

import pytest

from donkeycar.parts.track_config import (
    CvTrack,
    TrackConfig,
    TrackConfigError,
    default_track,
    find_track_file,
    load_track,
    parse_track,
)

# The `cv_control:` section of a track file. Most rules live there, so most tests
# build one of these and wrap it with `cv()`.
GOOD = {
    "continuous": True,
    "lap_length_inches": 480.0,
    "centerline": {"tape_color": "yellow", "width_inches": 1.0, "dashed": True},
    "side_lines": {"tape_color": "white", "left_inches": 18.0, "right_inches": 18.0},
    "lanes": {"left": -9.0, "right": 9.0},
}

MINIMAL = {"continuous": False, "lanes": {"left": -12.0, "right": 12.0}}


def cv(section, **top_level):
    """Parse a whole track file holding this cv_control section, and return the section."""
    return parse_track({"cv_control": section, **top_level}).cv_control


def write(tmp_path, text):
    path = tmp_path / "track.yml"
    path.write_text(text)
    return str(path)


# ------------------------------------------------------------------ happy path


def test_parses_a_complete_track():
    track = cv(dict(GOOD))
    assert track.continuous is True
    assert track.lap_length_inches == 480.0
    assert track.centerline.dashed is True
    assert track.side_lines is not None
    assert track.side_lines.left_inches == 18.0
    assert track.lane_names() == ["center", "left", "right"]


def test_optional_fields_have_sensible_defaults():
    track = cv(dict(MINIMAL))
    assert track.lap_length_inches is None
    assert track.centerline.tape_color == "yellow"
    assert track.centerline.width_inches == 1.0
    assert track.centerline.dashed is False
    assert track.side_lines is None


def test_side_lines_may_give_only_one_side():
    raw = dict(MINIMAL, side_lines={"right_inches": 20.0})
    track = cv(raw)
    assert track.side_lines is not None
    assert track.side_lines.left_inches is None
    assert track.side_lines.right_inches == 20.0


def test_shipped_example_track_is_valid():
    """The file `donkey createcar` copies must itself parse."""
    import donkeycar

    example = f"{donkeycar.__path__[0]}/templates/track.yml"
    track = load_track(example)
    assert track.cv_control.lane_names() == ["center", "left", "right"]
    assert track.cv_control.centerline.tape_color == "yellow"


def test_round_trips_through_the_tool_shape():
    payload = parse_track({"name": "Test track", "cv_control": dict(GOOD)}).to_dict()
    assert payload["name"] == "Test track"
    section = payload["cv_control"]
    assert section["lanes"]["right"] == 9.0
    assert section["continuous"] is True
    assert section["lap_length_inches"] == 480.0
    assert section["centerline"] == {"tape_color": "yellow", "width_inches": 1.0, "dashed": True}
    assert section["side_lines"]["tape_color"] == "white"
    assert section["side_lines"]["left_inches"] == 18.0


def test_tool_shape_keeps_cv_fields_in_their_section():
    """Only the track's own name and description sit beside the sections."""
    payload = parse_track({"cv_control": dict(GOOD)}).to_dict()
    assert set(payload) == {"name", "description", "nominal", "note", "cv_control"}


def test_tool_shape_says_the_values_are_nominal():
    """The agent must not read a single measured width as true along the whole track."""
    payload = parse_track({"cv_control": dict(MINIMAL)}).to_dict()
    assert payload["nominal"] is True
    assert "measure_ground_point" in payload["note"]
    assert "tape_color is only a label" in payload["note"]
    assert payload["cv_control"]["side_lines"] is None


def test_tool_shape_has_no_segment_fields():
    payload = parse_track({"cv_control": dict(GOOD)}).to_dict()
    assert not any("segment" in key or "cross" in key for key in [*payload, *payload["cv_control"]])


# ------------------------------------------------------------------- schema


@pytest.mark.parametrize("where", ["top level", "cv_control"])
def test_no_traffic_feature_list_is_accepted(where):
    """
    Features are discovered visually. An unknown section is an error rather
    than a silently ignored one, so a file that tries to list them fails loudly.
    """
    features = [{"kind": "stop_sign"}]
    with pytest.raises(TrackConfigError, match="unknown field"):
        if where == "top level":
            parse_track({"cv_control": dict(GOOD), "features": features})
        else:
            cv(dict(GOOD, features=features))


def test_cv_control_section_is_required():
    with pytest.raises(TrackConfigError) as exc:
        parse_track({"name": "Bare"})
    assert "cv_control" in str(exc.value)


def test_a_misspelt_section_is_unknown_not_empty():
    """`cv_contrl:` must not read as "no track"."""
    with pytest.raises(TrackConfigError) as exc:
        parse_track({"cv_contrl": dict(GOOD)})
    assert "cv_contrl" in str(exc.value)
    assert "unknown field" in str(exc.value)


@pytest.mark.parametrize("key", ["continuous", "lanes", "lap_length_inches", "centerline", "side_lines"])
def test_cv_fields_at_the_top_level_are_told_to_move(key):
    """A file in the shape before sections must say where each field now belongs."""
    raw = {"cv_control": dict(GOOD), key: GOOD[key]}
    with pytest.raises(TrackConfigError) as exc:
        parse_track(raw)
    message = str(exc.value)
    assert key in message
    assert "belong under 'cv_control:'" in message


def test_an_unsectioned_file_fails_to_load(tmp_path):
    path = write(tmp_path, "name: Old\ncontinuous: false\nlanes: {left: -12, right: 12}\n")
    with pytest.raises(TrackConfigError) as exc:
        load_track(path)
    assert "continuous" in str(exc.value)
    assert "lanes" in str(exc.value)
    assert "cv_control" in str(exc.value)


def test_section_must_be_a_mapping():
    with pytest.raises(TrackConfigError, match="mapping"):
        parse_track({"cv_control": "yes"})


def test_typo_in_a_field_name_is_rejected():
    raw = dict(GOOD)
    raw["lap_lenght_inches"] = raw.pop("lap_length_inches")
    with pytest.raises(TrackConfigError) as exc:
        cv(raw)
    assert "lap_lenght_inches" in str(exc.value)


@pytest.mark.parametrize(
    "key",
    [
        "segment_length_inches",
        "cross_length_inches",
        "segment_count",
        "cross_colors",
        "tape_width_inches",
        "tape_color",
    ],
)
@pytest.mark.parametrize("where", ["top level", "cv_control"])
def test_retired_segment_fields_are_refused_by_name(key, where):
    """An upgraded car's old track.yml must say exactly what to delete, wherever it sits."""
    with pytest.raises(TrackConfigError) as exc:
        if where == "top level":
            parse_track({"cv_control": dict(MINIMAL), key: 36.0})
        else:
            cv(dict(MINIMAL, **{key: 36.0}))
    message = str(exc.value)
    assert key in message
    assert "no longer used" in message


def test_an_old_segment_file_fails_to_load(tmp_path):
    path = write(
        tmp_path,
        "segment_length_inches: 36\ncross_length_inches: 12\ncontinuous: false\nlanes: {left: -12, right: 12}\n",
    )
    with pytest.raises(TrackConfigError) as exc:
        load_track(path)
    assert "cross_length_inches" in str(exc.value)
    assert "segment_length_inches" in str(exc.value)


@pytest.mark.parametrize("missing", ["continuous", "lanes"])
def test_missing_required_field_names_it(missing):
    raw = dict(GOOD)
    del raw[missing]
    with pytest.raises(TrackConfigError) as exc:
        cv(raw)
    assert missing in str(exc.value)


def test_non_positive_lap_length_is_rejected():
    raw = dict(GOOD, lap_length_inches=-5.0)
    with pytest.raises(TrackConfigError) as exc:
        cv(raw)
    assert "lap_length_inches" in str(exc.value)
    assert "positive" in str(exc.value)


def test_non_numeric_lap_length_is_rejected():
    raw = dict(GOOD, lap_length_inches="forty feet")
    with pytest.raises(TrackConfigError, match="lap_length_inches"):
        cv(raw)


@pytest.mark.parametrize(
    ("block", "value", "field"),
    [
        ("centerline", {"width_inches": 0}, "width_inches"),
        ("centerline", {"dashed": "sometimes"}, "dashed"),
        ("centerline", {"colour": "yellow"}, "colour"),
        ("centerline", {"color": "yellow"}, "tape_color"),
        ("side_lines", {"color": "white"}, "tape_color"),
        ("side_lines", {"left_inches": -18}, "left_inches"),
        ("side_lines", {"right_inches": "wide"}, "right_inches"),
        ("side_lines", {"middle_inches": 4}, "middle_inches"),
    ],
)
def test_bad_centerline_and_side_line_fields_are_named(block, value, field):
    raw = dict(MINIMAL)
    raw[block] = value
    with pytest.raises(TrackConfigError) as exc:
        cv(raw)
    assert block in str(exc.value)
    assert field in str(exc.value)


@pytest.mark.parametrize("block", ["centerline", "side_lines"])
def test_blocks_must_be_mappings(block):
    raw = dict(MINIMAL)
    raw[block] = "yellow"
    with pytest.raises(TrackConfigError, match="mapping"):
        cv(raw)


def test_continuous_must_be_a_boolean():
    raw = dict(GOOD)
    raw["continuous"] = "yes"
    with pytest.raises(TrackConfigError, match="continuous"):
        cv(raw)


# -------------------------------------------------------------------- lanes


def test_lanes_cannot_be_empty():
    raw = dict(GOOD)
    raw["lanes"] = {}
    with pytest.raises(TrackConfigError, match="at least one lane"):
        cv(raw)


def test_lane_offset_must_be_a_number():
    raw = dict(GOOD)
    raw["lanes"] = {"left": "twelve", "right": 12}
    with pytest.raises(TrackConfigError) as exc:
        cv(raw)
    assert "left" in str(exc.value)


def test_duplicate_lane_names_are_rejected():
    """YAML cannot repeat a key, but a case difference reads as a duplicate."""
    raw = dict(GOOD)
    raw["lanes"] = {"Left": -12.0, "left": -6.0, "right": 12.0}
    with pytest.raises(TrackConfigError, match="duplicate lane"):
        cv(raw)


@pytest.mark.parametrize("absent", ["left", "right"])
def test_left_and_right_lanes_are_required(absent):
    """Every track must answer the same three high-level lane commands."""
    lanes = {"left": -12.0, "right": 12.0}
    del lanes[absent]
    with pytest.raises(TrackConfigError) as exc:
        cv(dict(MINIMAL, lanes=lanes))
    assert absent in str(exc.value)
    assert "missing" in str(exc.value)


@pytest.mark.parametrize(
    ("lanes", "named"),
    [
        ({"left": 12.0, "right": 12.0}, "left"),
        ({"left": 0.0, "right": 12.0}, "left"),
        ({"left": -12.0, "right": -12.0}, "right"),
    ],
)
def test_lane_signs_are_checked(lanes, named):
    """Backwards signs put the car on the wrong side of the track."""
    with pytest.raises(TrackConfigError) as exc:
        cv(dict(MINIMAL, lanes=lanes))
    assert f"'{named}'" in str(exc.value)


def test_tape_color_is_accepted_in_both_blocks():
    track = cv(dict(MINIMAL, centerline={"tape_color": "orange"}, side_lines={"tape_color": "blue"}))
    assert track.centerline.tape_color == "orange"
    assert track.side_lines is not None
    assert track.side_lines.tape_color == "blue"


def test_center_is_always_the_centreline_without_being_configured():
    track = cv(dict(MINIMAL))
    assert track.offset_inches("center") == 0.0
    assert track.lane_names() == ["center", "left", "right"]


@pytest.mark.parametrize("name", ["center", "Center"])
@pytest.mark.parametrize("offset", [0, 0.0, 2.0])
def test_configuring_center_is_refused(name, offset):
    """Center is the centreline by definition; configuring it, even at 0, is an error."""
    with pytest.raises(TrackConfigError) as exc:
        cv(dict(MINIMAL, lanes={"left": -12.0, name: offset, "right": 12.0}))
    assert "'center'" in str(exc.value)
    assert "remove it" in str(exc.value)


def test_further_named_lanes_are_allowed():
    lanes = {"left": -12.0, "right": 12.0, "wide_right": 18.0}
    track = cv(dict(MINIMAL, lanes=lanes))
    assert track.offset_inches("wide_right") == 18.0


def test_unknown_lane_lookup_lists_the_real_ones():
    track = cv(dict(GOOD))
    with pytest.raises(TrackConfigError) as exc:
        track.offset_inches("shoulder")
    message = str(exc.value)
    assert "shoulder" in message
    assert "center" in message and "left" in message and "right" in message


def test_known_lane_lookup():
    track = cv(dict(GOOD))
    assert track.offset_inches("right") == 9.0
    assert track.offset_inches("center") == 0.0


# --------------------------------------------------------------- file layer


def test_loads_from_a_file(tmp_path):
    path = write(
        tmp_path,
        """
name: Kitchen loop
cv_control:
  continuous: true
  lap_length_inches: 480
  centerline:
    dashed: true
  side_lines:
    tape_color: white
    left_inches: 18
    right_inches: 18
  lanes:
    left: -9
    right: 9
    wide_right: 18
""",
    )
    track = load_track(path)
    assert track.name == "Kitchen loop"
    assert track.cv_control.continuous is True
    assert track.cv_control.centerline.dashed is True
    assert track.cv_control.offset_inches("wide_right") == 18.0


def test_swapping_the_file_changes_the_description(tmp_path):
    """A different track must need no code change."""
    lanes = "  lanes: {left: -12, right: 12}\n"
    first = load_track(write(tmp_path, "cv_control:\n  continuous: false\n" + lanes)).cv_control
    second = load_track(
        write(tmp_path, "cv_control:\n  continuous: true\n  lap_length_inches: 300\n" + lanes)
    ).cv_control
    assert first.continuous is False
    assert first.lap_length_inches is None
    assert second.continuous is True
    assert second.lap_length_inches == 300.0


def test_malformed_yaml_is_reported_with_the_path(tmp_path):
    path = write(tmp_path, "lanes: [unclosed\n")
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
    assert isinstance(track.cv_control, CvTrack)
    assert track.cv_control.offset_inches("center") == 0.0
