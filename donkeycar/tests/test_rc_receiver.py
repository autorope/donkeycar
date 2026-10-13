#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

import pytest

from donkeycar.parts.controls.device import NO_CHANGE
from donkeycar.parts.controls.gamepads import RC3ChanJoystick
from donkeycar.parts.controls.rc import RCReceiver
from donkeycar.tests.fake_rc import FakePigpioDevice

PINS = (5, 6, 13)


def make_receiver(**kwargs) -> tuple[RCReceiver, FakePigpioDevice]:
    device = FakePigpioDevice(num_channels=len(PINS))
    receiver = RCReceiver(pins=PINS, device=device, **kwargs)
    receiver.init()
    return receiver, device


def drain(receiver: RCReceiver) -> list:
    changes = []
    while (change := receiver.poll()) != NO_CHANGE:
        changes.append(change)
    return changes


class TestPulseWidthConversion(unittest.TestCase):
    """
    A servo channel runs 1000 to 2000 microseconds; the parts downstream
    want -1.0 to 1.0, the same range a gamepad stick reports.
    """

    def test_centre(self):
        receiver, device = make_receiver()
        device.set_width(0, 1500.0)
        assert receiver.poll() == NO_CHANGE  # centre is the resting state

    def test_full_travel_each_way(self):
        receiver, device = make_receiver()

        device.set_width(0, 1000.0)
        assert receiver.poll().axis_value == -1.0

        device.set_width(0, 2000.0)
        assert receiver.poll().axis_value == 1.0

    def test_half_travel(self):
        receiver, device = make_receiver()
        device.set_width(0, 1750.0)
        assert receiver.poll().axis_value == 0.5

    def test_a_width_beyond_the_normal_range_is_clamped(self):
        """
        Receivers overshoot; a value outside -1..1 would drive an actuator
        past its travel.
        """
        receiver, device = make_receiver()

        device.set_width(0, 2200.0)
        assert receiver.poll().axis_value == 1.0

        device.set_width(0, 800.0)
        assert receiver.poll().axis_value == -1.0

    def test_invert_reverses_every_channel(self):
        receiver, device = make_receiver(invert=True)

        device.set_width(0, 1000.0)
        assert receiver.poll().axis_value == 1.0

        device.set_width(0, 2000.0)
        assert receiver.poll().axis_value == -1.0


class TestSilentChannels(unittest.TestCase):

    def test_a_channel_never_seen_reports_nothing(self):
        """
        A transmitter that is switched off reads zero pulse width, which is
        not the same as a transmitter centred.  Reporting it as centre would
        make a dead radio look like a driver holding steady.
        """
        receiver, _ = make_receiver()
        assert receiver.poll() == NO_CHANGE

    def test_a_channel_that_goes_silent_stops_reporting(self):
        receiver, device = make_receiver()
        device.set_width(0, 2000.0)
        assert receiver.poll().axis_value == 1.0

        device.set_width(0, 0.0)
        assert receiver.poll() == NO_CHANGE


class TestNoChangeIsLost(unittest.TestCase):

    def test_channels_moving_together_are_all_reported(self):
        receiver, device = make_receiver()
        device.set_position(0, 0.5)
        device.set_position(1, -0.5)
        device.set_position(2, 1.0)

        moved = {(c.axis, c.axis_value) for c in drain(receiver)}
        assert moved == {
            ('steering', 0.5),
            ('throttle', -0.5),
            ('switch', 1.0),
        }

    def test_steering_and_throttle_together_keep_both(self):
        """
        The ordinary case: a driver turns and accelerates at once.
        """
        receiver, device = make_receiver()
        device.set_position(0, 0.8)
        device.set_position(1, 0.8)

        assert len(drain(receiver)) == 2


class TestJitterFilter(unittest.TestCase):

    def test_jitter_below_epsilon_is_suppressed(self):
        receiver, device = make_receiver(axis_epsilon=0.05)
        for width in (1502.0, 1505.0, 1508.0):
            device.set_width(0, width)
            assert receiver.poll() == NO_CHANGE

    def test_a_real_movement_gets_through(self):
        receiver, device = make_receiver(axis_epsilon=0.05)
        device.set_position(0, 0.5)
        assert receiver.poll().axis == 'steering'


class TestChannelNaming(unittest.TestCase):

    def test_the_default_names_match_the_other_rc_transmitter(self):
        """
        RC3ChanJoystick reaches the same transmitter through a joystick
        driver.  Sharing the names means a behavior map mostly carries
        between the two routes in.
        """
        receiver, _ = make_receiver()
        assert receiver.axis_map == ('steering', 'throttle', 'switch')

        joystick_names = set(RC3ChanJoystick.AXIS_NAMES.values())
        assert {'steering', 'throttle'} <= joystick_names

    def test_the_switch_is_analog_here_and_buttons_there(self):
        """
        A deliberate difference: the joystick driver thresholds the third
        channel into two buttons, while this layer reports what the
        receiver sends and leaves thresholding to a behavior part.
        """
        receiver, _ = make_receiver()
        assert 'switch' in receiver.axis_map

        assert set(RC3ChanJoystick.BUTTON_NAMES.values()) == {
            'switch_up', 'switch_down',
        }

    def test_channels_can_be_renamed(self):
        device = FakePigpioDevice(num_channels=2)
        receiver = RCReceiver(
            pins=(5, 6), device=device, channel_names=('rudder', 'elevator')
        )
        receiver.init()

        assert receiver.axis_map == ('rudder', 'elevator')

    def test_a_name_per_pin_is_required(self):
        device = FakePigpioDevice(num_channels=3)
        receiver = RCReceiver(
            pins=(5, 6, 13), device=device, channel_names=('only_one',)
        )

        with pytest.raises(ValueError, match='pins but'):
            receiver.init()


class TestLifecycle(unittest.TestCase):

    def test_init_watches_the_given_pins(self):
        _, device = make_receiver()
        assert device.pins == PINS

    def test_init_fails_without_pigpio(self):
        device = FakePigpioDevice(open_error=OSError('pigpiod not running'))
        receiver = RCReceiver(pins=PINS, device=device)

        assert receiver.init() is False
        assert receiver.poll() == NO_CHANGE

    def test_init_is_idempotent(self):
        receiver, device = make_receiver()
        receiver.init()
        assert device.open_count == 1

    def test_shutdown_releases_the_device(self):
        """
        The legacy part indexed its callback list with a Channel object, so
        shutdown raised TypeError every single time, and the pigpio
        connection was never released.
        """
        receiver, device = make_receiver()
        receiver.shutdown()

        assert device.closed is True
        assert receiver.poll() == NO_CHANGE

    def test_shutdown_is_safe_before_init(self):
        device = FakePigpioDevice()
        RCReceiver(pins=PINS, device=device).shutdown()
        assert device.closed is True
