#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
How complete.py wires StopVehicle, run through a real drive loop.

The template decides between a button gesture and an axis chord from what
the behavior map binds, and getting that wrong is not a button that does
nothing: a released trigger reads -1.0, which is true, so a chord wired the
button way stops the car on the first pass.
"""

import unittest

import donkeycar as dk
from donkeycar.parts.controls import mapping as behaviors
from donkeycar.parts.controls.events import format_axis_key, format_button_key
from donkeycar.parts.controls.factory import _press
from donkeycar.templates.complete import _add_stop_vehicle


class Config:
    def __init__(self, behavior_map) -> None:
        self.CONTROLLER_TYPE = 'custom'
        self.CONTROLLER_BEHAVIOR_MAP = behavior_map


TRIGGERS = {
    behaviors.STOP_VEHICLE: format_axis_key('right_trigger'),
    behaviors.STOP_VEHICLE_MODIFIER: format_axis_key('left_trigger'),
}

BUTTONS = {
    behaviors.STOP_VEHICLE: _press('xbox'),
    behaviors.STOP_VEHICLE_MODIFIER: format_button_key('view'),
}


def vehicle_for(behavior_map) -> dk.vehicle.Vehicle:
    V = dk.vehicle.Vehicle()
    _add_stop_vehicle(V, Config(behavior_map))
    return V


def one_pass(V, stop=None, modifier=None) -> None:
    """
    One pass of the loop, with the behaviors as BehaviorEventMapper would
    have published them.  It publishes nothing for an untouched control.
    """
    V.mem[behaviors.STOP_VEHICLE] = stop
    V.mem[behaviors.STOP_VEHICLE_MODIFIER] = modifier
    V.update_parts()


class TestBothTriggers(unittest.TestCase):

    def test_squeezing_both_stops_the_car(self):
        V = vehicle_for(TRIGGERS)

        one_pass(V, stop=1.0, modifier=1.0)

        assert V.on is False

    def test_released_triggers_do_not_stop_the_car(self):
        V = vehicle_for(TRIGGERS)

        one_pass(V, stop=-1.0, modifier=-1.0)

        assert V.on is True

    def test_one_trigger_does_not_stop_the_car(self):
        V = vehicle_for(TRIGGERS)

        one_pass(V, stop=1.0, modifier=-1.0)
        one_pass(V, stop=-1.0, modifier=1.0)

        assert V.on is True

    def test_either_order(self):
        for first in ('stop', 'modifier'):
            V = vehicle_for(TRIGGERS)
            one_pass(V, **{first: 1.0})
            assert V.on is True
            one_pass(V, stop=1.0, modifier=1.0)
            assert V.on is False, f'{first} first'

    def test_untouched_triggers_do_not_stop_the_car(self):
        V = vehicle_for(TRIGGERS)

        one_pass(V)

        assert V.on is True


class TestButtonGesture(unittest.TestCase):
    """
    The existing way, unchanged.
    """

    def test_press_while_holding_stops_the_car(self):
        V = vehicle_for(BUTTONS)

        one_pass(V, stop=12.5, modifier=1)

        assert V.on is False

    def test_press_without_holding_does_not(self):
        V = vehicle_for(BUTTONS)

        one_pass(V, stop=12.5, modifier=0)

        assert V.on is True


class TestUnbound(unittest.TestCase):

    def test_nothing_bound_adds_nothing(self):
        V = vehicle_for({behaviors.STEERING: format_axis_key('left_stick_horz')})

        assert V.parts == []


if __name__ == '__main__':
    unittest.main()
