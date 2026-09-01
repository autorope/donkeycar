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

Naming convention.  Controls that every pad has are named for what they are,
identically across pads: left_stick_horz, left_stick_vert, right_stick_horz,
right_stick_vert, left_trigger, right_trigger, left_shoulder,
right_shoulder, left_stick_press, right_stick_press, dpad_*.  Controls that
carry the pad's own identity keep the words printed on it: a_button and
menu on an Xbox pad, cross and select on a PlayStation one.  This keeps a
behavior map legible when it is read next to another pad's, while leaving
each pad recognisable to the person holding it.

@author: ezward
"""

from donkeycar.parts.controls.linux import LinuxGameController


class PS3Joystick(LinuxGameController):
    """
    Sony DualShock 3 on the in-kernel `hid-sony` driver.

    This is the mapping that has worked on Raspberry Pi OS from Stretch
    onward.  PS3 pads are unusually driver-dependent -- the same controller
    reports different codes through `sixad` and through the older Jessie
    driver -- so those have their own classes rather than options here.

    Two things differ from the Xbox-style pads:

    The dpad is four buttons, not a pair of axes.  `hid-sony` reports
    BTN_DPAD_UP and friends, so bind dpad_up rather than watching an axis
    for -1.

    The triggers are reported twice over: as analog axes (left_trigger,
    right_trigger) and as digital buttons (left_trigger_button,
    right_trigger_button).  A squeeze produces both.  Use the axis for
    proportional control and the button for a simple press.

    NOT VERIFIED against hardware -- no DualShock 3 was available.  The
    codes come from the map Donkeycar has shipped for years.  Its axis
    layout agrees with the Xbox pad that was measured, which is reassuring
    but not proof: the ABS codes are kernel-wide constants with conventional
    meanings, and `hid-sony` follows the same convention `xpad` does, but
    nothing forces a driver to.  Worth confirming on a real pad.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'left_trigger',
        0x03: 'right_stick_horz',
        0x04: 'right_stick_vert',
        0x05: 'right_trigger',
    }

    BUTTON_NAMES = {
        0x130: 'cross',
        0x131: 'circle',
        0x133: 'triangle',
        0x134: 'square',
        0x136: 'left_shoulder',
        0x137: 'right_shoulder',
        0x138: 'left_trigger_button',
        0x139: 'right_trigger_button',
        0x13A: 'select',
        0x13B: 'start',
        0x13C: 'ps',
        0x13D: 'left_stick_press',
        0x13E: 'right_stick_press',
        0x220: 'dpad_up',
        0x221: 'dpad_down',
        0x222: 'dpad_left',
        0x223: 'dpad_right',
    }


class PS3JoystickSixAd(LinuxGameController):
    """
    Sony DualShock 3 through the `sixad` userland driver, as used on the
    Jetson Nano.

    The same physical pad as PS3Joystick, reporting entirely different
    codes.  `sixad` builds its own uinput device and assigns controls in its
    own order rather than following the conventions the in-kernel drivers
    use, so:

    The right stick is at 0x02/0x03, not 0x03/0x04.  `sixad` numbers the
    axes sequentially -- left stick, then right stick -- so the right stick
    lands on ABS_Z and ABS_RX, the codes that mean the triggers everywhere
    else.  A map that "corrected" this to match the Xbox pad would steer
    with the wrong stick.

    There are no analog trigger axes at all.  L2 and R2 are reported only as
    digital buttons, so proportional trigger control is not available on
    this driver.

    The buttons are in the generic joystick block (0x120-0x12f) rather than
    the gamepad block (0x130+), because `sixad` presents the pad as a plain
    joystick.  Only the PS button lands at 0x130.

    NOT VERIFIED against hardware.  The codes come from the map Donkeycar
    has shipped, and unlike the other PlayStation map there is no convention
    to check them against -- these assignments are `sixad`'s own.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'right_stick_horz',
        0x03: 'right_stick_vert',
    }

    BUTTON_NAMES = {
        0x120: 'select',
        0x121: 'left_stick_press',
        0x122: 'right_stick_press',
        0x123: 'start',
        0x124: 'dpad_up',
        0x125: 'dpad_right',
        0x126: 'dpad_down',
        0x127: 'dpad_left',
        0x128: 'left_trigger_button',
        0x129: 'right_trigger_button',
        0x12A: 'left_shoulder',
        0x12B: 'right_shoulder',
        0x12C: 'triangle',
        0x12D: 'circle',
        0x12E: 'cross',
        0x12F: 'square',
        0x130: 'ps',
    }


class PS3JoystickOld(LinuxGameController):
    """
    Sony DualShock 3 on the Raspbian Jessie-era `hid-sony` driver.

    The third layout for this one controller, agreeing with neither of the
    others: the right stick is at 0x02/0x05 here, at 0x03/0x04 through the
    modern in-kernel driver, and at 0x02/0x03 through `sixad`.

    What makes this driver distinctive is that it exposes the DualShock 3's
    pressure sensitivity.  Every face button, shoulder and dpad direction
    reports how hard it is being pressed, as an axis, alongside the ordinary
    digital button.  Twelve of the axes here are pressure; only the first
    four and the tilt axes are conventional.

    The pad's motion sensors also appear, as tilt_x, tilt_y, tilt_a and
    tilt_b.  Those names come from the legacy map and are kept because
    nothing better is known -- which of them are accelerometer axes and
    which the gyro has not been established.

    NOT VERIFIED against hardware.  The codes come from the map Donkeycar
    has shipped.  One addition: the legacy map named eleven of the twelve
    pressure axes, in the order the DualShock 3 reports them, and omitted
    dpad_left_pressure at 0x2f, the one gap in an otherwise unbroken run.
    It is named here so a left-dpad press does not surface as an anonymous
    'axis(0x2f)', but the inference is from the sequence rather than from a
    device.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'right_stick_horz',
        0x05: 'right_stick_vert',

        # motion sensors; the legacy names, meanings unestablished
        0x1A: 'tilt_x',
        0x1B: 'tilt_y',
        0x3C: 'tilt_b',
        0x3D: 'tilt_a',

        # pressure-sensitive controls, in the order the pad reports them:
        # dpad up/right/down/left, L2, R2, L1, R1, then the face buttons
        0x2C: 'dpad_up_pressure',
        0x2D: 'dpad_right_pressure',
        0x2E: 'dpad_down_pressure',
        0x2F: 'dpad_left_pressure',
        0x30: 'left_trigger',
        0x31: 'right_trigger',
        0x32: 'left_shoulder_pressure',
        0x33: 'right_shoulder_pressure',
        0x34: 'triangle_pressure',
        0x35: 'circle_pressure',
        0x36: 'cross_pressure',
        0x37: 'square_pressure',
    }

    BUTTON_NAMES = {
        0x120: 'select',
        0x121: 'left_stick_press',
        0x122: 'right_stick_press',
        0x123: 'start',
        0x124: 'dpad_up',
        0x125: 'dpad_right',
        0x126: 'dpad_down',
        0x127: 'dpad_left',
        0x128: 'left_trigger_button',
        0x129: 'right_trigger_button',
        0x12A: 'left_shoulder',
        0x12B: 'right_shoulder',
        0x12C: 'triangle',
        0x12D: 'circle',
        0x12E: 'cross',
        0x12F: 'square',
        0x2C0: 'ps',
    }


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
