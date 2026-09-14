#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import (
    PILOT_MODES,
    AutoRecordOnThrottle,
    EraseLastNRecords,
    ShowRecordCount,
    TogglePilotMode,
    ToggleRecording,
)


class FakeTub:
    def __init__(self, fail: bool = False) -> None:
        self.deleted: list[int] = []
        self.fail = fail

    def delete_last_n_records(self, n: int) -> None:
        if self.fail:
            raise OSError('tub is not writable')
        self.deleted.append(n)


class FakeRecordTracker:
    def __init__(self) -> None:
        self.last_num_rec_print = 99
        self.force_alert = 0


class TestTogglePilotMode(unittest.TestCase):

    def test_it_steps_through_the_modes_and_wraps(self):
        toggle = TogglePilotMode()

        assert toggle.run('user') == 'local_angle'
        assert toggle.run('local_angle') == 'local'
        assert toggle.run('local') == 'user'

    def test_it_reads_the_mode_rather_than_remembering_it(self):
        """
        Something else may have changed the mode -- the web interface, or a
        behavior that drops to manual -- and this has to step on from where
        the car actually is, not from where it last left it.
        """
        toggle = TogglePilotMode()

        assert toggle.run('user') == 'local_angle'
        assert toggle.run('user') == 'local_angle'

    def test_nothing_set_yet_gives_the_human_control(self):
        assert TogglePilotMode().run(None) == 'user'
        assert TogglePilotMode().run() == 'user'

    def test_an_unknown_mode_gives_the_human_control(self):
        """
        Better to hand the car back than to guess at a mode nobody set.
        """
        assert TogglePilotMode().run('something_else') == 'user'

    def test_the_modes_can_be_replaced(self):
        toggle = TogglePilotMode(modes=('user', 'local'))

        assert toggle.run('user') == 'local'
        assert toggle.run('local') == 'user'

    def test_the_first_mode_is_the_one_the_human_drives(self):
        assert PILOT_MODES[0] == 'user'


class TestToggleRecording(unittest.TestCase):

    def test_it_flips(self):
        assert ToggleRecording().run(False) is True
        assert ToggleRecording().run(True) is False

    def test_nothing_set_yet_starts_recording(self):
        assert ToggleRecording().run(None) is True
        assert ToggleRecording().run() is True

    def test_it_reads_the_value_rather_than_remembering_it(self):
        toggle = ToggleRecording()

        assert toggle.run(True) is False
        assert toggle.run(True) is False


class TestAutoRecordOnThrottle(unittest.TestCase):

    def test_it_records_while_driving(self):
        assert AutoRecordOnThrottle().run(0.5, 'user') is True

    def test_it_stops_recording_when_the_throttle_closes(self):
        auto = AutoRecordOnThrottle()

        assert auto.run(0.5, 'user') is True
        assert auto.run(0.0, 'user') is False

    def test_reverse_counts_as_driving(self):
        assert AutoRecordOnThrottle().run(-0.5, 'user') is True

    def test_throttle_inside_the_dead_zone_is_not_driving(self):
        auto = AutoRecordOnThrottle(dead_zone=0.1)

        assert auto.run(0.05, 'user') is False
        assert auto.run(0.5, 'user') is True

    def test_nothing_yet_is_not_driving(self):
        assert AutoRecordOnThrottle().run(None, None) is False
        assert AutoRecordOnThrottle().run() is False

    def test_it_does_not_record_the_pilot_driving_itself(self):
        """
        Recording the pilot's own output and training on it teaches the
        pilot to do what it already does.
        """
        auto = AutoRecordOnThrottle()

        assert auto.run(0.5, 'local') is False
        assert auto.run(0.5, 'local_angle') is False

    def test_recording_in_autopilot_can_be_asked_for(self):
        auto = AutoRecordOnThrottle(record_in_autopilot=True)
        assert auto.run(0.5, 'local') is True

    def test_no_mode_is_treated_as_the_human_driving(self):
        """
        A template that never sets a mode is a manually driven car.
        """
        assert AutoRecordOnThrottle().run(0.5, None) is True


class TestEraseLastNRecords(unittest.TestCase):

    def test_it_erases_the_asked_for_number(self):
        tub = FakeTub()
        EraseLastNRecords(tub, num_records=25).run()

        assert tub.deleted == [25]

    def test_it_erases_once_per_call(self):
        """
        It wants a one-pass run condition; on a held button this would take
        the whole tub in a couple of seconds.
        """
        tub = FakeTub()
        erase = EraseLastNRecords(tub, num_records=10)
        erase.run()
        erase.run()

        assert tub.deleted == [10, 10]

    def test_no_tub_is_not_a_crash(self):
        EraseLastNRecords(None).run()  # must not raise

    def test_a_failed_erase_does_not_stop_the_car(self):
        """
        Erasing is a convenience.  A car that is driving must not fall over
        because the tub could not be written.
        """
        EraseLastNRecords(FakeTub(fail=True)).run()  # must not raise


class TestShowRecordCount(unittest.TestCase):

    def test_it_asks_for_the_count_to_be_announced(self):
        tracker = FakeRecordTracker()
        ShowRecordCount(tracker).run()

        assert tracker.last_num_rec_print == 0
        assert tracker.force_alert == 1

    def test_no_tracker_is_not_a_crash(self):
        ShowRecordCount(None).run()  # must not raise


class TestTheTwoRecordingPartsDisagree(unittest.TestCase):
    """
    ToggleRecording and AutoRecordOnThrottle both write 'recording', so a
    template picks one.  The legacy part folded both into one object with a
    latch, and the manual toggle then silently did nothing whenever
    auto-record was on -- it logged a line and ignored the press.

    Keeping them separate makes the choice visible in the template instead
    of buried in a conditional, and these tests record what each does so the
    difference is not surprising.
    """

    def test_the_toggle_ignores_the_throttle(self):
        assert ToggleRecording().run(False) is True

    def test_the_automatic_one_ignores_the_button(self):
        auto = AutoRecordOnThrottle()
        assert auto.run(0.0, 'user') is False
        assert auto.run(0.0, 'user') is False
