"""
What the agent can see.

A real agent implements `Perception` with a vision model: hand it the camera
frame, get back what is in view. The scripted implementation here exists so the
driving logic can be tested and demonstrated without one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Sighting:
    """Something the agent recognises in the frame."""

    kind: str
    pixel: tuple[float, float]
    text: str | None = None
    # An obstacle you must wait for (a person, an animal) versus one you may
    # drive around (a parked car). The agent decides which by looking.
    blocking: bool = True


class Perception(Protocol):
    """Turn a camera frame into sightings."""

    def observe(self, frame: bytes | None, state: dict[str, Any]) -> list[Sighting]: ...


class ScriptedPerception:
    """
    Replays a fixed list of sightings, one loop at a time.

    Used by the tests and by `--demo`, so the activities can be exercised end to
    end against a real vehicle loop without a vision model in the way.
    """

    def __init__(self, script: list[list[Sighting]] | None = None) -> None:
        self._script = list(script or [])
        self._index = 0

    def observe(self, frame: bytes | None, state: dict[str, Any]) -> list[Sighting]:
        if self._index >= len(self._script):
            return []
        sightings = self._script[self._index]
        self._index += 1
        return sightings

    @property
    def exhausted(self) -> bool:
        return self._index >= len(self._script)
