"""
The track description an agent reads before it starts driving.

Geometry only. Traffic features -- stop signs, addresses, obstacles -- are
deliberately absent: the agent discovers those in the camera frame, which is
what the learning progression is about, and it means a track can be rearranged
or have features moved around it without editing this file.

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

REQUIRED_KEYS = frozenset({"segment_length_inches", "cross_length_inches", "continuous", "lanes"})
OPTIONAL_KEYS = frozenset({"name", "description", "tape_width_inches", "segment_count", "tape_color", "cross_colors"})
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS


class TrackConfigError(ValueError):
    """The track file is unusable. The message names the offending field."""


@dataclass(frozen=True)
class TrackConfig:
    """A validated track description."""

    segment_length_inches: float
    cross_length_inches: float
    continuous: bool
    lanes: dict[str, float]
    name: str | None = None
    description: str | None = None
    tape_width_inches: float = 1.0
    segment_count: int | None = None
    tape_color: str = "yellow"
    cross_colors: list[str] = field(default_factory=lambda: ["red", "blue"])

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
            "segment_length_inches": self.segment_length_inches,
            "cross_length_inches": self.cross_length_inches,
            "tape_width_inches": self.tape_width_inches,
            "tape_color": self.tape_color,
            "cross_colors": list(self.cross_colors),
            "segment_count": self.segment_count,
            "continuous": self.continuous,
            "lanes": dict(self.lanes),
        }


def default_track() -> TrackConfig:
    """What to report when a car has no track file."""
    return TrackConfig(
        segment_length_inches=36.0,
        cross_length_inches=12.0,
        continuous=False,
        lanes={"left": -12.0, "center": 0.0, "right": 12.0},
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
    unknown = sorted(set(raw) - ALLOWED_KEYS)
    if unknown:
        # This is also what keeps a traffic-feature list out of the schema: it
        # is not an accepted key, so adding one is an error rather than a
        # silently ignored section.
        raise TrackConfigError(f"{source}: unknown field(s) {unknown}. Allowed fields: {sorted(ALLOWED_KEYS)}")

    missing = sorted(REQUIRED_KEYS - set(raw))
    if missing:
        raise TrackConfigError(f"{source}: missing required field(s) {missing}")

    segment_length = _positive_number(raw, "segment_length_inches", source)
    cross_length = _positive_number(raw, "cross_length_inches", source)
    tape_width = _positive_number(raw, "tape_width_inches", source) if "tape_width_inches" in raw else 1.0

    continuous = raw["continuous"]
    if not isinstance(continuous, bool):
        raise TrackConfigError(f"{source}: 'continuous' must be true or false, got {continuous!r}")

    segment_count = raw.get("segment_count")
    if segment_count is not None:
        if not isinstance(segment_count, int) or isinstance(segment_count, bool):
            raise TrackConfigError(f"{source}: 'segment_count' must be a whole number, got {segment_count!r}")
        if segment_count <= 0:
            raise TrackConfigError(f"{source}: 'segment_count' must be positive, got {segment_count}")

    lanes = _lanes(raw["lanes"], source)

    return TrackConfig(
        segment_length_inches=segment_length,
        cross_length_inches=cross_length,
        continuous=continuous,
        lanes=lanes,
        name=_optional_str(raw, "name", source),
        description=_optional_str(raw, "description", source),
        tape_width_inches=tape_width,
        segment_count=segment_count,
        tape_color=_optional_str(raw, "tape_color", source) or "yellow",
        cross_colors=_colors(raw.get("cross_colors"), source),
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


def _colors(value: object, source: str) -> list[str]:
    if value is None:
        return ["red", "blue"]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TrackConfigError(f"{source}: 'cross_colors' must be a list of colour names, got {value!r}")
    return list(value)


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
        # YAML mappings cannot repeat a key, but a case difference reads as a
        # duplicate to anyone using the file and would silently shadow.
        if name.lower() in {existing.lower() for existing in lanes}:
            raise TrackConfigError(f"{source}: duplicate lane name {name!r}")
        lanes[name] = float(offset)
    return lanes
