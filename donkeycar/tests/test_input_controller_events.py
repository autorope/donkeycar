#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

import pytest

from donkeycar.memory import Memory
from donkeycar.parts.controls import ControlChange
from donkeycar.parts.controls.events import (
    BUTTON_DOWN,
    BUTTON_HOLD,
    BUTTON_UP,
    InputControllerEvents,
    format_axis_event,
    format_axis_key,
    format_button_click_event,
    format_button_event,
    format_button_key,
)
from donkeycar.tests.fake_js import FakeClock, FakeInputController

FAST_CLICK = 0.2
LONG_PRESS = 0.5

# Step clearly past a threshold rather than exactly onto it: the clock
# accumulates float error, so `advance(FAST_CLICK)` lands a hair short and
# an exact-boundary assertion would be testing float equality, not
# behaviour.  Real presses never land on the boundary either.
BURST_ENDED = FAST_CLICK * 2
HELD_LONG_ENOUGH = LONG_PRESS * 2

PRESS_A = ControlChange(button='A', button_state=1)
RELEASE_A = ControlChange(button='A', button_state=0)
PRESS_B = ControlChange(button='B', button_state=1)
RELEASE_B = ControlChange(button='B', button_state=0)

A_PRESS = format_button_event('A', BUTTON_DOWN)
A_RELEASE = format_button_event('A', BUTTON_UP)
A_HOLD = format_button_event('A', BUTTON_HOLD)
A_STATE = format_button_key('A')


def a_click(count: int) -> str:
    return format_button_click_event('A', count)


class EventsFixture:
    """
    A part wired to a hand-driven clock, plus the two calls the vehicle loop
    would make: poll() on the background thread, run_threaded() on the main
    one.
    """

    def __init__(self, defer_clicks=True, **kwargs):
        self.memory = Memory()
        self.clock = FakeClock()
        self.controller = FakeInputController()
        self.part = InputControllerEvents(
            memory=self.memory,
            controller=self.controller,
            fast_click_time=FAST_CLICK,
            long_press_time=LONG_PRESS,
            defer_clicks=defer_clicks,
            clock=self.clock,
            sleep=self.clock.sleep,
            **kwargs,
        )

    def send(self, *changes: ControlChange) -> None:
        """
        Deliver state changes as the polling thread would.
        """
        self.controller.changes.extend(changes)
        for _ in changes:
            self.part.poll()

    def tick(self) -> None:
        """
        One pass through the vehicle loop.
        """
        self.part.run_threaded()

    def keys(self) -> set[str]:
        return set(self.memory.keys())

    def events(self) -> set[str]:
        return {k for k in self.memory.keys() if k.startswith('/event/')}


class TestPressAndRelease(unittest.TestCase):

    def setUp(self):
        self.fix = EventsFixture()

    def test_press_publishes_a_press_event(self):
        self.fix.send(PRESS_A)
        self.fix.tick()

        assert self.fix.memory[A_PRESS] == 0.0

    def test_press_event_value_is_the_time_it_happened(self):
        self.fix.clock.advance(12.5)
        self.fix.send(PRESS_A)
        self.fix.tick()

        assert self.fix.memory[A_PRESS] == 12.5

    def test_release_publishes_a_release_event(self):
        self.fix.send(PRESS_A)
        self.fix.tick()
        self.fix.send(RELEASE_A)
        self.fix.tick()

        assert A_RELEASE in self.fix.keys()

    def test_press_publishes_persistent_button_state(self):
        self.fix.send(PRESS_A)
        self.fix.tick()
        assert self.fix.memory[A_STATE] == 1

        self.fix.send(RELEASE_A)
        self.fix.tick()
        assert self.fix.memory[A_STATE] == 0

    def test_button_state_persists_across_loops(self):
        """
        Unlike the events, state stays put so a part can use one button as a
        modifier for another -- the 'hold X while clicking B' gesture.
        """
        self.fix.send(PRESS_A)
        self.fix.tick()
        self.fix.tick()
        self.fix.tick()

        assert self.fix.memory[A_STATE] == 1

    def test_events_last_exactly_one_pass(self):
        self.fix.send(PRESS_A)
        self.fix.tick()
        assert A_PRESS in self.fix.keys()

        self.fix.tick()
        assert A_PRESS not in self.fix.keys()

    def test_repeated_button_state_is_ignored(self):
        self.fix.send(PRESS_A, PRESS_A)
        self.fix.tick()

        assert self.fix.events() == {A_PRESS}

    def test_buttons_are_tracked_independently(self):
        self.fix.send(PRESS_A, PRESS_B)
        self.fix.tick()

        assert self.fix.memory[A_STATE] == 1
        assert self.fix.memory[format_button_key('B')] == 1

    def test_no_events_when_nothing_happened(self):
        self.fix.tick()
        assert self.fix.keys() == set()


class TestDeferredClicks(unittest.TestCase):
    """
    A click is held back until the burst of clicks has ended, so a
    double-click does not also fire every single-click behavior on its way
    through.
    """

    def setUp(self):
        self.fix = EventsFixture()

    def click(self, gap: float = 0.0) -> None:
        self.fix.clock.advance(gap)
        self.fix.send(PRESS_A)
        self.fix.clock.advance(0.05)
        self.fix.send(RELEASE_A)

    def test_click_is_not_published_on_release(self):
        self.click()
        self.fix.tick()

        assert A_RELEASE in self.fix.keys()
        assert a_click(1) not in self.fix.keys()

    def test_click_is_not_published_partway_through_the_window(self):
        self.click()
        self.fix.tick()
        self.fix.clock.advance(FAST_CLICK / 2)
        self.fix.tick()

        assert a_click(1) not in self.fix.keys()

    def test_click_is_published_once_the_burst_ends(self):
        self.click()
        self.fix.tick()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(1) in self.fix.keys()

    def test_click_value_is_the_release_time(self):
        """
        The value is when the click completed, not when the loop noticed.
        """
        self.click()
        released_at = self.fix.clock.now
        self.fix.tick()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert self.fix.memory[a_click(1)] == released_at

    def test_double_click_publishes_only_the_double(self):
        self.click()
        self.fix.tick()
        self.click(gap=0.05)
        self.fix.tick()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(2) in self.fix.keys()
        assert a_click(1) not in self.fix.keys()

    def test_triple_click_publishes_only_the_triple(self):
        for _ in range(3):
            self.click(gap=0.05)
            self.fix.tick()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(3) in self.fix.keys()
        assert a_click(1) not in self.fix.keys()
        assert a_click(2) not in self.fix.keys()

    def test_slow_clicks_are_separate_single_clicks(self):
        self.click()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()
        assert a_click(1) in self.fix.keys()

        self.click(gap=1.0)
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()
        assert a_click(1) in self.fix.keys()
        assert a_click(2) not in self.fix.keys()

    def test_burst_resets_after_it_is_published(self):
        for _ in range(2):
            self.click(gap=0.05)
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()
        assert a_click(2) in self.fix.keys()

        self.click(gap=1.0)
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()
        assert a_click(1) in self.fix.keys()

    def test_click_resolves_without_any_new_device_event(self):
        """
        The click is published by the passage of time, so run_threaded()
        must resolve it even though the gamepad has gone quiet.
        """
        self.click()
        self.fix.tick()
        self.fix.clock.advance(BURST_ENDED)

        self.fix.tick()  # no send() in between
        assert a_click(1) in self.fix.keys()

    def test_a_late_press_does_not_extend_a_published_burst(self):
        """
        If the vehicle loop stalls past the window, the pending click still
        counts as finished and the next press starts a new burst.
        """
        self.click()
        self.fix.clock.advance(BURST_ENDED * 2)  # loop stalled; no tick
        self.click()
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(1) in self.fix.keys()
        assert a_click(2) not in self.fix.keys()


class TestImmediateClicks(unittest.TestCase):

    def setUp(self):
        self.fix = EventsFixture(defer_clicks=False)

    def test_click_is_published_on_release(self):
        self.fix.send(PRESS_A, RELEASE_A)
        self.fix.tick()

        assert a_click(1) in self.fix.keys()

    def test_double_click_publishes_both_clicks(self):
        self.fix.send(PRESS_A, RELEASE_A)
        self.fix.tick()
        self.fix.clock.advance(0.05)
        self.fix.send(PRESS_A, RELEASE_A)
        self.fix.tick()

        assert a_click(2) in self.fix.keys()

    def test_slow_clicks_are_separate_single_clicks(self):
        self.fix.send(PRESS_A, RELEASE_A)
        self.fix.tick()
        self.fix.clock.advance(1.0)
        self.fix.send(PRESS_A, RELEASE_A)
        self.fix.tick()

        assert a_click(1) in self.fix.keys()
        assert a_click(2) not in self.fix.keys()


class TestHold(unittest.TestCase):

    def setUp(self):
        self.fix = EventsFixture()

    def test_hold_is_published_once_the_press_is_long_enough(self):
        self.fix.send(PRESS_A)
        self.fix.tick()
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()

        assert A_HOLD in self.fix.keys()

    def test_hold_value_does_not_depend_on_when_the_loop_looks(self):
        self.fix.send(PRESS_A)
        pressed_at = self.fix.clock.now
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()

        assert self.fix.memory[A_HOLD] == pressed_at + LONG_PRESS

    def test_no_hold_before_the_long_press_time(self):
        self.fix.send(PRESS_A)
        self.fix.clock.advance(LONG_PRESS / 2)
        self.fix.tick()

        assert A_HOLD not in self.fix.keys()

    def test_hold_is_published_only_once(self):
        self.fix.send(PRESS_A)
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()
        assert A_HOLD in self.fix.keys()

        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()
        assert A_HOLD not in self.fix.keys()

    def test_a_short_press_publishes_no_hold(self):
        self.fix.send(PRESS_A)
        self.fix.clock.advance(LONG_PRESS / 2)
        self.fix.send(RELEASE_A)
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()

        assert A_HOLD not in self.fix.keys()

    def test_a_hold_is_not_also_a_click(self):
        """
        A long press is a gesture of its own, so a button bound to both
        hold and click must not fire both.
        """
        self.fix.send(PRESS_A)
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()
        self.fix.send(RELEASE_A)
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(1) not in self.fix.keys()

    def test_a_click_after_a_hold_starts_a_fresh_burst(self):
        self.fix.send(PRESS_A)
        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.tick()
        self.fix.send(RELEASE_A)
        self.fix.tick()

        self.fix.clock.advance(0.05)
        self.fix.send(PRESS_A)
        self.fix.clock.advance(0.05)
        self.fix.send(RELEASE_A)
        self.fix.clock.advance(BURST_ENDED)
        self.fix.tick()

        assert a_click(1) in self.fix.keys()
        assert a_click(2) not in self.fix.keys()

    def test_hold_still_publishes_press_and_release(self):
        self.fix.send(PRESS_A)
        self.fix.tick()
        assert A_PRESS in self.fix.keys()

        self.fix.clock.advance(HELD_LONG_ENOUGH)
        self.fix.send(RELEASE_A)
        self.fix.tick()
        assert A_RELEASE in self.fix.keys()
        assert A_HOLD in self.fix.keys()


class TestAxis(unittest.TestCase):

    def setUp(self):
        self.fix = EventsFixture()

    def test_axis_change_publishes_an_event(self):
        self.fix.send(ControlChange(axis='steer', axis_value=0.5))
        self.fix.tick()

        assert self.fix.memory[format_axis_event('steer')] == 0.5

    def test_axis_change_publishes_persistent_state(self):
        self.fix.send(ControlChange(axis='steer', axis_value=0.5))
        self.fix.tick()
        self.fix.tick()

        assert format_axis_event('steer') not in self.fix.keys()
        assert self.fix.memory[format_axis_key('steer')] == 0.5

    def test_unchanged_axis_publishes_nothing(self):
        self.fix.send(
            ControlChange(axis='steer', axis_value=0.5),
            ControlChange(axis='steer', axis_value=0.5),
        )
        self.fix.tick()
        self.fix.tick()

        assert self.fix.events() == set()

    def test_axis_can_return_to_zero(self):
        self.fix.send(ControlChange(axis='steer', axis_value=0.5))
        self.fix.tick()
        self.fix.send(ControlChange(axis='steer', axis_value=0.0))
        self.fix.tick()

        assert self.fix.memory[format_axis_key('steer')] == 0.0


class TestLifecycle(unittest.TestCase):

    def test_constructor_does_not_open_the_device(self):
        """
        Opening in the constructor would block assembling the vehicle on an
        unpaired gamepad, and fail the whole car if it never appeared.
        """
        controller = FakeInputController(init_results=[False] * 100)
        part = InputControllerEvents(memory=Memory(), controller=controller)

        assert controller.init_count == 0
        assert part.running is True

    def test_update_retries_until_the_device_is_ready(self):
        fix = EventsFixture()
        fix.controller.init_results = [False, False, True]

        def stop_after_init() -> None:
            fix.part.running = False

        fix.part.poll = stop_after_init  # end the loop on the first poll
        fix.part.update()

        assert fix.controller.init_count == 3
        assert fix.controller.showed_map is True
        assert fix.clock.slept == [1.0, 1.0]

    def test_update_gives_up_when_shut_down_while_waiting(self):
        fix = EventsFixture()
        fix.controller.init_results = [False] * 10
        fix.part.running = False
        fix.part.update()

        assert fix.controller.showed_map is False

    def test_shutdown_stops_polling_and_closes_the_device(self):
        fix = EventsFixture()
        fix.part.shutdown()

        assert fix.part.running is False
        assert fix.controller.closed is True

    def test_shutdown_expires_outstanding_events(self):
        fix = EventsFixture()
        fix.send(PRESS_A)
        fix.tick()
        fix.part.shutdown()

        assert A_PRESS not in fix.keys()

    def test_poll_after_shutdown_does_nothing(self):
        fix = EventsFixture()
        fix.part.shutdown()
        fix.send(PRESS_A)
        fix.tick()

        assert fix.keys() == set()


class TestFailureHandling(unittest.TestCase):

    def test_a_disconnected_device_stops_polling(self):
        fix = EventsFixture()
        fix.controller.poll_error = OSError('device disconnected')
        fix.part.poll()

        assert fix.part.running is False

    def test_keyboard_interrupt_is_not_swallowed(self):
        """
        Regression: a bare `except:` used to catch KeyboardInterrupt and
        silently stop the controller with nothing in the log.
        """
        fix = EventsFixture()
        fix.controller.poll_error = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            fix.part.poll()

    def test_update_logs_and_stops_on_an_unexpected_error(self):
        fix = EventsFixture()
        fix.controller.poll_error = ValueError('driver went sideways')

        fix.part.update()

        assert fix.part.running is False

    def test_update_does_not_swallow_keyboard_interrupt(self):
        fix = EventsFixture()
        fix.controller.poll_error = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            fix.part.update()


class TestEventOrdering(unittest.TestCase):

    def test_press_release_and_click_arrive_in_order(self):
        """
        The documented stream for a single click, as in issue #1097.
        """
        fix = EventsFixture()
        fix.send(PRESS_A)
        fix.clock.advance(0.05)
        fix.send(RELEASE_A)
        fix.tick()
        assert fix.events() == {A_PRESS, A_RELEASE}

        fix.clock.advance(BURST_ENDED)
        fix.tick()
        assert fix.events() == {a_click(1)}

    def test_a_burst_faster_than_the_loop_keeps_every_click(self):
        """
        Several presses can land between two run_threaded() calls.  Only the
        last press and release survive as events, which is why the click
        carries its count -- no click is lost.
        """
        fix = EventsFixture()
        for _ in range(3):
            fix.send(PRESS_A)
            fix.clock.advance(0.01)
            fix.send(RELEASE_A)
            fix.clock.advance(0.01)
        fix.clock.advance(BURST_ENDED)
        fix.tick()

        assert a_click(3) in fix.keys()
