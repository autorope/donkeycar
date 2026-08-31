#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.events import OneShotEvents
from donkeycar.memory import Memory


class TestOneShotEvents(unittest.TestCase):

    def setUp(self) -> None:
        self.mem = Memory()
        self.events = OneShotEvents(self.mem)

    def test_emit_publishes_to_memory(self) -> None:
        self.events.emit({'/event/button/Y/press': 1.5})
        assert self.mem['/event/button/Y/press'] == 1.5

    def test_emit_expires_the_previous_events(self) -> None:
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.emit({'/event/button/Y/release': 1.7})

        assert '/event/button/Y/press' not in self.mem.keys()
        assert self.mem['/event/button/Y/release'] == 1.7

    def test_empty_emit_expires_the_previous_events(self) -> None:
        """
        emit({}) is what expires a pass's events when nothing new happened,
        so a part must call emit() every loop, not only when it has events.
        """
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.emit({})

        assert '/event/button/Y/press' not in self.mem.keys()

    def test_event_survives_exactly_one_pass(self) -> None:
        self.events.emit({'/event/axis/steer': 0.25})
        # the whole loop runs here and every part sees the event
        assert self.mem['/event/axis/steer'] == 0.25
        self.events.emit({})
        assert '/event/axis/steer' not in self.mem.keys()

    def test_repeated_key_keeps_the_new_value(self) -> None:
        """
        A key emitted on consecutive passes must survive the expiry of the
        previous pass and hold the newer value.
        """
        self.events.emit({'/event/axis/steer': 0.25})
        self.events.emit({'/event/axis/steer': -0.5})

        assert self.mem['/event/axis/steer'] == -0.5

    def test_emit_multiple_events(self) -> None:
        self.events.emit({
            '/event/button/Y/press': 1.5,
            '/event/button/Y/release': 1.7,
            '/event/button/Y/click/1': 1.7,
        })
        assert self.mem['/event/button/Y/press'] == 1.5
        assert self.mem['/event/button/Y/release'] == 1.7
        assert self.mem['/event/button/Y/click/1'] == 1.7

        self.events.emit({})
        assert list(self.mem.keys()) == []

    def test_clear_expires_without_publishing(self) -> None:
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.clear()

        assert '/event/button/Y/press' not in self.mem.keys()
        assert self.events.emitted == ()

    def test_clear_is_idempotent(self) -> None:
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.clear()
        self.events.clear()

        assert list(self.mem.keys()) == []

    def test_emit_after_clear(self) -> None:
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.clear()
        self.events.emit({'/event/button/Y/release': 1.7})

        assert self.mem['/event/button/Y/release'] == 1.7
        assert self.events.emitted == ('/event/button/Y/release',)

    def test_expiry_tolerates_a_key_removed_by_someone_else(self) -> None:
        """
        Another part may legitimately have removed the key already; expiry
        must not raise.  This is why Memory.remove() ignores missing keys.
        """
        self.events.emit({'/event/button/Y/press': 1.5})
        self.mem.remove(['/event/button/Y/press'])

        self.events.emit({})  # must not raise

        assert list(self.mem.keys()) == []

    def test_emitted_reports_live_keys(self) -> None:
        assert self.events.emitted == ()

        self.events.emit({'/event/button/Y/press': 1.5})
        assert self.events.emitted == ('/event/button/Y/press',)

        self.events.emit({})
        assert self.events.emitted == ()

    def test_emitted_does_not_alias_the_emitted_mapping(self) -> None:
        """
        A part that reuses one dict as its event buffer must not be able to
        corrupt the expiry list by clearing that dict.
        """
        buffer = {'/event/button/Y/press': 1.5}
        self.events.emit(buffer)
        buffer.clear()

        self.events.emit({})
        assert list(self.mem.keys()) == []

    def test_two_emitters_share_memory_without_interfering(self) -> None:
        buttons = OneShotEvents(self.mem)
        axes = OneShotEvents(self.mem)

        buttons.emit({'/event/button/Y/press': 1.5})
        axes.emit({'/event/axis/steer': 0.25})
        assert self.mem['/event/button/Y/press'] == 1.5
        assert self.mem['/event/axis/steer'] == 0.25

        buttons.emit({})
        assert '/event/button/Y/press' not in self.mem.keys()
        assert self.mem['/event/axis/steer'] == 0.25

    def test_does_not_disturb_persistent_state(self) -> None:
        self.mem['user/mode'] = 'local'
        self.events.emit({'/event/button/Y/press': 1.5})
        self.events.emit({})

        assert self.mem['user/mode'] == 'local'
