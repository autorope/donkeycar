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


class PS3JoystickPC(PS3Joystick):
    """
    Sony DualShock 3 on a PC, where the driver also exposes the pad's
    pressure and motion axes.

    Unlike the other PlayStation variants this is not a different layout.
    Every code it shares with PS3Joystick means the same thing -- the
    buttons are identical, and so are the sticks and triggers -- and it adds
    the twelve pressure axes and four tilt axes on top.  So it derives from
    PS3Joystick rather than restating it, which also stops the two drifting
    apart if either is ever corrected.

    That raises a question worth someone checking on real hardware: if this
    is the same driver with more axes surfaced, then PS3Joystick is not
    *different*, just incomplete, and a Pi user is getting anonymous
    'axis(0x2c)' events for pressure the pad is really sending.  If so these
    two should merge.  Nobody has confirmed it either way.

    The legacy map noted this pad wants /dev/input/js1 rather than js0, and
    that on Ubuntu 16.04 it drives the mouse around until you run:

        xinput set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0

    NOT VERIFIED against hardware.  As in PS3JoystickOld, the legacy map
    left dpad_left_pressure at 0x2f unnamed -- the one gap in the dpad's run
    -- and it is filled here by inference from the sequence.  Note that
    0x30 and 0x31 are deliberately absent: on this driver the analog
    triggers arrive at 0x02 and 0x05 with the sticks, not in the pressure
    block where PS3JoystickOld puts them.
    """

    AXIS_NAMES = {
        **PS3Joystick.AXIS_NAMES,

        # motion sensors; the legacy names, meanings unestablished
        0x1A: 'tilt_x',
        0x1B: 'tilt_y',
        0x3C: 'tilt_b',
        0x3D: 'tilt_a',

        # pressure-sensitive controls.  The triggers are absent from this
        # run because this driver reports them at 0x02/0x05 instead.
        0x2C: 'dpad_up_pressure',
        0x2D: 'dpad_right_pressure',
        0x2E: 'dpad_down_pressure',
        0x2F: 'dpad_left_pressure',
        0x32: 'left_shoulder_pressure',
        0x33: 'right_shoulder_pressure',
        0x34: 'triangle_pressure',
        0x35: 'circle_pressure',
        0x36: 'cross_pressure',
        0x37: 'square_pressure',
    }


class PS4Joystick(LinuxGameController):
    """
    Sony DualShock 4 on the in-kernel `hid-sony` driver.

    Closer to the Xbox pads in shape than to the DualShock 3: the dpad is an
    axis pair rather than four buttons, and the triggers report as analog
    axes with digital buttons alongside.

    The legacy map for this pad had a defect that cost two controls.  It
    wrote 0x13a twice, as both 'L3' and 'share', and 0x13b twice, as both
    'R3' and 'options'.  Python keeps the last of a repeated key, so the
    earlier entries vanished silently and the stick-press buttons could not
    be bound at all.  A duplicate key cannot be seen in the finished dict --
    it is already gone -- which is why the tests read the source instead.

    Fixing that meant deciding what those codes really are, and the codes
    are unambiguous: 0x13a is BTN_SELECT and 0x13b is BTN_START, so share
    and options, while the stick presses are BTN_THUMBL and BTN_THUMBR at
    0x13d and 0x13e.  That is what PS3Joystick already does on the same
    driver.

    Two further corrections in the same area.  The legacy map had the
    shoulders and triggers the other way round from its own PS3 map -- L1 at
    0x138 and L2 at 0x136, where the PS3 map, the kernel headers and this
    one all have L1 at 0x136 (BTN_TL) and L2 at 0x138 (BTN_TL2).  The two
    shipped maps cannot both be right for the same driver.  And 0x13d was
    named 'pad' for the touchpad click; it is BTN_THUMBL.  The touchpad
    presents as its own input device rather than on the joystick node, so
    it is not named here at all.

    NOT VERIFIED against hardware -- no DualShock 4 was available.  Every
    correction above follows the kernel's own button codes and agrees with
    the PS3 map on the shared driver, but a pad on a bench would settle it.
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

        # motion sensors; the legacy names, meanings unestablished
        0x06: 'motion_a',
        0x07: 'motion_b',
        0x08: 'motion_c',
        0x19: 'tilt_a',
        0x1A: 'tilt_b',
        0x1B: 'tilt_c',
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
        0x13A: 'share',
        0x13B: 'options',
        0x13C: 'ps',
        0x13D: 'left_stick_press',
        0x13E: 'right_stick_press',
    }


class Nimbus(LinuxGameController):
    """
    SteelSeries Nimbus, as seen on a Jetson TX2 running JetPack 4.2.

    An MFi controller handled by `hid-generic`, which assigns the gamepad
    button codes in the order the HID descriptor lists them rather than by
    what each button means.  So the codes run straight through 0x130-0x137
    for A, B, X, Y and the four shoulders, and do not line up with the
    Xbox-style pads: 0x133 is Y here and X there.  That is the driver's
    doing, not an error, and a test asserts the difference so it is not
    tidied into agreement later.

    The pad's four shoulders are all digital on this driver -- no analog
    trigger axes are reported -- so the triggers are named as buttons.

    The Nimbus has a Menu button that the legacy map did not name and this
    one does not either, because its code is unknown.  It will surface as
    'button(0x...)', which show_map() will reveal on a real device.

    NOT VERIFIED against hardware.  The codes come from the map Donkeycar
    has shipped.

    One correction: the legacy map named the two hat axes 'hmm' and 'what',
    evidently placeholders that were never resolved.  They are 0x10 and
    0x11, ABS_HAT0X and ABS_HAT0Y, which are the dpad -- the same codes
    measured as the dpad on a real Xbox pad.  They are named dpad_horiz and
    dpad_vert here, matching every other pad that reports a hat.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x02: 'right_stick_horz',
        0x05: 'right_stick_vert',
        0x10: 'dpad_horiz',
        0x11: 'dpad_vert',
    }

    BUTTON_NAMES = {
        0x130: 'a_button',
        0x131: 'b_button',
        0x132: 'x_button',
        0x133: 'y_button',
        0x134: 'left_shoulder',
        0x135: 'right_shoulder',
        0x136: 'left_trigger_button',
        0x137: 'right_trigger_button',
    }


class WiiU(LinuxGameController):
    """
    Nintendo Wii U Pro Controller.

    Nintendo's face buttons sit in the opposite arrangement to everyone
    else's: B is the bottom button and A the right one, X the top and Y the
    left.  The codes follow the positions, not the letters, so a_button is
    at 0x131 here where an Xbox pad has b_button.  That is correct and a
    test asserts it, because it looks exactly like the kind of transposition
    that is usually a bug.

    The four shoulders are all digital -- the Pro Controller has no analog
    triggers -- so they are named as buttons.  The pad prints its two system
    buttons as minus and plus; they are named select and start after the
    codes they use and the names Donkeycar has always given them.

    NOT VERIFIED against hardware, and rather less certain than the other
    maps: the legacy map was transcribed from a third-party config file and
    carried the comment "need testing!" from the day it landed.

    Two corrections.  The legacy map named the down direction 'PAD_DOWN,'
    with a comma inside the string, so the event key had a stray comma in
    it.  And it put that direction on 0x224, which is not a dpad code at
    all: up, down, left and right are 0x220 to 0x223, and the legacy map had
    the other three right.  So down is moved to 0x221, where the run of four
    is unbroken.  As it stood, dpad down could not fire and 0x221 went
    unnamed.
    """

    AXIS_NAMES = {
        0x00: 'left_stick_horz',
        0x01: 'left_stick_vert',
        0x03: 'right_stick_horz',
        0x04: 'right_stick_vert',
    }

    BUTTON_NAMES = {
        # face buttons by position, which is how Nintendo arranges them
        0x130: 'b_button',
        0x131: 'a_button',
        0x133: 'x_button',
        0x134: 'y_button',

        0x136: 'left_shoulder',
        0x137: 'right_shoulder',
        0x138: 'left_trigger_button',
        0x139: 'right_trigger_button',
        0x13A: 'select',
        0x13B: 'start',
        0x13D: 'left_stick_press',
        0x13E: 'right_stick_press',

        0x220: 'dpad_up',
        0x221: 'dpad_down',
        0x222: 'dpad_left',
        0x223: 'dpad_right',
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
