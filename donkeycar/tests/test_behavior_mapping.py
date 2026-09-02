#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.memory import Memory
from donkeycar.parts.controls.events import (
    BUTTON_DOWN,
    InputControllerEvents,
    format_axis_event,
    format_button_event,
    format_button_key,
)
from donkeycar.parts.controls.mapping import (
    KNOWN_BEHAVIORS,
    STEERING,
    TOGGLE_PILOT_MODE,
    TOGGLE_RECORDING,
    BehaviorEventMapper,
)
from donkeycar.parts.controls.device import ControlChange
from donkeycar.tests.fake_js import FakeClock, FakeInputController


class TestTranslating(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.mapper = BehaviorEventMapper(
            self.memory,
            {TOGGLE_RECORDING: '/event/button/circle/press'},
        )

    def test_a_control_event_publishes_its_behavior(self):
        self.memory['/event/button/circle/press'] = 12.5
        self.mapper.run()

        assert self.memory[TOGGLE_RECORDING] == 12.5

    def test_nothing_happening_publishes_nothing(self):
        self.mapper.run()
        assert TOGGLE_RECORDING not in self.memory.keys()

    def test_the_value_is_carried_across_unchanged(self):
        """
        So a behavior means exactly what the control meant, and a part can
        take one as both its input and its run condition.
        """
        mapper = BehaviorEventMapper(
            self.memory, {STEERING: format_axis_event('left_stick_horz')}
        )
        self.memory[format_axis_event('left_stick_horz')] = -0.75
        mapper.run()

        assert self.memory[STEERING] == -0.75


class TestOneShotBehavior(unittest.TestCase):
    """
    A behavior must last exactly as long as what caused it: a one-shot
    event drives a one-shot behavior, and a persistent state drives a
    persistent one.  Otherwise a part bound to a behavior would fire on
    every pass after the button was let go.
    """

    def setUp(self):
        self.memory = Memory()
        self.mapper = BehaviorEventMapper(
            self.memory, {TOGGLE_RECORDING: '/event/button/circle/press'}
        )

    def test_the_behavior_goes_when_the_event_goes(self):
        self.memory['/event/button/circle/press'] = 12.5
        self.mapper.run()
        assert TOGGLE_RECORDING in self.memory.keys()

        self.memory.remove(['/event/button/circle/press'])
        self.mapper.run()
        assert TOGGLE_RECORDING not in self.memory.keys()

    def test_a_persistent_control_drives_a_persistent_behavior(self):
        mapper = BehaviorEventMapper(
            self.memory, {TOGGLE_RECORDING: format_button_key('circle')}
        )
        self.memory[format_button_key('circle')] = 1

        mapper.run()
        assert self.memory[TOGGLE_RECORDING] == 1

        mapper.run()
        assert self.memory[TOGGLE_RECORDING] == 1

    def test_shutdown_takes_the_behaviors_with_it(self):
        self.memory['/event/button/circle/press'] = 12.5
        self.mapper.run()
        self.mapper.shutdown()

        assert TOGGLE_RECORDING not in self.memory.keys()


class TestSeveralControlsOneBehavior(unittest.TestCase):
    """
    The case the templates handle today by writing every binding twice,
    once for the gamepad and once for the web UI.
    """

    def setUp(self):
        self.memory = Memory()
        self.mapper = BehaviorEventMapper(
            self.memory,
            {
                TOGGLE_RECORDING: [
                    '/event/button/circle/press',
                    '/event/button/web_w1/press',
                ]
            },
        )

    def test_either_control_publishes_the_behavior(self):
        self.memory['/event/button/circle/press'] = 1.0
        self.mapper.run()
        assert self.memory[TOGGLE_RECORDING] == 1.0

        self.memory.remove(['/event/button/circle/press'])
        self.memory['/event/button/web_w1/press'] = 2.0
        self.mapper.run()
        assert self.memory[TOGGLE_RECORDING] == 2.0

    def test_both_at_once_publishes_the_behavior_once(self):
        """
        Someone pressing both is asking for the behavior, not for it twice.
        """
        self.memory['/event/button/circle/press'] = 1.0
        self.memory['/event/button/web_w1/press'] = 2.0
        self.mapper.run()

        assert self.memory[TOGGLE_RECORDING] == 1.0

    def test_one_control_can_drive_several_behaviors(self):
        memory = Memory()
        mapper = BehaviorEventMapper(
            memory,
            {
                TOGGLE_RECORDING: '/event/button/circle/press',
                TOGGLE_PILOT_MODE: '/event/button/circle/press',
            },
        )
        memory['/event/button/circle/press'] = 1.0
        mapper.run()

        assert memory[TOGGLE_RECORDING] == 1.0
        assert memory[TOGGLE_PILOT_MODE] == 1.0


class TestCheckingAMap(unittest.TestCase):

    def test_a_typo_is_reported(self):
        mapper = BehaviorEventMapper(
            Memory(), {'/behavior/togle_recording': '/event/button/circle/press'}
        )
        assert mapper.unknown_behaviors() == ('/behavior/togle_recording',)

    def test_a_sound_map_reports_nothing_unknown(self):
        mapper = BehaviorEventMapper(
            Memory(), {TOGGLE_RECORDING: '/event/button/circle/press'}
        )
        assert mapper.unknown_behaviors() == ()

    def test_behaviors_left_unbound_are_reported(self):
        """
        Not an error -- a pad with eight buttons cannot drive twenty
        behaviors -- but worth being able to see.
        """
        mapper = BehaviorEventMapper(
            Memory(), {TOGGLE_RECORDING: '/event/button/circle/press'}
        )
        unbound = mapper.unbound_behaviors()

        assert TOGGLE_PILOT_MODE in unbound
        assert TOGGLE_RECORDING not in unbound

    def test_show_map_works_with_no_bindings(self):
        BehaviorEventMapper(Memory(), {}).show_map()  # must not raise

    def test_the_bindings_are_readable(self):
        mapper = BehaviorEventMapper(
            Memory(), {TOGGLE_RECORDING: '/event/button/circle/press'}
        )
        assert mapper.bindings == {
            TOGGLE_RECORDING: ('/event/button/circle/press',)
        }
        mapper.show_map()

    def test_every_known_behavior_is_under_the_behavior_prefix(self):
        assert all(b.startswith('/behavior/') for b in KNOWN_BEHAVIORS)


class TestThroughTheWholeChain(unittest.TestCase):
    """
    A button on a controller, through the event pump, through the map, to
    the behavior a template binds to.  Each piece is tested on its own;
    this checks they actually join up.
    """

    def setUp(self):
        self.memory = Memory()
        self.clock = FakeClock()
        self.controller = FakeInputController()
        self.events = InputControllerEvents(
            memory=self.memory,
            controller=self.controller,
            clock=self.clock,
            sleep=self.clock.sleep,
        )
        self.mapper = BehaviorEventMapper(
            self.memory,
            {
                TOGGLE_RECORDING: format_button_event('circle', BUTTON_DOWN),
                STEERING: format_axis_event('left_stick_horz'),
            },
        )

    def pump(self) -> None:
        for _ in range(4):
            self.events.poll()
        self.events.run_threaded()
        self.mapper.run()

    def test_a_button_press_reaches_its_behavior(self):
        self.controller.changes.append(
            ControlChange(button='circle', button_state=1)
        )
        self.pump()

        assert TOGGLE_RECORDING in self.memory.keys()

    def test_an_axis_move_reaches_its_behavior_with_its_value(self):
        self.controller.changes.append(
            ControlChange(axis='left_stick_horz', axis_value=-0.5)
        )
        self.pump()

        assert self.memory[STEERING] == -0.5

    def test_the_behavior_expires_with_the_event(self):
        self.controller.changes.append(
            ControlChange(button='circle', button_state=1)
        )
        self.pump()
        assert TOGGLE_RECORDING in self.memory.keys()

        self.pump()
        assert TOGGLE_RECORDING not in self.memory.keys()

    def test_a_control_nothing_is_bound_to_reaches_no_behavior(self):
        self.controller.changes.append(
            ControlChange(button='triangle', button_state=1)
        )
        self.pump()

        assert format_button_event('triangle', BUTTON_DOWN) in self.memory.keys()
        assert TOGGLE_RECORDING not in self.memory.keys()

    def test_a_different_pad_needs_only_a_different_map(self):
        """
        The point of the exercise: the template binds to the behavior, and
        which control drives it is a line in myconfig.py.
        """
        memory = Memory()
        clock = FakeClock()
        controller = FakeInputController(
            [ControlChange(button='b_button', button_state=1)]
        )
        events = InputControllerEvents(
            memory=memory, controller=controller, clock=clock, sleep=clock.sleep
        )
        mapper = BehaviorEventMapper(
            memory,
            {TOGGLE_RECORDING: format_button_event('b_button', BUTTON_DOWN)},
        )

        for _ in range(4):
            events.poll()
        events.run_threaded()
        mapper.run()

        assert TOGGLE_RECORDING in memory.keys()
