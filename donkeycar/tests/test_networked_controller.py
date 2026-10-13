#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.device import NO_CHANGE, ControlChange
from donkeycar.parts.controls.network import (
    ControllerPublisher,
    MessagePublisher,
    MessageSubscriber,
    NetworkedController,
    decode,
    encode,
)
from donkeycar.tests.fake_js import FakeInputController


class FakeSubscriber:
    def __init__(self, messages=(), open_error: OSError | None = None) -> None:
        self.messages = list(messages)
        self.open_error = open_error
        self.open_count = 0
        self.closed = False

    def open(self) -> None:
        self.open_count += 1
        if self.open_error is not None:
            raise self.open_error

    def receive(self) -> str | None:
        return self.messages.pop(0) if self.messages else None

    def close(self) -> None:
        self.closed = True


class FakePublisher:
    def __init__(self, open_error: OSError | None = None) -> None:
        self.sent: list[str] = []
        self.open_error = open_error
        self.closed = False

    def open(self) -> None:
        if self.open_error is not None:
            raise self.open_error

    def send(self, message: str) -> None:
        self.sent.append(message)

    def close(self) -> None:
        self.closed = True


_subscriber_check: MessageSubscriber = FakeSubscriber()
_publisher_check: MessagePublisher = FakePublisher()


def make_controller(messages=()):
    subscriber = FakeSubscriber(messages)
    controller = NetworkedController(subscriber=subscriber)
    controller.init()
    return controller, subscriber


class TestWireFormat(unittest.TestCase):
    """
    The legacy format was four space-separated fields with '0' meaning
    'nothing happened'.
    """

    def test_a_change_survives_a_round_trip(self):
        change = ControlChange(button='a_button', button_state=1)
        assert decode(encode(change)) == change

    def test_an_axis_change_survives_a_round_trip(self):
        change = ControlChange(axis='left_stick_horz', axis_value=-0.5)
        assert decode(encode(change)) == change

    def test_a_name_containing_a_space_survives(self):
        """
        Legacy split the payload on spaces, so a control whose name had one
        produced too many fields and took the receiver's thread down.
        """
        change = ControlChange(button='red button', button_state=1)
        assert decode(encode(change)) == change

    def test_a_control_named_zero_is_not_mistaken_for_nothing(self):
        """
        Legacy used the string '0' to mean 'no control', so a control
        actually called that could never be reported.
        """
        change = ControlChange(button='0', button_state=1)
        assert decode(encode(change)).button == '0'

    def test_nothing_decodes_from_junk(self):
        assert decode('not json at all') is None
        assert decode('') is None
        assert decode('[1, 2, 3]') is None


class TestReceiving(unittest.TestCase):

    def test_a_message_becomes_a_control_change(self):
        controller, _ = make_controller(
            [encode(ControlChange(button='a_button', button_state=1))]
        )
        change = controller.poll()

        assert change.button == 'a_button'
        assert change.button_state == 1

    def test_nothing_arriving_is_not_a_failure(self):
        controller, _ = make_controller()
        assert controller.poll() == NO_CHANGE

    def test_a_bad_message_does_not_stop_the_receiver(self):
        """
        Legacy unpacked the split payload into four names with no error
        handling at all, so one malformed message killed the thread and the
        car stopped responding with no way back.
        """
        controller, _ = make_controller([
            'garbage',
            encode(ControlChange(button='a_button', button_state=1)),
        ])

        assert controller.poll() == NO_CHANGE  # the junk
        assert controller.poll().button == 'a_button'

    def test_an_empty_change_is_ignored(self):
        controller, _ = make_controller([encode(NO_CHANGE)])
        assert controller.poll() == NO_CHANGE


class TestNoChangeIsLost(unittest.TestCase):
    """
    Regression.  The legacy receiver kept one button and one axis in fields
    and overwrote them on every message, so anything arriving faster than
    the vehicle loop read it was gone.  A network delivers bursts by nature,
    so this was not a rare case.
    """

    def test_every_message_in_a_burst_is_delivered(self):
        messages = [
            encode(ControlChange(button='a_button', button_state=1)),
            encode(ControlChange(button='a_button', button_state=0)),
            encode(ControlChange(axis='steering', axis_value=0.5)),
        ]
        controller, _ = make_controller(messages)

        seen = []
        while (change := controller.poll()) != NO_CHANGE:
            seen.append(change)

        assert len(seen) == 3
        assert seen[0].button_state == 1
        assert seen[1].button_state == 0
        assert seen[2].axis == 'steering'

    def test_a_press_and_its_release_both_arrive(self):
        """
        Losing one of these leaves a button stuck down forever.
        """
        controller, _ = make_controller([
            encode(ControlChange(button='a_button', button_state=1)),
            encode(ControlChange(button='a_button', button_state=0)),
        ])

        assert controller.poll().button_state == 1
        assert controller.poll().button_state == 0


class TestRemoteControlsAreDiscovered(unittest.TestCase):

    def test_nothing_is_known_before_a_message_arrives(self):
        controller, _ = make_controller()
        assert controller.seen_controls == ()
        assert controller.show_map() is True

    def test_controls_are_remembered_as_they_report(self):
        controller, _ = make_controller([
            encode(ControlChange(button='a_button', button_state=1)),
            encode(ControlChange(axis='steering', axis_value=0.5)),
        ])
        while controller.poll() != NO_CHANGE:
            pass

        assert controller.seen_controls == ('a_button', 'steering')


class TestLifecycle(unittest.TestCase):

    def test_init_opens_the_subscriber(self):
        _, subscriber = make_controller()
        assert subscriber.open_count == 1

    def test_init_fails_when_the_network_is_unavailable(self):
        subscriber = FakeSubscriber(open_error=OSError('no route to host'))
        controller = NetworkedController(subscriber=subscriber)

        assert controller.init() is False
        assert controller.poll() == NO_CHANGE

    def test_shutdown_closes_the_subscriber(self):
        controller, subscriber = make_controller()
        controller.shutdown()

        assert subscriber.closed is True
        assert controller.poll() == NO_CHANGE


class TestPublishing(unittest.TestCase):

    def test_it_publishes_what_the_controller_reports(self):
        controller = FakeInputController([
            ControlChange(button='a_button', button_state=1),
            ControlChange(axis='steering', axis_value=0.5),
        ])
        publisher = FakePublisher()
        pub = ControllerPublisher(controller, publisher)
        pub.init()

        pub.poll()
        pub.poll()

        assert [decode(m).button for m in publisher.sent[:1]] == ['a_button']
        assert decode(publisher.sent[1]).axis == 'steering'

    def test_nothing_is_published_when_nothing_moved(self):
        publisher = FakePublisher()
        pub = ControllerPublisher(FakeInputController(), publisher)
        pub.init()
        pub.poll()

        assert publisher.sent == []

    def test_any_controller_can_be_published(self):
        """
        The legacy publisher hardcoded a PS3 pad, so driving from anything
        else meant editing the class.
        """
        publisher = FakePublisher()
        pub = ControllerPublisher(
            FakeInputController([ControlChange(axis='throttle', axis_value=1.0)]),
            publisher,
        )
        pub.init()
        pub.poll()

        assert decode(publisher.sent[0]).axis == 'throttle'

    def test_a_disconnected_controller_stops_publishing(self):
        controller = FakeInputController(poll_error=OSError('unplugged'))
        pub = ControllerPublisher(controller, FakePublisher())
        pub.init()
        pub.poll()

        assert pub.running is False

    def test_shutdown_releases_both_ends(self):
        controller = FakeInputController()
        publisher = FakePublisher()
        pub = ControllerPublisher(controller, publisher)
        pub.init()
        pub.shutdown()

        assert pub.running is False
        assert controller.closed is True
        assert publisher.closed is True


class TestEndToEnd(unittest.TestCase):

    def test_what_is_published_is_what_arrives(self):
        source = FakeInputController([
            ControlChange(button='a_button', button_state=1),
            ControlChange(axis='left_stick_horz', axis_value=-0.75),
        ])
        wire = FakePublisher()
        pub = ControllerPublisher(source, wire)
        pub.init()
        pub.poll()
        pub.poll()

        far_end, _ = make_controller(wire.sent)

        assert far_end.poll() == ControlChange(button='a_button', button_state=1)
        assert far_end.poll() == ControlChange(
            axis='left_stick_horz', axis_value=-0.75
        )
