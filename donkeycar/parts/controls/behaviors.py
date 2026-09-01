#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The behaviors a controller drives, as individual parts.

Each one does a single thing and says what it needs through its inputs and
outputs, so a template can bind any of them to any control -- which is the
point of the whole exercise.  The legacy JoystickController held all of
this as methods on one object sharing mutable fields, which is why its
behaviors could not be moved to different buttons.

@author: ezward
"""

import logging

logger = logging.getLogger(__name__)

#: A trigger rests at one end of its travel rather than in the middle,
#: measured on a real Xbox pad.  Before a trigger has been touched there is
#: no value for it in memory at all, and reading that absence as centre
#: would be reading it as half squeezed.
TRIGGER_RESTING = -1.0


def apply_dead_zone(value: float, dead_zone: float) -> float:
    """
    Treat a small reading as no reading.

    Sticks do not rest at exactly zero -- the test pad idled as far out as
    0.1 -- so without this a car with nobody touching it drifts.
    """
    return 0.0 if abs(value) < dead_zone else value


class UserSteering:
    """
    Turns a steering control's position into a steering value.

        V.add(UserSteering(scale=cfg.JOYSTICK_STEERING_SCALE),
              inputs=[steering_axis],
              outputs=['user/steering'],
              run_condition=steering_axis)

    Using the axis event as both the input and the run condition means the
    part runs only when the control actually moves, and gets the new
    position when it does.

    NOTE on dead_zone: the legacy controller applied JOYSTICK_DEADZONE only
    to the decision about whether to record, never to the steering value
    itself.  Wiring it here would be a change in how a car drives, so it
    defaults to zero and a template has to ask for it deliberately.
    """

    def __init__(
        self,
        scale: float = 1.0,
        dead_zone: float = 0.0,
        invert: bool = False,
    ) -> None:
        """
        scale:     how much of the control's travel to use
        dead_zone: readings smaller than this count as centred
        invert:    swap left and right, for a control wired backwards
        """
        self.scale = scale
        self.dead_zone = dead_zone
        self.direction = -1.0 if invert else 1.0

    def run(self, axis_value: float | None = None) -> float:
        if axis_value is None:
            return 0.0
        return self.direction * self.scale * apply_dead_zone(
            axis_value, self.dead_zone
        )


class UserThrottle:
    """
    Turns a throttle control's position into a throttle value.

        V.add(UserThrottle(direction=cfg.JOYSTICK_THROTTLE_DIR,
                           scale=cfg.JOYSTICK_MAX_THROTTLE),
              inputs=[throttle_axis, 'user/throttle_scale'],
              outputs=['user/throttle'],
              run_condition=throttle_axis)

    The scale is taken as an input as well as a constructor argument so
    that AdjustMaxThrottle can change it while driving.  On a car that
    never adjusts it, leave the input out and the constructor value stands.

    direction exists because a stick pushed forward usually reads negative,
    so the default of -1.0 turns "away from me" into "forwards".
    """

    def __init__(
        self,
        direction: float = -1.0,
        scale: float = 1.0,
        dead_zone: float = 0.0,
    ) -> None:
        """
        direction: -1.0 if pushing the control forward reads negative
        scale:     the most throttle to give at full travel
        dead_zone: readings smaller than this count as centred
        """
        self.direction = direction
        self.scale = scale
        self.dead_zone = dead_zone

    def run(
        self,
        axis_value: float | None = None,
        throttle_scale: float | None = None,
    ) -> float:
        if axis_value is None:
            return 0.0

        scale = self.scale if throttle_scale is None else throttle_scale
        return self.direction * scale * apply_dead_zone(
            axis_value, self.dead_zone
        )


class TriggerThrottle:
    """
    Turns a pair of triggers into a throttle: one for forward, one for
    reverse.  This is what the legacy code called Forza mode.

        V.add(TriggerThrottle(scale=cfg.JOYSTICK_MAX_THROTTLE),
              inputs=['/axis/right_trigger', '/axis/left_trigger',
                      'user/throttle_scale'],
              outputs=['user/throttle'])

    A trigger rests at -1.0 and travels to +1.0, so each is remapped to 0.0
    at rest and 1.0 fully squeezed, and the result is forward minus
    reverse.  Squeezing both therefore cancels out, which is the sensible
    reading of an ambiguous request.

    Note this takes both triggers together, unlike the legacy version,
    which bound each to its own handler and had them write the throttle in
    turn -- so whichever was moved last won outright, and holding the
    forward trigger while brushing the reverse one gave full reverse.

    Takes the control states rather than their events, because both
    triggers have to be read whenever either moves.  Give it no run
    condition; it is cheap and needs to see every change.
    """

    def __init__(self, scale: float = 1.0, dead_zone: float = 0.0) -> None:
        """
        scale:     the most throttle to give at full squeeze
        dead_zone: squeezes smaller than this count as untouched
        """
        self.scale = scale
        self.dead_zone = dead_zone

    def run(
        self,
        forward_axis: float | None = None,
        reverse_axis: float | None = None,
        throttle_scale: float | None = None,
    ) -> float:
        scale = self.scale if throttle_scale is None else throttle_scale
        forward = self._squeeze(forward_axis)
        reverse = self._squeeze(reverse_axis)
        return scale * (forward - reverse)

    def _squeeze(self, axis_value: float | None) -> float:
        """
        A trigger's position as how far it is squeezed, 0.0 to 1.0.
        """
        if axis_value is None:
            # untouched, not centred: a trigger has no value in memory
            # until it first moves, and centre would be half throttle
            axis_value = TRIGGER_RESTING

        squeeze = (axis_value - TRIGGER_RESTING) / 2.0
        squeeze = max(0.0, min(1.0, squeeze))
        return apply_dead_zone(squeeze, self.dead_zone)
