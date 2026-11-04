#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import unittest
from collections.abc import Iterable

from donkeycar.parts.controls.capture import (
    Control,
    Movement,
    capture_step,
    run_capture,
)
from donkeycar.parts.controls.linux import (
    JS_EVENT_AXIS,
    JS_EVENT_INIT,
    JsEvent,
)
from donkeycar.tests.fake_js import (
    FakeClock,
    FakeJsDevice,
    axis_event,
    button_event,
)

# The Bluetooth Xbox layout, which is what this tool was written to measure.
AXIS_CODES = (0x00, 0x01, 0x02, 0x05, 0x09, 0x0A)
BUTTON_CODES = (0x130, 0x131)


class TickingClock(FakeClock):
    """
    A clock that moves on every reading, so a loop that waits for a window
    to close does close, without any real waiting.
    """

    def __call__(self) -> float:
        self.now += 0.01
        return self.now


class LateDevice(FakeJsDevice):
    """
    A device that is quiet for one read before its events arrive, the way a
    real pad is between the person pressing Enter and touching the control.
    Without that pause, a step's opening drain would discard them.
    """

    def __init__(self, events: Iterable[JsEvent] = (),
                 initial: Iterable[JsEvent] = ()) -> None:
        super().__init__(axis_codes=AXIS_CODES, button_codes=BUTTON_CODES,
                         events=initial)
        self.late = list(events)

    def read_event(self) -> JsEvent | None:
        if not self.events and self.late:
            self.events, self.late = self.late, []
            return None
        return super().read_event()


class ScriptedDevice(LateDevice):
    """
    A device whose events arrive in batches, one batch per capture step,
    the way a person works one control after pressing Enter.  Anything left
    over from a step is gone by the next, as it would be on a real pad.
    """

    def __init__(self, steps: Iterable[Iterable[JsEvent]],
                 initial: Iterable[JsEvent] = ()) -> None:
        super().__init__(initial=initial)
        self.steps = [list(step) for step in steps]

    def next_step(self) -> None:
        self.events = []
        self.late = self.steps.pop(0) if self.steps else []


def axis_init(number: int, value: int) -> JsEvent:
    return JsEvent(time=0, value=value, type=JS_EVENT_AXIS | JS_EVENT_INIT,
                   number=number)


def scripted_person(device: ScriptedDevice, answers: Iterable[str]):
    """
    An ask() that gives the scripted answers in turn, and releases the
    device's next batch of events whenever a step starts.
    """
    remaining = list(answers)
    prompts: list[str] = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        answer = remaining.pop(0)
        if 'Enter to start' in prompt and answer == '':
            device.next_step()
        return answer

    return ask, prompts


class TestCaptureStep(unittest.TestCase):

    def test_records_the_range_each_code_moved(self) -> None:
        device = LateDevice([axis_event(4, -32767), axis_event(4, 32767),
                             axis_event(4, -32767)])
        info = device.open()

        moved = capture_step(device, info, TickingClock(), window=1.0)

        # index 4 is code 0x09, the right trigger over Bluetooth
        assert moved == {'axis 0x9': Movement(events=3, min=-1.0, max=1.0)}

    def test_the_control_asked_for_is_listed_first(self) -> None:
        """
        A stick sweep nudges its neighbouring axis, so a step reports both;
        the one that travelled furthest is the one that was asked for.
        """
        device = LateDevice([axis_event(1, 8000), axis_event(0, -32767),
                             axis_event(0, 32767), axis_event(1, 0)])
        info = device.open()

        moved = capture_step(device, info, TickingClock(), window=1.0)

        assert list(moved) == ['axis 0x0', 'axis 0x1']

    def test_ignores_init_events_and_undeclared_indexes(self) -> None:
        device = LateDevice([axis_init(0, 0), button_event(9, 1)])
        info = device.open()

        assert capture_step(device, info, TickingClock(), window=1.0) == {}

    def test_discards_what_moved_before_the_step_began(self) -> None:
        """
        Fiddling with the pad while reading the prompt is not the control
        being asked for.
        """
        device = LateDevice([button_event(0, 1)],
                            initial=[axis_event(0, 32767)])
        info = device.open()

        moved = capture_step(device, info, TickingClock(), window=1.0)

        assert list(moved) == ['button 0x130']


class TestRunCapture(unittest.TestCase):

    CONTROLS = (
        Control('right_trigger', 'squeeze it'),
        Control('a_button', 'press it'),
    )

    def run_with(self, steps, answers, initial=()):
        device = ScriptedDevice(steps, initial=initial)
        ask, prompts = scripted_person(device, answers)
        said: list[str] = []
        result = run_capture(device, ask=ask, say=said.append,
                             clock=TickingClock(), controls=self.CONTROLS,
                             window=1.0)
        return result, prompts, said

    def test_records_each_control(self) -> None:
        result, _, _ = self.run_with(
            steps=[[axis_event(4, 32767)], [button_event(0, 1)]],
            answers=['', '', '', ''])

        assert list(result.controls['right_trigger']) == ['axis 0x9']
        assert list(result.controls['a_button']) == ['button 0x130']

    def test_resting_values_come_from_the_initial_state(self) -> None:
        result, _, _ = self.run_with(
            steps=[], answers=['s', 's'],
            initial=[axis_init(0, 0), axis_init(4, -32767)])

        assert result.axis_rest == {'0x0': 0.0, '0x9': -1.0}

    def test_skip(self) -> None:
        result, _, _ = self.run_with(
            steps=[[button_event(0, 1)]], answers=['s', '', ''])

        assert result.controls['right_trigger'] == 'skipped'
        assert list(result.controls['a_button']) == ['button 0x130']

    def test_redo_repeats_the_step_and_keeps_only_the_retry(self) -> None:
        """
        The person pressed the wrong control first time.  Redo asks for the
        same control again, and the fumbled attempt is not recorded.
        """
        result, prompts, _ = self.run_with(
            steps=[[button_event(0, 1)],          # wrong: A, not the trigger
                   [axis_event(4, 32767)],        # retry: the trigger
                   [button_event(0, 1)]],
            answers=['', 'r', '', '', '', ''])

        assert list(result.controls['right_trigger']) == ['axis 0x9']
        assert list(result.controls['a_button']) == ['button 0x130']
        starts = [p for p in prompts if 'Enter to start' in p]
        assert [p.split(']')[0] for p in starts] == [
            '[right_trigger', '[right_trigger', '[a_button']

    def test_redo_more_than_once(self) -> None:
        result, _, _ = self.run_with(
            steps=[[], [button_event(1, 1)], [axis_event(4, 32767)],
                   [button_event(0, 1)]],
            answers=['', 'r', '', 'r', '', '', '', ''])

        assert list(result.controls['right_trigger']) == ['axis 0x9']

    def test_redo_is_offered_after_every_step(self) -> None:
        _, prompts, _ = self.run_with(
            steps=[[], []], answers=['', '', '', ''])

        assert sum('r to redo' in p for p in prompts) == 2

    def test_saves_as_json(self) -> None:
        result, _, _ = self.run_with(
            steps=[[axis_event(4, 32767)]], answers=['', '', 's'])

        saved = json.loads(result.to_json())
        assert saved['device'] == 'Fake Gamepad'
        assert saved['axis_codes'][4] == '0x9'
        assert saved['controls']['right_trigger']['axis 0x9'] == {
            'events': 1, 'min': 1.0, 'max': 1.0}
        assert saved['controls']['a_button'] == 'skipped'


if __name__ == '__main__':
    unittest.main()
