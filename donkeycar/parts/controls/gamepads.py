#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Button and axis names for the game controllers Donkeycar supports.

A controller here is pure data: a LinuxGameController subclass declaring
what each of the driver's control codes is called.  Everything else --
opening the device, reading events, naming unmapped controls -- comes from
the base class.

A map is only as good as the driver it was written against.  The same pad
reports different codes through different drivers, so each map records which
driver and which device it was verified against, and says so plainly when it
was not verified at all.

@author: ezward
"""

from donkeycar.parts.controls.linux import LinuxGameController


class LogitechJoystick(LinuxGameController):
    """
    Logitech Gamepad F710 with its mode switch set to X (XInput).

    In that mode the pad presents itself as an Xbox 360 controller and is
    driven by the same in-kernel `xpad` driver, so it reports the same
    control codes as XboxOneJoystick and differs only in what the labels
    say: BACK, START and the Logitech button in place of view, menu and the
    Xbox guide.  Set to D (DirectInput) it enumerates differently and this
    map does not apply.

    Like the Xbox pad, the triggers are axes resting at -1.0 rather than
    centring at 0.0, and the sticks jitter enough to want `axis_epsilon`.

    NOT VERIFIED against hardware -- no F710 was available.  The codes come
    from the map Donkeycar has shipped for years, which is corroborated by
    the Xbox measurement: it places the triggers at 0x02/0x05 and the right
    stick at 0x03/0x04, exactly as measured on the same driver, and this is
    where the legacy Xbox map was wrong.  Worth confirming on a real F710
    before relying on it.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'left_trigger',
        0x03: 'right_stick_horz',
        0x04: 'right_stick_vert',
        0x05: 'right_trigger',
        0x10: 'dpad_horiz',
        0x11: 'dpad_vert',
    }

    BUTTON_NAMES = {
        0x130: 'a_button',
        0x131: 'b_button',
        0x133: 'x_button',
        0x134: 'y_button',
        0x136: 'left_shoulder',
        0x137: 'right_shoulder',
        0x13A: 'back',
        0x13B: 'start',
        0x13C: 'logitech',
        0x13D: 'left_stick_press',
        0x13E: 'right_stick_press',
    }


class XboxOneJoystick(LinuxGameController):
    """
    Microsoft Xbox One / Series controller on the in-kernel `xpad` driver.

    Verified against a 'Microsoft X-Box One S pad' over USB on 2026-08-31,
    each control moved in isolation.  The driver reports exactly the eight
    axes and eleven buttons named below.

    Two things to know about this pad's axes:

    The triggers are axes, not buttons, and they rest at -1.0 and travel to
    +1.0 -- unlike the sticks, which rest at 0.0 and travel both ways.  A
    part that treats a trigger as though it centred at zero will read a
    fully released trigger as full deflection.

    The sticks jitter.  A resting stick on the test pad produced a steady
    trickle of events up to about 0.1, which floods the event stream.  Pass
    `axis_epsilon` to filter it; 0.1 was enough here.

    NOTE: over Bluetooth this pad presents a malformed HID report descriptor
    that mainline `hid-generic` rejects outright ('unbalanced collection at
    end of report description'), so no device node appears at all.  Use USB,
    update the pad's firmware, or install `xpadneo`.  Note that `xpadneo`
    numbers the axes differently, so this map does not apply to it.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'left_trigger',
        0x03: 'right_stick_horz',
        0x04: 'right_stick_vert',
        0x05: 'right_trigger',
        0x10: 'dpad_horiz',
        0x11: 'dpad_vert',
    }

    BUTTON_NAMES = {
        0x130: 'a_button',
        0x131: 'b_button',
        0x133: 'x_button',
        0x134: 'y_button',
        0x136: 'left_shoulder',
        0x137: 'right_shoulder',
        0x13A: 'view',
        0x13B: 'menu',
        0x13C: 'xbox',
        0x13D: 'left_stick_press',
        0x13E: 'right_stick_press',
    }
