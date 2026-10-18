"""
The track description an agent reads before it starts driving.

Geometry only, and nominal. The track is a centreline, possibly dashed, with
optional side-lines, and its width and the centreline's position vary along the
course. These numbers are guidance for the agent, which can measure the real
values from the camera frame once the ground plane is calibrated.

Traffic features -- stop signs, addresses, obstacles -- are deliberately
absent: the agent discovers those in the camera frame, which is what the
learning progression is about, and it means a track can be rearranged or have
features moved around it without editing this file.

The schema is validated strictly and unknown keys are rejected. A silently
wrong lane width is a car in the wall, and a typo that reads as "no lanes
configured" is worse than a refusal to start.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

TRACK_FILENAME = "track.yml"

REQUIRED_KEYS = frozenset({"continuous", "lanes"})
OPTIONAL_KEYS = frozenset({"name", "description", "lap_length_inches", "centerline", "side_lines"})
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS

# Fields from when the track was modelled as a chain of "T" segments. Real
# tracks are a centreline with side-lines whose spacing varies, so these no
# longer describe anything. They are refused by name rather than lumped in with
# typos, so an upgraded car says exactly what to delete.
RETIRED_KEYS = frozenset(
    {
        "segment_length_inches",
        "cross_length_inches",
        "segment_count",
        "cross_colors",
        "tape_width_inches",
        "tape_color",
    }
)

CENTERLINE_KEYS = frozenset({"color", "width_inches", "dashed"})
SIDE_LINE_KEYS = frozenset({"color", "left_inches", "right_inches"})

# Every track must answer the same three high-level commands: drive in the left
# lane, on the centreline, or in the right lane. The centre lane is the
# centreline by definition, so it is never configured -- only left and right are.
REQUIRED_LANES = ("left", "right")
CENTER_LANE = "center"

NOMINAL_NOTE = (
    "These values are nominal: measured once, as guidance. The track's width and the centreline's "
    "position vary along the course, so where it matters, measure from the camera frame with "
    "measure_ground_point rather than trusting these numbers."
)


class TrackConfigError(ValueError):
    """The track file is unusable. The message names the offending field."""


@dataclass(frozen=True)
class Centerline:
    """The line the autopilot follows."""

    color: str = "yellow"
    width_inches: float = 1.0
    dashed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"color": self.color, "width_inches": self.width_inches, "dashed": self.dashed}


@dataclass(frozen=True)
class SideLines:
    """Lines marking the edges of the track, as nominal distances from the centreline."""

    color: str | None = None
    left_inches: float | None = None
    right_inches: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"color": self.color, "left_inches": self.left_inches, "right_inches": self.right_inches}


@dataclass(frozen=True)
class TrackConfig:
    """A validated track description. Every distance in it is nominal."""

    continuous: bool
    lanes: dict[str, float]
    name: str | None = None
    description: str | None = None
    lap_length_inches: float | None = None
    centerline: Centerline = field(default_factory=Centerline)
    side_lines: SideLines | None = None

    def lane_names(self) -> list[str]:
        return sorted(self.lanes)

    def offset_inches(self, lane: str) -> float:
        """Look up a named lane, or say which names exist."""
        try:
            return self.lanes[lane]
        except KeyError:
            raise TrackConfigError(f"Unknown lane {lane!r}. Known lanes: {self.lane_names()}") from None

    def to_dict(self) -> dict[str, Any]:
        """The shape the MCP `get_track_config` tool returns."""
        return {
            "name": self.name,
            "description": self.description,
            "nominal": True,
            "note": NOMINAL_NOTE,
            "continuous": self.continuous,
            "lap_length_inches": self.lap_length_inches,
            "centerline": self.centerline.to_dict(),
            "side_lines": self.side_lines.to_dict() if self.side_lines else None,
            "lanes": dict(self.lanes),
        }


def default_track() -> TrackConfig:
    """What to report when a car has no track file."""
    return TrackConfig(
        continuous=False,
        lanes={"left": -12.0, CENTER_LANE: 0.0, "right": 12.0},
        description="Default track description; no track.yml was found.",
    )


def find_track_file(car_dir: str | None) -> str | None:
    if not car_dir:
        return None
    path = os.path.join(os.path.expanduser(car_dir), TRACK_FILENAME)
    return path if os.path.exists(path) else None


def load_track(path: str) -> TrackConfig:
    """Read and validate a track file."""
    try:
        with open(path) as handle:
            raw = yaml.safe_load(handle)
    except OSError as exc:
        raise TrackConfigError(f"Could not read track file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise TrackConfigError(f"{path} is not valid YAML: {exc}") from exc

    if raw is None:
        raise TrackConfigError(f"{path} is empty")
    if not isinstance(raw, dict):
        raise TrackConfigError(f"{path} must contain a mapping at the top level, got {type(raw).__name__}")

    return parse_track(raw, source=path)


def parse_track(raw: dict[str, Any], source: str = "<track>") -> TrackConfig:
    """Validate an already-parsed mapping."""
    retired = sorted(set(raw) & RETIRED_KEYS)
    if retired:
        raise TrackConfigError(
            f"{source}: {retired} are no longer used. The track is described by its centreline, "
            "side-lines and lanes, not by segments; delete these fields. Put the tape's colour and "
            "width under 'centerline' if you want to keep them."
        )

    unknown = sorted(set(raw) - ALLOWED_KEYS)
    if unknown:
        # This is also what keeps a traffic-feature list out of the schema: it
        # is not an accepted key, so adding one is an error rather than a
        # silently ignored section.
        raise TrackConfigError(f"{source}: unknown field(s) {unknown}. Allowed fields: {sorted(ALLOWED_KEYS)}")

    missing = sorted(REQUIRED_KEYS - set(raw))
    if missing:
        raise TrackConfigError(f"{source}: missing required field(s) {missing}")

    continuous = raw["continuous"]
    if not isinstance(continuous, bool):
        raise TrackConfigError(f"{source}: 'continuous' must be true or false, got {continuous!r}")

    lap_length = (
        _positive_number(raw, "lap_length_inches", source) if raw.get("lap_length_inches") is not None else None
    )

    return TrackConfig(
        continuous=continuous,
        lanes=_lanes(raw["lanes"], source),
        name=_optional_str(raw, "name", source),
        description=_optional_str(raw, "description", source),
        lap_length_inches=lap_length,
        centerline=_centerline(raw.get("centerline"), source),
        side_lines=_side_lines(raw.get("side_lines"), source),
    )


def _block(value: object, key: str, allowed: frozenset[str], source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TrackConfigError(f"{source}: '{key}' must be a mapping, got {value!r}")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise TrackConfigError(f"{source}: unknown field(s) {unknown} in '{key}'. Allowed fields: {sorted(allowed)}")
    return value


def _centerline(value: object, source: str) -> Centerline:
    if value is None:
        return Centerline()
    block = _block(value, "centerline", CENTERLINE_KEYS, source)
    where = f"{source}: centerline"
    dashed = block.get("dashed", False)
    if not isinstance(dashed, bool):
        raise TrackConfigError(f"{where}: 'dashed' must be true or false, got {dashed!r}")
    return Centerline(
        color=_optional_str(block, "color", where) or "yellow",
        width_inches=_positive_number(block, "width_inches", where) if "width_inches" in block else 1.0,
        dashed=dashed,
    )


def _side_lines(value: object, source: str) -> SideLines | None:
    if value is None:
        return None
    block = _block(value, "side_lines", SIDE_LINE_KEYS, source)
    where = f"{source}: side_lines"
    return SideLines(
        color=_optional_str(block, "color", where),
        left_inches=_positive_number(block, "left_inches", where) if block.get("left_inches") is not None else None,
        right_inches=_positive_number(block, "right_inches", where) if block.get("right_inches") is not None else None,
    )


def _positive_number(raw: dict[str, Any], key: str, source: str) -> float:
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrackConfigError(f"{source}: '{key}' must be a number, got {value!r}")
    if value <= 0:
        raise TrackConfigError(f"{source}: '{key}' must be positive, got {value}")
    return float(value)


def _optional_str(raw: dict[str, Any], key: str, source: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TrackConfigError(f"{source}: '{key}' must be text, got {value!r}")
    return value


def _lanes(value: object, source: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise TrackConfigError(f"{source}: 'lanes' must be a mapping of name to offset in inches, got {value!r}")
    if not value:
        raise TrackConfigError(f"{source}: 'lanes' must name at least one lane")

    lanes: dict[str, float] = {}
    for name, offset in value.items():
        if not isinstance(name, str) or not name.strip():
            raise TrackConfigError(f"{source}: lane names must be non-empty text, got {name!r}")
        if isinstance(offset, bool) or not isinstance(offset, (int, float)):
            raise TrackConfigError(f"{source}: lane {name!r} offset must be a number of inches, got {offset!r}")
        if name.lower() == CENTER_LANE:
            # Always the centreline, so there is nothing to configure, and a
            # file that tries is saying something it cannot mean.
            raise TrackConfigError(
                f"{source}: lane 'center' is always the centreline (0) and must not be configured; remove it."
            )
        # YAML mappings cannot repeat a key, but a case difference reads as a
        # duplicate to anyone using the file and would silently shadow.
        if name.lower() in {existing.lower() for existing in lanes}:
            raise TrackConfigError(f"{source}: duplicate lane name {name!r}")
        lanes[name] = float(offset)

    absent = [name for name in REQUIRED_LANES if name not in lanes]
    if absent:
        raise TrackConfigError(
            f"{source}: 'lanes' must name {list(REQUIRED_LANES)}; missing {absent}. Further lanes are allowed."
        )
    # The sign convention is easy to get backwards, and backwards is the car on
    # the wrong side of the track, so check it rather than trust it.
    if lanes["left"] >= 0:
        raise TrackConfigError(f"{source}: lane 'left' must be negative (left of the centreline), got {lanes['left']}")
    if lanes["right"] <= 0:
        raise TrackConfigError(
            f"{source}: lane 'right' must be positive (right of the centreline), got {lanes['right']}"
        )
    return {**lanes, CENTER_LANE: 0.0}
