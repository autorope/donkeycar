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
from typing import Any

logger = logging.getLogger(__name__)

#: Applied to steering and throttle unless a template says otherwise.
#: Matches JOYSTICK_DEADZONE in the shipped configuration.
#:
#: Note the measured jitter on a real pad reached 0.099, well past this, so
#: a car whose sticks idle that far out wants a larger value.  Raise
#: JOYSTICK_DEADZONE in myconfig.py rather than editing this.
DEFAULT_DEAD_ZONE = 0.01

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

    The dead zone is applied by default.  The legacy controller applied
    JOYSTICK_DEADZONE only to the decision about whether to record and never
    to the steering value, so a resting stick steered the car a little --
    measured jitter on a real pad reached 0.099.  Pass dead_zone=0.0 for the
    old behavior.
    """

    def __init__(
        self,
        scale: float = 1.0,
        dead_zone: float = DEFAULT_DEAD_ZONE,
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
        dead_zone: float = DEFAULT_DEAD_ZONE,
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

    def __init__(
        self, scale: float = 1.0, dead_zone: float = DEFAULT_DEAD_ZONE
    ) -> None:
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


#: The pilot modes, in the order TogglePilotMode steps through them.
#:
#: 'user' is human steering and throttle, 'local_angle' is the pilot
#: steering with human throttle, and 'local' is the pilot driving.
PILOT_MODES = ('user', 'local_angle', 'local')

DEFAULT_PILOT_MODE = PILOT_MODES[0]


class TogglePilotMode:
    """
    Steps the pilot mode on: user, local_angle, local, and round again.

        V.add(TogglePilotMode(),
              inputs=['user/mode'],
              outputs=['user/mode'],
              run_condition=format_button_event('y_button', BUTTON_DOWN))

    Steps once per call, so it needs a run condition that is true for one
    pass through the loop -- which is exactly what an input event is.
    Without one it would race through the modes several times a second.

    Takes the current mode as an input and returns the next, rather than
    keeping the mode itself, so that anything else can change the mode too
    and this part will still step on from wherever it actually is.
    """

    def __init__(self, modes: tuple[str, ...] = PILOT_MODES) -> None:
        self.modes = modes

    def run(self, mode: str | None = None) -> str:
        if mode not in self.modes:
            # nothing set it yet, or something set a mode we do not know;
            # either way the first mode is the safe answer, since it is the
            # one where the human is driving
            return self.modes[0]

        index = self.modes.index(mode)
        next_mode = self.modes[(index + 1) % len(self.modes)]
        logger.info(f'pilot mode: {next_mode}')
        return next_mode


class ToggleRecording:
    """
    Turns recording on or off.

        V.add(ToggleRecording(),
              inputs=['recording'],
              outputs=['recording'],
              run_condition=format_button_event('b_button', BUTTON_DOWN))

    Like TogglePilotMode this flips once per call and takes the current
    value as an input, so it needs a one-pass run condition.

    This replaces the ToggleRecording in complete.py, which #1097 asks to
    have removed.  That part decided three separate things at once -- a
    manual toggle, whether auto-record-on-throttle should override it, and
    whether recording is allowed in autopilot -- through two latches and a
    remembered previous value, which is why it could not be moved to
    another button.  Each of those is now its own part.
    """

    def run(self, recording: bool | None = None) -> bool:
        toggled = not bool(recording)
        logger.info(f'recording: {toggled}')
        return toggled


class AutoRecordOnThrottle:
    """
    Records whenever the car is being driven.

        V.add(AutoRecordOnThrottle(dead_zone=cfg.JOYSTICK_DEADZONE),
              inputs=['user/throttle', 'user/mode'],
              outputs=['recording'])

    Runs every pass rather than on an event, since it follows the throttle
    rather than a button.  Add it *instead of* ToggleRecording: with both,
    whichever runs later in the loop wins and the button appears to do
    nothing every time the throttle is open.

    Only records while the human is driving, unless record_in_autopilot is
    set.  Recording the pilot's own output and then training on it teaches
    the pilot to do what it already does.
    """

    def __init__(
        self,
        dead_zone: float = DEFAULT_DEAD_ZONE,
        record_in_autopilot: bool = False,
        user_mode: str = DEFAULT_PILOT_MODE,
    ) -> None:
        """
        dead_zone:           throttle smaller than this is not driving
        record_in_autopilot: record while a pilot is driving too
        user_mode:           the mode in which the human is driving
        """
        self.dead_zone = dead_zone
        self.record_in_autopilot = record_in_autopilot
        self.user_mode = user_mode
        self._recording = False

    def run(
        self,
        throttle: float | None = None,
        mode: str | None = None,
    ) -> bool:
        driving = abs(throttle or 0.0) > self.dead_zone
        if mode is not None and mode != self.user_mode:
            driving = driving and self.record_in_autopilot

        if driving != self._recording:
            self._recording = driving
            logger.info(f'recording: {driving}')
        return driving


class EraseLastNRecords:
    """
    Throws away the last few records, for when a run goes wrong.

        V.add(EraseLastNRecords(tub_writer.tub, cfg.ERASE_LAST_N_RECORDS),
              run_condition=format_button_event('x_button', BUTTON_DOWN))

    Erases once per call, so it wants a one-pass run condition; on a held
    button it would erase the whole tub in a couple of seconds.

    Consider binding this to a click rather than a press, or to a
    double-click, since it cannot be undone.
    """

    def __init__(self, tub: Any, num_records: int = 100) -> None:
        """
        tub:         the tub to erase from
        num_records: how many of the most recent records to erase
        """
        self.tub = tub
        self.num_records = num_records

    def run(self) -> None:
        if self.tub is None:
            logger.warning('No tub to erase records from.')
            return

        try:
            self.tub.delete_last_n_records(self.num_records)
            logger.info(f'deleted last {self.num_records} records')
        except Exception:
            # erasing is a convenience; failing to erase must not stop a
            # car that is driving
            logger.exception('Failed to erase records.')


class ShowRecordCount:
    """
    Asks for the record count to be announced.

        V.add(ShowRecordCount(rec_tracker),
              run_condition=format_button_event('view', BUTTON_DOWN))

    In the legacy template this hijacked the circle button whenever
    auto-record-on-throttle was on, on the reasoning that the button was
    free because manual recording was disabled.  As a part it can go on any
    button, and does not need manual recording to be off.
    """

    def __init__(self, record_tracker: Any) -> None:
        self.record_tracker = record_tracker

    def run(self) -> None:
        if self.record_tracker is None:
            return
        self.record_tracker.last_num_rec_print = 0
        self.record_tracker.force_alert = 1


#: How much one press changes the throttle limit.  Matches the legacy step.
DEFAULT_THROTTLE_STEP = 0.01

#: The most and least the throttle limit can be set to.
MIN_THROTTLE_SCALE = 0.0
MAX_THROTTLE_SCALE = 1.0

#: The throttle limit is rounded to this many places, as the legacy code
#: did, so that repeated steps do not accumulate float error and leave the
#: limit reading 0.7300000000000001.
THROTTLE_SCALE_PLACES = 2


class AdjustMaxThrottle:
    """
    Raises or lowers the throttle limit while driving.

        V.add(AdjustMaxThrottle(+cfg.THROTTLE_STEP),
              inputs=['user/throttle_scale'],
              outputs=['user/throttle_scale'],
              run_condition=format_button_event('dpad_up', BUTTON_DOWN))
        V.add(AdjustMaxThrottle(-cfg.THROTTLE_STEP),
              inputs=['user/throttle_scale'],
              outputs=['user/throttle_scale'],
              run_condition=format_button_event('dpad_down', BUTTON_DOWN))

    One part with a signed step, rather than a separate part for up and
    down, so both directions cannot drift apart.

    Steps once per call, so it wants a one-pass run condition.  Note that
    binding it to a press gives one step per press, which at the default
    step of 0.01 takes fifty presses to cross half the range -- fine for
    trimming, tedious for a real change.  Binding it to '/hold' instead
    gives one step per hold rather than a repeat; there is deliberately no
    key-repeat here, because a part that repeats while a button is held
    would need to know how long it has been held, and that belongs in the
    event layer if it is ever wanted.

    Takes the current limit as an input, so the web interface or a config
    reload can change it too.
    """

    def __init__(
        self,
        step: float = DEFAULT_THROTTLE_STEP,
        default_scale: float = MAX_THROTTLE_SCALE,
    ) -> None:
        """
        step:          how much to change the limit by, signed
        default_scale: the limit to assume when nothing has set one
        """
        self.step = step
        self.default_scale = default_scale

    def run(self, throttle_scale: float | None = None) -> float:
        current = self.default_scale if throttle_scale is None else throttle_scale
        adjusted = current + self.step
        adjusted = max(MIN_THROTTLE_SCALE, min(MAX_THROTTLE_SCALE, adjusted))
        adjusted = round(adjusted, THROTTLE_SCALE_PLACES)

        logger.info(f'throttle scale: {adjusted}')
        return adjusted


class ToggleConstantThrottle:
    """
    Holds the throttle open without the control being touched, so the car
    can be driven on steering alone.

        V.add(ToggleConstantThrottle(),
              inputs=['user/constant_throttle'],
              outputs=['user/constant_throttle'],
              run_condition=format_button_event('start', BUTTON_DOWN))

    This only says whether constant throttle is wanted.  ConstantThrottle
    is the part that acts on it, because what to do about the throttle is a
    separate question from whether the driver asked for it -- and the
    legacy version answered both at once, which is why it could not be
    rebound.

    Steps once per call, so it wants a one-pass run condition.
    """

    def run(self, constant_throttle: bool | None = None) -> bool:
        toggled = not bool(constant_throttle)
        logger.info(f'constant throttle: {toggled}')
        return toggled


class ConstantThrottle:
    """
    Supplies the throttle while constant throttle is on.

        V.add(ConstantThrottle(),
              inputs=['user/constant_throttle', 'user/throttle_scale',
                      'user/throttle'],
              outputs=['user/throttle'])

    Add it after the part that reads the throttle control, since it
    overrides that part's answer while it is on and passes it through
    untouched while it is off.

    While on, the throttle is held at the current limit -- so the same
    control that trims the limit also sets the speed the car holds, which
    is what makes AdjustMaxThrottle worth binding on a car driven this way.

    Turning it off gives no throttle rather than handing back whatever the
    control happens to read.  A driver who has not touched the throttle for
    a lap will have it resting at zero, and a car that lurched to whatever
    the stick said at that moment would be a surprise.  The next real
    movement of the control takes over as usual.
    """

    def __init__(self, default_scale: float = MAX_THROTTLE_SCALE) -> None:
        self.default_scale = default_scale
        self._was_on = False

    def run(
        self,
        constant_throttle: bool | None = None,
        throttle_scale: float | None = None,
        throttle: float | None = None,
    ) -> float:
        is_on = bool(constant_throttle)
        scale = self.default_scale if throttle_scale is None else throttle_scale

        if is_on:
            self._was_on = True
            return scale

        if self._was_on:
            # just switched off; stop rather than jump to whatever the
            # control reads right now
            self._was_on = False
            return 0.0

        return throttle or 0.0
