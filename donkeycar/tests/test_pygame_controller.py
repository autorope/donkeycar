#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.device import NO_CHANGE
from donkeycar.parts.controls.gamepads import PS4Joystick
from donkeycar.parts.controls.pygame_device import (
    PyGameController,
    PyGamePS4Joystick,
)
from donkeycar.tests.fake_js import GamepadMapChecks
from donkeycar.tests.fake_pygame import FakePyGameDevice


def drain(pad: PyGameController) -> list:
    """Everything one scan produced, in order."""
    changes = []
    while (change := pad.poll()) != NO_CHANGE:
        changes.append(change)
    return changes


class TestScanning(unittest.TestCase):
    """
    PyGame reports where controls are, not what moved, so the controller has
    to notice changes itself.
    """

    def setUp(self):
        self.device = FakePyGameDevice(num_axes=4, num_buttons=4, num_hats=1)
        self.pad = PyGameController(device=self.device)
        self.pad.init()

    def test_nothing_moved_is_no_change(self):
        assert self.pad.poll() == NO_CHANGE

    def test_an_axis_move_is_reported(self):
        self.device.set_axis(0, 0.5)
        change = self.pad.poll()

        assert change.axis == 'axis(0)'
        assert change.axis_value == 0.5

    def test_a_button_press_is_reported(self):
        self.device.set_button(2, 1)
        change = self.pad.poll()

        assert change.button == 'button(2)'
        assert change.button_state == 1

    def test_a_position_reported_twice_is_one_change(self):
        self.device.set_axis(0, 0.5)
        assert self.pad.poll().axis_value == 0.5
        assert self.pad.poll() == NO_CHANGE

    def test_the_event_queue_is_serviced_before_reading(self):
        """
        PyGame only refreshes device state when its event queue is pumped.
        """
        self.pad.poll()
        assert self.device.pump_count == 1


class TestNoChangeIsLost(unittest.TestCase):
    """
    Regression.  The legacy version scanned every control while overwriting
    one pair of return values, so when several moved together it reported
    the last and dropped the rest -- having already recorded their new
    positions, so they were never reported at all.  A stick moved
    diagonally changes two axes at once, so this happened constantly.
    """

    def setUp(self):
        self.device = FakePyGameDevice(num_axes=4, num_buttons=4, num_hats=1)
        self.pad = PyGameController(device=self.device)
        self.pad.init()

    def test_two_axes_moving_together_are_both_reported(self):
        self.device.set_axis(0, 0.5)
        self.device.set_axis(1, -0.5)

        moved = {(c.axis, c.axis_value) for c in drain(self.pad)}
        assert moved == {('axis(0)', 0.5), ('axis(1)', -0.5)}

    def test_a_diagonal_stick_keeps_both_halves(self):
        self.device.set_axis(0, 0.7)
        self.device.set_axis(1, 0.7)
        first = drain(self.pad)

        self.device.set_axis(0, -0.7)
        self.device.set_axis(1, -0.7)
        second = drain(self.pad)

        assert len(first) == 2
        assert len(second) == 2

    def test_buttons_and_axes_moving_together_are_all_reported(self):
        self.device.set_axis(0, 0.5)
        self.device.set_button(1, 1)
        self.device.set_button(3, 1)

        changes = drain(self.pad)
        assert len(changes) == 3

    def test_queued_changes_survive_across_polls(self):
        self.device.set_axis(0, 0.5)
        self.device.set_axis(1, 0.5)
        self.device.set_axis(2, 0.5)

        # one at a time, as the event pump would take them
        assert self.pad.poll().axis == 'axis(0)'
        assert self.pad.poll().axis == 'axis(1)'
        assert self.pad.poll().axis == 'axis(2)'
        assert self.pad.poll() == NO_CHANGE


class TestDeadZone(unittest.TestCase):

    def setUp(self):
        self.device = FakePyGameDevice(num_axes=2, num_buttons=0, num_hats=0)
        self.pad = PyGameController(device=self.device, dead_zone=0.07)
        self.pad.init()

    def test_movement_inside_the_dead_zone_reads_as_centred(self):
        self.device.set_axis(0, 0.05)
        assert self.pad.poll() == NO_CHANGE

    def test_movement_outside_the_dead_zone_reports(self):
        self.device.set_axis(0, 0.5)
        assert self.pad.poll().axis_value == 0.5

    def test_returning_to_the_dead_zone_reports_a_centred_axis(self):
        """
        Otherwise a stick released to a resting 0.03 would stay reported at
        whatever it last moved to.
        """
        self.device.set_axis(0, 0.5)
        assert self.pad.poll().axis_value == 0.5

        self.device.set_axis(0, 0.03)
        assert self.pad.poll().axis_value == 0.0


class TestHatsBecomeButtons(unittest.TestCase):
    """
    A hat reports a position rather than button presses, so each one is
    expanded into four pseudo-buttons numbered after the real ones.
    """

    def setUp(self):
        self.device = FakePyGameDevice(num_axes=0, num_buttons=4, num_hats=1)
        self.pad = PyGameController(device=self.device)
        self.pad.init()

    def test_the_hat_adds_four_buttons(self):
        assert len(self.pad.button_map) == 8

    def test_left_and_right(self):
        self.device.set_hat(0, (-1, 0))
        assert self.pad.poll().button == 'button(4)'  # left

        self.device.set_hat(0, (1, 0))
        changes = drain(self.pad)
        assert ('button(4)', 0) in [(c.button, c.button_state) for c in changes]
        assert ('button(5)', 1) in [(c.button, c.button_state) for c in changes]

    def test_down_and_up(self):
        self.device.set_hat(0, (0, -1))
        assert self.pad.poll().button == 'button(6)'  # down

        self.device.set_hat(0, (0, 0))
        assert self.pad.poll().button_state == 0

        self.device.set_hat(0, (0, 1))
        assert self.pad.poll().button == 'button(7)'  # up

    def test_a_diagonal_presses_two_directions(self):
        self.device.set_hat(0, (-1, 1))
        pressed = {c.button for c in drain(self.pad) if c.button_state == 1}

        assert pressed == {'button(4)', 'button(7)'}  # left and up


class TestNaming(unittest.TestCase):

    def test_unmapped_controls_use_their_index(self):
        device = FakePyGameDevice(num_axes=2, num_buttons=2, num_hats=0)
        pad = PyGameController(device=device)
        pad.init()

        assert pad.axis_map == ('axis(0)', 'axis(1)')
        assert pad.button_map == ('button(0)', 'button(1)')

    def test_caller_names_override_the_built_in_map(self):
        device = FakePyGameDevice(num_axes=4, num_buttons=14, num_hats=1)
        pad = PyGamePS4Joystick(device=device, button_names={1: 'renamed'})
        pad.init()

        assert pad.button_map[1] == 'renamed'
        assert pad.button_map[0] == 'square'

    def test_init_fails_when_pygame_has_no_pad(self):
        device = FakePyGameDevice(open_error=OSError('no joystick'))
        pad = PyGameController(device=device)

        assert pad.init() is False
        assert pad.poll() == NO_CHANGE

    def test_shutdown_closes_the_device(self):
        device = FakePyGameDevice()
        pad = PyGameController(device=device)
        pad.init()
        pad.shutdown()

        assert device.closed is True


class TestPS4MapIsSound(GamepadMapChecks, unittest.TestCase):
    PAD = PyGamePS4Joystick


class TestPS4MapIsIndexedNotCoded(unittest.TestCase):
    """
    The same controller as PS4Joystick, numbered by PyGame instead of by
    Linux input codes, so the two maps share no numbering whatever.  A map
    written for one is meaningless for the other.
    """

    def test_the_indices_are_small_not_input_codes(self):
        assert max(PyGamePS4Joystick.BUTTON_NAMES) < 0x100
        assert min(PS4Joystick.BUTTON_NAMES) >= 0x100

    def test_the_right_stick_is_at_different_numbers(self):
        assert PyGamePS4Joystick.AXIS_NAMES[2] == 'right_stick_horz'
        assert PyGamePS4Joystick.AXIS_NAMES[3] == 'right_stick_vert'

        assert PS4Joystick.AXIS_NAMES[2] == 'left_trigger'
        assert PS4Joystick.AXIS_NAMES[3] == 'right_stick_horz'

    def test_the_touchpad_is_a_button_here(self):
        """
        PyGame surfaces the touchpad click as an ordinary button.  The Linux
        driver does not -- there it is a separate input device that never
        reaches the joystick node -- which is why PS4Joystick has no name
        for it.
        """
        assert PyGamePS4Joystick.BUTTON_NAMES[13] == 'touchpad'
        assert 'touchpad' not in PS4Joystick.BUTTON_NAMES.values()

    def test_the_control_names_still_match_the_other_ps4_map(self):
        """
        Different numbering, same vocabulary, so a behavior map carries
        across even though the codes do not.
        """
        shared = set(PyGamePS4Joystick.BUTTON_NAMES.values()) & set(
            PS4Joystick.BUTTON_NAMES.values()
        )
        assert {'cross', 'circle', 'triangle', 'square'} <= shared
        assert {'share', 'options'} <= shared
        assert {'left_shoulder', 'right_shoulder'} <= shared
        assert {'left_stick_press', 'right_stick_press'} <= shared


class TestPS4Polling(unittest.TestCase):

    def setUp(self):
        self.device = FakePyGameDevice(num_axes=4, num_buttons=14, num_hats=1)
        self.pad = PyGamePS4Joystick(device=self.device)
        self.pad.init()

    def test_a_face_button_reports_by_name(self):
        self.device.set_button(1, 1)
        assert self.pad.poll().button == 'cross'

    def test_the_hat_reports_as_the_dpad(self):
        self.device.set_hat(0, (0, 1))
        assert self.pad.poll().button == 'dpad_up'

    def test_the_sticks_report_by_name(self):
        self.device.set_axis(2, 0.5)
        assert self.pad.poll().axis == 'right_stick_horz'
