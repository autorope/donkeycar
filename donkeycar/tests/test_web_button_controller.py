#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.memory import Memory
from donkeycar.parts.controls.device import NO_CHANGE
from donkeycar.parts.controls.events import (
    BUTTON_DOWN,
    BUTTON_UP,
    InputControllerEvents,
    format_button_click_event,
    format_button_event,
    format_button_key,
)
from donkeycar.parts.controls.web import WebButtonController
from donkeycar.tests.fake_js import FakeClock


def drain(controller: WebButtonController) -> list:
    changes = []
    while (change := controller.poll()) != NO_CHANGE:
        changes.append(change)
    return changes


class TestPushesBecomeChanges(unittest.TestCase):

    def setUp(self):
        self.controller = WebButtonController(poll_timeout=0.0)

    def test_a_push_is_a_press(self):
        self.controller.run({'w1': True})
        change = self.controller.poll()

        assert change.button == 'web_w1'
        assert change.button_state == 1

    def test_the_web_interface_clearing_the_latch_is_a_release(self):
        """
        The web controller latches a push true and clears it on the next
        pass, so one push arrives here as a press and then a release.
        """
        self.controller.run({'w1': True})
        assert self.controller.poll().button_state == 1

        self.controller.run({'w1': False})
        assert self.controller.poll().button_state == 0

    def test_a_button_dropping_out_of_the_dictionary_is_released(self):
        """
        The web controller stops reporting a button once it has cleared it.
        Treating a missing button as still pushed would leave it held down
        for the rest of the drive.
        """
        self.controller.run({'w1': True})
        assert self.controller.poll().button_state == 1

        self.controller.run({})
        assert self.controller.poll().button_state == 0

    def test_nothing_pushed_is_no_change(self):
        self.controller.run({})
        assert self.controller.poll() == NO_CHANGE

    def test_no_buttons_at_all_is_no_change(self):
        self.controller.run(None)
        assert self.controller.poll() == NO_CHANGE

    def test_an_unchanged_push_reports_once(self):
        self.controller.run({'w1': True})
        assert len(drain(self.controller)) == 1

        self.controller.run({'w1': True})
        assert self.controller.poll() == NO_CHANGE

    def test_several_buttons_pushed_together_are_all_reported(self):
        self.controller.run({'w1': True, 'w2': True, 'w3': True})
        pushed = {c.button for c in drain(self.controller)}

        assert pushed == {'web_w1', 'web_w2', 'web_w3'}

    def test_names_are_prefixed_so_they_cannot_clash_with_a_gamepad(self):
        self.controller.run({'a_button': True})
        assert self.controller.poll().button == 'web_a_button'

    def test_the_prefix_can_be_changed(self):
        controller = WebButtonController(prefix='ui/', poll_timeout=0.0)
        controller.run({'w1': True})
        assert controller.poll().button == 'ui/w1'


class TestDiscovery(unittest.TestCase):

    def test_nothing_is_known_before_a_push(self):
        controller = WebButtonController(poll_timeout=0.0)
        assert controller.button_map == ()
        assert controller.show_map() is True

    def test_buttons_are_remembered_once_pushed(self):
        controller = WebButtonController(poll_timeout=0.0)
        controller.run({'w1': True, 'w5': True})

        assert controller.button_map == ('web_w1', 'web_w5')


class TestLifecycle(unittest.TestCase):

    def test_it_needs_no_device_to_initialize(self):
        assert WebButtonController(poll_timeout=0.0).init() is True

    def test_shutdown_stops_it_reporting(self):
        controller = WebButtonController(poll_timeout=0.0)
        controller.shutdown()
        controller.run({'w1': True})

        assert controller.poll() == NO_CHANGE


class TestThroughTheEventPump(unittest.TestCase):
    """
    The point of the exercise: a web push produces the same events as a
    gamepad button, so a behavior binds to either without the template
    knowing which.
    """

    def setUp(self):
        self.memory = Memory()
        self.clock = FakeClock()
        self.controller = WebButtonController(poll_timeout=0.0)
        self.events = InputControllerEvents(
            memory=self.memory,
            controller=self.controller,
            fast_click_time=0.2,
            clock=self.clock,
            sleep=self.clock.sleep,
        )

    def pump(self) -> None:
        """
        One pass of the events thread, then one of the vehicle loop.  The
        thread would poll continuously; a few passes is plenty to drain
        what one push produces, and an empty queue returns at once.
        """
        for _ in range(8):
            self.events.poll()
        self.events.run_threaded()

    def push(self, name: str) -> None:
        self.controller.run({name: True})

    def release(self, name: str) -> None:
        self.controller.run({name: False})

    def test_a_push_publishes_a_press_event(self):
        self.push('w1')
        self.pump()

        assert format_button_event('web_w1', BUTTON_DOWN) in self.memory.keys()

    def test_a_push_and_clear_publishes_press_and_release(self):
        self.push('w1')
        self.pump()
        self.release('w1')
        self.pump()

        assert format_button_event('web_w1', BUTTON_UP) in self.memory.keys()

    def test_a_push_publishes_persistent_button_state(self):
        self.push('w1')
        self.pump()
        assert self.memory[format_button_key('web_w1')] == 1

        self.release('w1')
        self.pump()
        assert self.memory[format_button_key('web_w1')] == 0

    def test_a_push_becomes_a_click(self):
        self.push('w1')
        self.pump()
        self.release('w1')
        self.pump()

        self.clock.advance(0.5)
        self.pump()
        assert format_button_click_event('web_w1', 1) in self.memory.keys()

    def test_two_fast_pushes_become_a_double_click(self):
        for _ in range(2):
            self.push('w1')
            self.pump()
            self.clock.advance(0.02)
            self.release('w1')
            self.pump()
            self.clock.advance(0.02)

        self.clock.advance(0.5)
        self.pump()

        assert format_button_click_event('web_w1', 2) in self.memory.keys()
        assert format_button_click_event('web_w1', 1) not in self.memory.keys()

    def test_the_events_expire_like_any_other(self):
        self.push('w1')
        self.pump()
        assert format_button_event('web_w1', BUTTON_DOWN) in self.memory.keys()

        self.pump()
        assert format_button_event('web_w1', BUTTON_DOWN) not in self.memory.keys()
