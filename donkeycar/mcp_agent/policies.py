"""
The five activities, as policies.

Each is the next one's base class, because the progression is cumulative: an
agent that stops at addresses also stops at stop signs, and one that drives
around obstacles also stops for the ones it must not pass.

A policy decides only what to do with throttle and lane. It never steers -- the
CV autopilot does that at loop rate, and an agent in the steering path would be
a round trip behind the road.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from donkeycar.mcp_agent.perception import Perception, Sighting
from donkeycar.mcp_agent.session import CarSession

logger = logging.getLogger(__name__)

CRUISE_THROTTLE = 0.35
STOP_SIGN_PAUSE_S = 5.0
# Start slowing at this distance, and be stopped by STOP_DISTANCE_INCHES.
SLOW_DISTANCE_INCHES = 36.0
STOP_DISTANCE_INCHES = 12.0


class Policy:
    """
    Base behaviour: hold a cruise throttle in the centre lane.

    `step` is called once per agent tick. It is deliberately not a loop, so a
    caller can drive it from a test, a demo, or a real agent's own cadence.
    """

    name = "base"

    def __init__(self, session: CarSession, perception: Perception) -> None:
        self.session = session
        self.perception = perception
        self.track: dict[str, Any] = {}
        self.finished = False
        self.log: list[str] = []

    # ------------------------------------------------------------------ helpers

    def begin(self) -> None:
        self.track = self.session.get_track_config()
        self.session.start()
        self.session.set_control(throttle=CRUISE_THROTTLE, lane="center")
        self._note(f"started on a track of {self.track.get('segment_count')} segments")

    def end(self) -> None:
        self.session.set_control(throttle=0.0)
        self.session.stop()
        self._note("stopped")

    def _note(self, message: str) -> None:
        self.log.append(message)
        logger.info("[%s] %s", self.name, message)

    def _distance_inches(self, sighting: Sighting) -> float | None:
        """
        How far ahead is it?

        This is why the calibration exists. Without it the only cue is apparent
        size, guessed over a round trip while the car keeps moving.
        """
        try:
            ground = self.session.measure_ground_point(*sighting.pixel)
        except Exception as exc:
            self._note(f"could not measure {sighting.kind}: {exc}")
            return None
        return float(ground["forward_inches"])

    def _approach_throttle(self, distance: float | None) -> float:
        """Slow down with distance; stop inside the stopping distance."""
        if distance is None:
            return CRUISE_THROTTLE
        if distance <= STOP_DISTANCE_INCHES:
            return 0.0
        if distance >= SLOW_DISTANCE_INCHES:
            return CRUISE_THROTTLE
        span = SLOW_DISTANCE_INCHES - STOP_DISTANCE_INCHES
        return CRUISE_THROTTLE * (distance - STOP_DISTANCE_INCHES) / span

    def _first(self, sightings: list[Sighting], kind: str) -> Sighting | None:
        return next((s for s in sightings if s.kind == kind), None)

    # --------------------------------------------------------------------- step

    def step(self) -> None:
        state, frame = self.session.get_vehicle_state()
        sightings = self.perception.observe(frame, state)
        self.handle(state, sightings)

    def handle(self, state: dict[str, Any], sightings: list[Sighting]) -> None:
        if self._lap_complete(sightings):
            self._note("lap complete")
            self.finished = True
            self.session.set_control(throttle=0.0)
            return
        self.session.set_control(throttle=CRUISE_THROTTLE)

    def _lap_complete(self, sightings: list[Sighting]) -> bool:
        return self._first(sightings, "lap_complete") is not None


class LapPolicy(Policy):
    """Activity 1: drive once around the track and stop."""

    name = "lap"


class StopSignPolicy(LapPolicy):
    """Activity 2: also stop for 5 seconds at stop signs."""

    name = "stop-signs"

    def __init__(
        self, session: CarSession, perception: Perception, clock: Callable[[], float] = time.monotonic
    ) -> None:
        super().__init__(session, perception)
        self._clock = clock
        self._waiting_until: float | None = None
        self._served: set[tuple[float, float]] = set()

    def handle(self, state: dict[str, Any], sightings: list[Sighting]) -> None:
        if self._waiting_until is not None:
            if self._clock() < self._waiting_until:
                self.session.set_control(throttle=0.0)
                return
            self._waiting_until = None
            self._note("stop sign wait over, moving off")

        sign = self._first(sightings, "stop_sign")
        if sign is not None and sign.pixel not in self._served:
            distance = self._distance_inches(sign)
            throttle = self._approach_throttle(distance)
            self.session.set_control(throttle=throttle)
            if throttle == 0.0:
                self._served.add(sign.pixel)
                self._waiting_until = self._clock() + STOP_SIGN_PAUSE_S
                self._note(f"stopped at a stop sign {distance} inches ahead; waiting {STOP_SIGN_PAUSE_S}s")
            return

        super().handle(state, sightings)


class ObstacleHaltPolicy(StopSignPolicy):
    """Activity 3: also wait at obstacles until they are removed."""

    name = "obstacle-halt"

    def handle(self, state: dict[str, Any], sightings: list[Sighting]) -> None:
        obstacle = self._first(sightings, "obstacle")
        if obstacle is not None:
            distance = self._distance_inches(obstacle)
            throttle = self._approach_throttle(distance)
            self.session.set_control(throttle=throttle)
            if throttle == 0.0:
                self._note("waiting for the obstacle to clear")
            return

        super().handle(state, sightings)


class ObstacleAvoidPolicy(ObstacleHaltPolicy):
    """
    Activity 4: drive around obstacles that can be passed.

    Blocking obstacles -- a person, an animal -- still stop the car. Which is
    which is a judgement the agent makes by looking, not something the track
    file declares.
    """

    name = "obstacle-avoid"

    def __init__(
        self, session: CarSession, perception: Perception, clock: Callable[[], float] = time.monotonic
    ) -> None:
        super().__init__(session, perception, clock)
        self._detoured = False

    def handle(self, state: dict[str, Any], sightings: list[Sighting]) -> None:
        obstacle = self._first(sightings, "obstacle")
        if obstacle is not None and not obstacle.blocking:
            lane = self._passing_lane()
            self.session.set_control(throttle=CRUISE_THROTTLE, lane=lane)
            self._detoured = True
            self._note(f"passing the obstacle in the {lane} lane")
            return

        if self._detoured and obstacle is None:
            self.session.set_control(lane="center")
            self._detoured = False
            self._note("back to the centre lane")

        super().handle(state, sightings)

    def _passing_lane(self) -> str:
        lanes = self.track.get("lanes", {})
        # Prefer a named lane on the far side from the obstacle; "left" is the
        # convention for passing on this track.
        for candidate in ("left", "right"):
            if candidate in lanes:
                return candidate
        return "center"


class AddressPolicy(ObstacleAvoidPolicy):
    """
    Activity 5: stop at a numbered address and wait to be released.

    `release()` is what the operator (or the agent's own supervisor) calls to
    let it move on.
    """

    name = "address"

    def __init__(
        self,
        session: CarSession,
        perception: Perception,
        destination: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(session, perception, clock)
        self.destination = destination
        self.arrived = False
        self._released = False

    def release(self) -> None:
        self._released = True
        self._note("released; continuing")

    def handle(self, state: dict[str, Any], sightings: list[Sighting]) -> None:
        if self.arrived and not self._released:
            self.session.set_control(throttle=0.0)
            return

        address = self._first(sightings, "address")
        if address is not None and self.destination and address.text == self.destination and not self.arrived:
            distance = self._distance_inches(address)
            throttle = self._approach_throttle(distance)
            self.session.set_control(throttle=throttle)
            if throttle == 0.0:
                self.arrived = True
                self._note(f"arrived at {self.destination}; waiting to be released")
            return

        super().handle(state, sightings)


POLICIES: dict[str, type[Policy]] = {
    "lap": LapPolicy,
    "stop-signs": StopSignPolicy,
    "obstacle-halt": ObstacleHaltPolicy,
    "obstacle-avoid": ObstacleAvoidPolicy,
    "address": AddressPolicy,
}


def build_policy(name: str, session: CarSession, perception: Perception, **kwargs: object) -> Policy:
    try:
        policy_class = POLICIES[name]
    except KeyError:
        raise ValueError(f"Unknown activity {name!r}. Known activities: {sorted(POLICIES)}") from None
    return policy_class(session, perception, **kwargs)
