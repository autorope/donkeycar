#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls import (
    NO_CHANGE,
    ControlChange,
    LinuxGameController,
)
from donkeycar.tests.fake_js import (
    FakeJsDevice,
    axis_event,
    button_event,
    duplicate_literal_keys,
    duplicate_values,
    init_event,
)

# a small pad to test the base class with: two axes, two buttons
AXIS_CODES = (0x00, 0x01)
BUTTON_CODES = (0x130, 0x131)


class PadUnderTest(LinuxGameController):
    AXIS_NAMES = {0x00: 'left_stick_horz', 0x01: 'left_stick_vert'}
    BUTTON_NAMES = {0x130: 'A', 0x131: 'B'}


def make_pad(events=(), axis_epsilon=0.0, **kwargs) -> PadUnderTest:
    device = FakeJsDevice(
        name='Pad Under Test',
        axis_codes=AXIS_CODES,
        button_codes=BUTTON_CODES,
        events=events,
    )
    pad = PadUnderTest(device=device, axis_epsilon=axis_epsilon, **kwargs)
    pad.init()
    return pad


class TestInit(unittest.TestCase):

    def test_init_reports_success(self):
        assert make_pad() is not None

    def test_init_reads_the_device_name(self):
        assert make_pad().name == 'Pad Under Test'

    def test_init_builds_the_control_maps(self):
        pad = make_pad()
        assert pad.axis_map == ('left_stick_horz', 'left_stick_vert')
        assert pad.button_map == ('A', 'B')

    def test_init_fails_when_the_device_is_absent(self):
        device = FakeJsDevice(open_error=FileNotFoundError('no such device'))
        pad = PadUnderTest(device=device)

        assert pad.init() is False
        assert pad.poll() == NO_CHANGE

    def test_init_can_be_retried_after_failure(self):
        """
        init() returns False rather than raising for a device that is not
        there yet, so the polling thread can keep retrying while the user
        pairs the gamepad.
        """
        device = FakeJsDevice(
            axis_codes=AXIS_CODES,
            button_codes=BUTTON_CODES,
            open_error=FileNotFoundError('not paired yet'),
        )
        pad = PadUnderTest(device=device)
        assert pad.init() is False

        device.open_error = None
        assert pad.init() is True
        assert pad.button_map == ('A', 'B')

    def test_init_is_idempotent(self):
        device = FakeJsDevice(
            axis_codes=AXIS_CODES, button_codes=BUTTON_CODES
        )
        pad = PadUnderTest(device=device)

        assert pad.init() is True
        assert pad.init() is True
        assert device.open_count == 1

    def test_show_map_needs_an_initialized_device(self):
        device = FakeJsDevice(open_error=FileNotFoundError('nope'))
        pad = PadUnderTest(device=device)
        pad.init()

        assert pad.show_map() is False
        assert make_pad().show_map() is True


class TestControlNaming(unittest.TestCase):

    def test_unmapped_controls_get_default_names(self):
        device = FakeJsDevice(axis_codes=(0x07,), button_codes=(0x2FF,))
        pad = LinuxGameController(device=device)
        pad.init()

        assert pad.axis_map == ('axis(0x07)',)
        assert pad.button_map == ('button(0x2ff)',)

    def test_caller_names_override_the_built_in_map(self):
        """
        A user renaming one control in myconfig.py must not have to
        restate the whole map.
        """
        device = FakeJsDevice(
            axis_codes=AXIS_CODES, button_codes=BUTTON_CODES
        )
        pad = PadUnderTest(
            device=device,
            button_names={0x131: 'renamed'},
        )
        pad.init()

        assert pad.button_map == ('A', 'renamed')
        assert pad.axis_map == ('left_stick_horz', 'left_stick_vert')

    def test_caller_names_can_name_an_unmapped_control(self):
        device = FakeJsDevice(axis_codes=(0x07,), button_codes=())
        pad = LinuxGameController(device=device, axis_names={0x07: 'pedal'})
        pad.init()

        assert pad.axis_map == ('pedal',)

    def test_controllers_do_not_share_name_maps(self):
        """
        Regression: the name maps were mutable default arguments that
        init() wrote into, so one controller's names leaked into the next.
        """
        first = LinuxGameController(
            device=FakeJsDevice(axis_codes=(0x07,)),
            axis_names={0x07: 'first_only'},
        )
        first.init()

        second = LinuxGameController(device=FakeJsDevice(axis_codes=(0x07,)))
        second.init()

        assert first.axis_map == ('first_only',)
        assert second.axis_map == ('axis(0x07)',)

    def test_subclass_maps_are_not_mutated_by_init(self):
        make_pad()
        assert PadUnderTest.AXIS_NAMES == {
            0x00: 'left_stick_horz',
            0x01: 'left_stick_vert',
        }
        assert PadUnderTest.BUTTON_NAMES == {0x130: 'A', 0x131: 'B'}


class TestButtonPolling(unittest.TestCase):

    def test_poll_reports_a_press(self):
        pad = make_pad([button_event(0, 1)])
        assert pad.poll() == ControlChange(button='A', button_state=1)

    def test_poll_reports_a_release(self):
        pad = make_pad([button_event(1, 1), button_event(1, 0)])
        assert pad.poll().button_state == 1
        change = pad.poll()
        assert change.button == 'B'
        assert change.button_state == 0

    def test_poll_normalizes_the_button_value(self):
        """
        The driver's value is only meaningfully zero or non-zero.
        """
        pad = make_pad([button_event(0, 7)])
        assert pad.poll().button_state == 1

    def test_poll_returns_no_change_when_idle(self):
        assert make_pad().poll() == NO_CHANGE

    def test_poll_before_init_returns_no_change(self):
        device = FakeJsDevice(
            axis_codes=AXIS_CODES,
            button_codes=BUTTON_CODES,
            events=[button_event(0, 1)],
        )
        pad = PadUnderTest(device=device)

        assert pad.poll() == NO_CHANGE

    def test_poll_ignores_the_drivers_init_events(self):
        """
        The driver replays every control's current state on open; those are
        not real changes and must not reach the event system.
        """
        pad = make_pad([init_event(0, 1), button_event(1, 1)])

        assert pad.poll() == NO_CHANGE
        assert pad.poll().button == 'B'

    def test_poll_ignores_an_undeclared_button(self):
        pad = make_pad([button_event(99, 1), button_event(0, 1)])

        assert pad.poll() == NO_CHANGE
        assert pad.poll().button == 'A'


class TestAxisPolling(unittest.TestCase):

    def test_poll_scales_the_axis_value(self):
        pad = make_pad([axis_event(0, 32767)])
        change = pad.poll()

        assert change.axis == 'left_stick_horz'
        assert change.axis_value == 1.0

    def test_poll_scales_a_negative_axis_value(self):
        pad = make_pad([axis_event(1, -32767)])
        assert pad.poll().axis_value == -1.0

    def test_poll_reports_center(self):
        pad = make_pad([axis_event(0, 16384), axis_event(0, 0)])
        assert pad.poll().axis_value > 0
        assert pad.poll().axis_value == 0.0

    def test_poll_suppresses_an_unchanged_axis(self):
        pad = make_pad([axis_event(0, 16384), axis_event(0, 16384)])

        assert pad.poll().axis_value > 0
        assert pad.poll() == NO_CHANGE

    def test_poll_ignores_an_undeclared_axis(self):
        pad = make_pad([axis_event(99, 32767), axis_event(0, 32767)])

        assert pad.poll() == NO_CHANGE
        assert pad.poll().axis == 'left_stick_horz'


class TestAxisJitterFilter(unittest.TestCase):

    def test_jitter_below_epsilon_is_suppressed(self):
        pad = make_pad(
            [axis_event(0, 100), axis_event(0, 200), axis_event(0, 300)],
            axis_epsilon=0.05,
        )
        assert pad.poll() == NO_CHANGE
        assert pad.poll() == NO_CHANGE
        assert pad.poll() == NO_CHANGE

    def test_movement_past_epsilon_is_reported(self):
        pad = make_pad([axis_event(0, 16384)], axis_epsilon=0.05)
        assert pad.poll().axis_value > 0.4

    def test_sustained_slow_movement_accumulates_past_epsilon(self):
        """
        Each step is under the deadband, but the comparison is against the
        last *reported* value, so a slow push still gets through instead of
        being filtered away one small step at a time.
        """
        steps = [axis_event(0, v) for v in (500, 1000, 1500, 2000, 2500)]
        pad = make_pad(steps, axis_epsilon=0.05)
        reported = [c for c in (pad.poll() for _ in steps) if c != NO_CHANGE]

        assert len(reported) == 1
        assert reported[0].axis_value == 2000 / 32767.0

    def test_return_to_center_is_always_reported(self):
        """
        The last step back to zero is smaller than the deadband here, so
        without the exact-center exemption it would be swallowed and leave
        the throttle or steering stuck slightly off center.
        """
        pad = make_pad(
            [axis_event(0, 32767), axis_event(0, 500), axis_event(0, 0)],
            axis_epsilon=0.05,
        )
        assert pad.poll().axis_value == 1.0
        settling = pad.poll().axis_value
        assert 0.0 < settling < 0.05  # the next step down is under epsilon
        assert pad.poll().axis_value == 0.0

    def test_zero_epsilon_reports_every_change(self):
        pad = make_pad([axis_event(0, 1), axis_event(0, 2)])
        assert pad.poll().axis_value == 1 / 32767.0
        assert pad.poll().axis_value == 2 / 32767.0


class TestControlChange(unittest.TestCase):

    def test_control_change_unpacks_as_a_four_tuple(self):
        """
        ControlChange is a NamedTuple so the older four-tuple unpacking
        used throughout the joystick code keeps working.
        """
        pad = make_pad([button_event(0, 1)])
        button, button_state, axis, axis_value = pad.poll()

        assert button == 'A'
        assert button_state == 1
        assert axis is None
        assert axis_value is None


class TestShutdown(unittest.TestCase):

    def test_shutdown_closes_the_device(self):
        device = FakeJsDevice(
            axis_codes=AXIS_CODES, button_codes=BUTTON_CODES
        )
        pad = PadUnderTest(device=device)
        pad.init()
        pad.shutdown()

        assert device.closed is True
        assert pad.poll() == NO_CHANGE


class TestNameMapAssertions(unittest.TestCase):
    """
    Self-tests for the shared helpers the per-gamepad commits rely on; a
    helper that silently passes everything would be worse than none.
    """

    def test_duplicate_values_finds_a_repeated_name(self):
        assert duplicate_values({0x01: 'A', 0x02: 'A', 0x03: 'B'}) == ['A']

    def test_duplicate_values_accepts_a_sound_map(self):
        assert duplicate_values({0x01: 'A', 0x02: 'B'}) == []
        assert duplicate_values(PadUnderTest.BUTTON_NAMES) == []
        assert duplicate_values(PadUnderTest.AXIS_NAMES) == []

    def test_duplicate_literal_keys_finds_a_repeated_key(self):
        class PadWithDuplicateKeys:
            BUTTON_NAMES = {
                0x13A: 'L3',
                0x13B: 'R3',
                0x13A: 'share',  # noqa: F601 - the defect under test
                0x13B: 'options',  # noqa: F601
            }

        # the duplicate is already gone from the dict itself
        assert len(PadWithDuplicateKeys.BUTTON_NAMES) == 2
        # but it is still visible in the source
        assert duplicate_literal_keys(PadWithDuplicateKeys) == ['314', '315']

    def test_duplicate_literal_keys_accepts_a_sound_map(self):
        assert duplicate_literal_keys(PadUnderTest) == []
