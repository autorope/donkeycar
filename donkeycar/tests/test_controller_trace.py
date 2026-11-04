#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The opt-in controller trace: the switch, and what the event pump logs.
"""
import logging

import pytest

from donkeycar.memory import Memory
from donkeycar.parts.controls import ControlChange
from donkeycar.parts.controls.events import InputControllerEvents
from donkeycar.parts.controls.trace import (
    TRACE_ENV,
    TRACE_LOGGER,
    trace_enabled,
)
from donkeycar.tests.fake_js import FakeClock, FakeInputController

FAST_CLICK = 0.2
LONG_PRESS = 0.5


@pytest.fixture
def trace_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TRACE_ENV, '1')


@pytest.fixture
def trace_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TRACE_ENV, raising=False)


def trace_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == TRACE_LOGGER]


class Pump:
    """
    An event pump on a hand-driven clock, constructed after the test has
    set the environment, as a car would be.
    """

    def __init__(self, defer_clicks: bool = True) -> None:
        self.clock = FakeClock()
        self.controller = FakeInputController()
        self.part = InputControllerEvents(
            memory=Memory(),
            controller=self.controller,
            fast_click_time=FAST_CLICK,
            long_press_time=LONG_PRESS,
            defer_clicks=defer_clicks,
            clock=self.clock,
            sleep=self.clock.sleep,
        )

    def send(self, *changes: ControlChange) -> None:
        self.controller.changes.extend(changes)
        for _ in changes:
            self.part.poll()

    def press(self, button: str) -> None:
        self.send(ControlChange(button=button, button_state=1))

    def release(self, button: str) -> None:
        self.send(ControlChange(button=button, button_state=0))


# --- the switch ---------------------------------------------------------

@pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'yes', 'Yes', 'on',
                                   ' on '])
def test_these_spellings_turn_it_on(monkeypatch, value):
    monkeypatch.setenv(TRACE_ENV, value)
    assert trace_enabled()


@pytest.mark.parametrize('value', ['', '0', 'false', 'no', 'off', 'debug'])
def test_anything_else_leaves_it_off(monkeypatch, value):
    monkeypatch.setenv(TRACE_ENV, value)
    assert not trace_enabled()


def test_it_is_off_by_default(trace_off):
    assert not trace_enabled()


# --- the pad layer ------------------------------------------------------

def test_an_axis_move_is_logged(trace_on, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    pump.send(ControlChange(axis='left_stick_horz', axis_value=-0.53125))
    assert trace_lines(caplog) == ['axis left_stick_horz -0.531']


def test_an_unchanged_axis_logs_nothing_more(trace_on, caplog):
    """
    The pump drops a repeated value, so the trace does too: a pad that
    repeats its idle reading must not fill the console.
    """
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    move = ControlChange(axis='left_stick_horz', axis_value=0.5)
    pump.send(move, move, move)
    assert trace_lines(caplog) == ['axis left_stick_horz 0.500']


def test_press_and_release_are_logged(trace_on, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump(defer_clicks=False)
    pump.press('cross')
    pump.release('cross')
    assert trace_lines(caplog) == [
        'button cross press',
        'button cross release',
        'button cross click x1',
    ]


def test_a_deferred_double_click_is_logged_once_with_its_count(
        trace_on, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    pump.press('cross')
    pump.release('cross')
    pump.press('cross')
    pump.release('cross')
    pump.clock.advance(FAST_CLICK * 2)
    pump.part.run_threaded()
    clicks = [line for line in trace_lines(caplog) if 'click' in line]
    assert clicks == ['button cross click x2']


def test_a_hold_is_logged(trace_on, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    pump.press('cross')
    pump.clock.advance(LONG_PRESS * 2)
    pump.part.run_threaded()
    assert trace_lines(caplog) == ['button cross press', 'button cross hold']


def test_losing_the_controller_is_logged(trace_on, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    pump.controller.poll_error = OSError('device disconnected')
    pump.part.poll()
    assert trace_lines(caplog) == ['controller lost']


def test_nothing_is_logged_when_off(trace_off, caplog):
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    pump.send(ControlChange(axis='left_stick_horz', axis_value=0.5))
    pump.press('cross')
    pump.clock.advance(LONG_PRESS * 2)
    pump.part.run_threaded()
    pump.release('cross')
    pump.controller.poll_error = OSError('device disconnected')
    pump.part.poll()
    assert trace_lines(caplog) == []


def test_the_switch_is_read_at_construction(trace_off, monkeypatch, caplog):
    """
    Read once, not per event: turning it on later does nothing to a part
    already built.
    """
    caplog.set_level(logging.INFO, logger=TRACE_LOGGER)
    pump = Pump()
    monkeypatch.setenv(TRACE_ENV, '1')
    pump.send(ControlChange(axis='left_stick_horz', axis_value=0.5))
    assert trace_lines(caplog) == []
