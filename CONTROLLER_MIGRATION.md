# Upgrading a car to the new controller system

Donkeycar's game controller code was rewritten (issue #1097).  A controller
now reports which of its controls moved and nothing more; what those
movements *do* is decided by ordinary parts bound to named behaviors.  That
is what makes a control remappable without editing a template.

Most cars need one or two lines changed.  Work down the list; each section
says how to tell whether it applies to you.

---

## 1. Does your car still start?

Run it.  If it starts and drives, sections 2 and 3 are all you need to read.

Three failures mean this rewrite has caught you:

| What you see | Section |
|---|---|
| `ImportError: cannot import name 'JoystickController'` | [4](#4-a-custom-my_joystickpy) |
| `ValueError: Unknown CONTROLLER_TYPE` | [5](#5-controller_type) |
| The car drives, but a button does nothing | [3](#3-buttons-that-stopped-working) |

---

## 2. Your car drives differently

### The dead zone now applies to steering and throttle

`JOYSTICK_DEADZONE` used to affect only the decision about whether to
record.  It now also applies to the steering and throttle values, so a
stick resting slightly off centre no longer steers the car.

The default is `0.01`, which is small.  **Measured on a real Xbox pad, a
resting stick idled as far out as `0.099`** — ten times the default.  If
your car wanders with nobody touching the controller, raise it:

```python
JOYSTICK_DEADZONE = 0.12
```

To get exactly the old behaviour, set it to `0.0`.

### Xbox and Logitech throttle may feel different — because it now works

The Xbox axis map was wrong.  `right_stick_horz` and `right_stick_vert`
named the codes the driver actually uses for the **triggers**, and the real
right stick had no name at all.  So an Xbox user's "right stick throttle"
was really the right trigger, resting pegged at `-1.0`.

This is fixed, and the default binding is unchanged in intent: throttle is
the right stick, and now reaches the stick it names.  If you had worked
around it, remove the workaround.

Two consequences worth knowing:

- **"Forza mode" never ran.** It was bound to `right_trigger` and
  `left_trigger`, names that resolved to codes an Xbox pad does not send.
  It works now — see [7](#7-recipes).
- **Trigger throttle behaves differently when both are squeezed.** The old
  code let whichever trigger moved last win outright, so holding forward
  while brushing reverse gave full reverse. They now cancel.

### Recording is either automatic or a button, never both

`AUTO_RECORD_ON_THROTTLE = True` used to silently disable the manual
record button — it logged a line and ignored the press.  Now the template
adds one part or the other, so the button exists only when auto-record is
off.  Nothing to change; this is just why the button now appears in or
disappears from your bindings.

---

## 3. Buttons that stopped working

### Control names changed

Names now say what a control *is*, and are the same across pads where the
control is the same.  Only controls that carry a pad's identity keep its
own words.  If you have a `CONTROLLER_BEHAVIOR_MAP`, or you named controls
in a fork, translate them:

| Old name | New name | Pads |
|---|---|---|
| `L1`, `R1` | `left_shoulder`, `right_shoulder` | PS3, PS4, Logitech |
| `L2`, `R2` | `left_trigger_button`, `right_trigger_button` | PS3, PS4 |
| `L2_pressure`, `R2_pressure` | `left_trigger`, `right_trigger` | Logitech, PS3 |
| `L3`, `R3` | `left_stick_press`, `right_stick_press` | PS3, PS4 |
| `A`, `B`, `X`, `Y` | `a_button`, `b_button`, `x_button`, `y_button` | Logitech, WiiU |
| `a`, `b`, `x`, `y` | `a_button`, `b_button`, `x_button`, `y_button` | Nimbus |
| `PS` | `ps` | PS3, PS4 |
| `options` | `menu` | **Xbox only** — it is a PlayStation word |
| `pad` | *(gone)* | PS4 — see below |
| `dpad_leftright`, `dpad_up_down` | `dpad_horiz`, `dpad_vert` | Logitech |
| `hmm`, `what` | `dpad_horiz`, `dpad_vert` | Nimbus — these were placeholders |
| `lx`, `ly`, `rx`, `ry` | `left_stick_horz`, `left_stick_vert`, `right_stick_horz`, `right_stick_vert` | Nimbus |
| `LEFT_STICK_X` … | `left_stick_horz` … | WiiU |
| `PAD_DOWN,` | `dpad_down` | WiiU — note the stray comma in the old name |
| `Switch-up`, `Switch-down` | `switch_up`, `switch_down` | RC 3-channel |
| `Steering`, `Throttle` | `steering`, `throttle` | RC 3-channel |

To see what your own controller reports, start the car: it prints its
control map and its behavior bindings at startup.

### Controls that never worked, and now do

These were bound to codes the drivers do not send, so pressing them did
nothing at all.  If you have been avoiding them, stop:

- **PS4 `L3` and `R3`.** The map wrote `0x13a` twice, as both `L3` and
  `share`, so the stick presses were unreachable.
- **PS4 shoulders and triggers were swapped** relative to the PS3 map on
  the same driver.  `L1` is now the shoulder, as the kernel defines it.
- **WiiU dpad down.** It was on `0x224`, which is not a dpad code.
- **PS3 left-dpad pressure** on the Jessie-era driver, which was the one
  gap in an otherwise complete run of pressure axes.
- **Nimbus dpad**, which was named `hmm` and `what`.

### Controls that are gone

- **PS4 `pad`** (the touchpad click) is not a joystick button.  It is a
  separate input device that never reaches `/dev/input/js0`, so binding it
  never worked.  Over **PyGame** it does exist, as `touchpad`.

### Settings that are no longer read

Delete these; they do nothing now.  Their jobs moved to
`CONTROLLER_BEHAVIOR_MAP`:

```
AI_LAUNCH_ENABLE_BUTTON     SAVE_PATH_BTN        LOAD_PATH_BTN
ERASE_PATH_BTN              RESET_ORIGIN_BTN     TOGGLE_RECORDING_BTN
INC_PID_P_BTN               DEC_PID_P_BTN
INC_PID_D_BTN               DEC_PID_D_BTN
```

Note they named controls in the old vocabulary — `"option"`, `"R2"`,
`"x"` — several of which did not match what the drivers report, so some of
them could not have worked as written.

Web UI buttons are no longer a special case.  `web/w1` through `web/w5` are
now `/event/button/web_w1/press` and so on, and a behavior can take a list,
so one behavior can be driven by a gamepad button *and* a web button:

```python
TOGGLE_RECORDING: ['/event/button/b_button/press',
                   '/event/button/web_w1/press'],
```

---

## 4. A custom `my_joystick.py`

If `CONTROLLER_TYPE = 'custom'`, you have a `my_joystick.py` in your car
directory that `donkey createjs` generated.  **It will not import** — the
classes it derives from are gone.

The wizard no longer generates code.  Naming a control is configuration,
and what a control does is `CONTROLLER_BEHAVIOR_MAP`.  Two ways forward:

**Re-run the wizard** (easiest):

```bash
donkey createjs
```

It asks you to press each control and name it, then prints two
dictionaries to paste into `myconfig.py`.

**Or convert by hand.**  Your `my_joystick.py` has exactly what is needed:

```python
# in my_joystick.py -- the codes are the same, only where they live changes
self.button_names = {0x133: 'red_button'}
self.axis_names   = {0x03: 'throttle_lever'}
```

becomes, in `myconfig.py`:

```python
CONTROLLER_TYPE = 'custom'
JOYSTICK_BUTTON_NAMES = {0x133: 'red_button'}
JOYSTICK_AXIS_NAMES = {0x03: 'throttle_lever'}
```

The other half of your file — `button_down_trigger_map` and
`axis_trigger_map` — becomes `CONTROLLER_BEHAVIOR_MAP`.  A trigger map
like:

```python
self.button_down_trigger_map = {'red_button': self.toggle_mode}
self.axis_trigger_map = {'throttle_lever': self.set_throttle}
```

becomes:

```python
from donkeycar.parts.controls.mapping import TOGGLE_PILOT_MODE, THROTTLE

CONTROLLER_BEHAVIOR_MAP = {
    TOGGLE_PILOT_MODE: '/event/button/red_button/press',
    THROTTLE: '/event/axis/throttle_lever',
}
```

Then delete `my_joystick.py`.  Nothing imports it.

Your names can be layered over a controller that *does* have a built-in
map, too — set `CONTROLLER_TYPE` to that pad and list only the controls
you want renamed.

---

## 5. `CONTROLLER_TYPE`

Every value that worked before still works.  Two changed meaning and four
are new:

| Value | Notes |
|---|---|
| `ps3` | The current in-kernel driver |
| `ps3sixad` | **Unchanged.** For `sixad`, as on a Jetson Nano |
| `ps3old` | **New.** Raspbian Jessie-era driver |
| `ps3pc` | **New.** On a PC, where the pressure axes are also reported |
| `ps4`, `xbox`, `nimbus`, `wiiu`, `F710`, `rc3` | Unchanged |
| `xboxswapped` | **Now the same controller as `xbox`** with a different default map — swapping which stick steers is a binding, not hardware |
| `pygame` | Unchanged |
| `custom` | **Changed.** No longer imports `my_joystick.py`; see [4](#4-a-custom-my_joystickpy) |
| `mock` | **Now works.** It never did: the template imported a `MockController` that no module defined, so choosing it raised `ImportError` |
| `MM1`, `pigpio_rc` | Unchanged from your side |

**The PS3 variants differ by driver, not by pad.** The same DualShock 3
reports completely different codes through each, sharing as few as two
between them, so choosing the wrong one names every control incorrectly.
If your PS3 controls are all wrong, try another variant.

---

## 6. If you use an RC receiver or a RoboHAT MM1

Both are input controllers now rather than parts that decided the pilot
mode and recording on the side.  Your config is unchanged.

Two fixes you may notice:

- **`pigpio_rc` shutdown never worked.** It indexed a list with an object
  rather than an index, so it raised `TypeError` every time and never
  released pigpio.
- **`MM1_STOPPED_PWM`, `MM1_MAX_FORWARD` and `MM1_MAX_REVERSE` have never
  affected throttle.** They were applied twice, in opposite directions, and
  cancelled exactly.  That behaviour is preserved rather than changed on a
  guess — if you have been tuning them and seeing nothing, that is why.
  Please say so on #1097 if you know what they were meant to do.

If you use `basic.py` with `USE_RC = True`, it could not have been working:
it called the receiver with a pin where it expected a config and with two
arguments the class never had, so it raised `TypeError` at startup.  It
works now.

---

## 7. Recipes

Everything below goes in `myconfig.py`.  Setting `CONTROLLER_BEHAVIOR_MAP`
replaces the default outright, so list every binding you want.

```python
from donkeycar.parts.controls.mapping import (
    STEERING, THROTTLE, THROTTLE_FORWARD, THROTTLE_REVERSE,
    TOGGLE_PILOT_MODE, TOGGLE_RECORDING, ERASE_RECORDS,
    EMERGENCY_STOP, STOP_VEHICLE, STOP_VEHICLE_MODIFIER,
    INCREASE_MAX_THROTTLE, DECREASE_MAX_THROTTLE,
)
```

**Swap which stick steers** (what `xboxswapped` was):

```python
CONTROLLER_BEHAVIOR_MAP = {
    STEERING: '/event/axis/right_stick_horz',
    THROTTLE: '/event/axis/left_stick_vert',
    # ... the rest of your bindings
}
```

**Forza mode** — triggers for throttle, which never ran before:

```python
    THROTTLE_FORWARD: '/axis/right_trigger',
    THROTTLE_REVERSE: '/axis/left_trigger',
```

**Guard something irreversible behind a double-click.**  Erasing a path or
records cannot be undone, and the old button triggers had no way to express
this:

```python
    ERASE_RECORDS: '/event/button/x_button/click/2',
```

**Require two hands to stop the car**, so it cannot happen by accident —
double-click B while holding X:

```python
    STOP_VEHICLE: '/event/button/b_button/click/2',
    STOP_VEHICLE_MODIFIER: '/button/x_button',
```

**Use a long press** rather than a click:

```python
    EMERGENCY_STOP: '/event/button/y_button/hold',
```

### What a control can offer

| Key | When |
|---|---|
| `/event/button/NAME/press` | The moment it goes down |
| `/event/button/NAME/release` | The moment it comes up |
| `/event/button/NAME/click/1` | A single click, once the burst has ended |
| `/event/button/NAME/click/2` | A double-click — and `/1` does *not* also fire |
| `/event/button/NAME/hold` | Held past half a second; no click follows |
| `/button/NAME` | `1` while held, `0` otherwise — persists, for modifiers |
| `/event/axis/NAME` | The moment it moves, carrying its position |
| `/axis/NAME` | Its position — persists |

---

## Getting help

Start the car and read the first few lines.  It prints the controls your
pad reports and the behavior each is bound to, which answers most of these
questions faster than this document does.

If something here is wrong or missing, say so on
[#1097](https://github.com/autorope/donkeycar/issues/1097).
