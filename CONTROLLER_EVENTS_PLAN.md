# Plan: finish the game-controller event refactor (#1097)

**50 / 50 tasks.** Phase 12's hardware check is still to do.

50 commits in total.  Phases 0–6 took 39: their 37 tasks, plus one for the
dead-zone default change (folded into 3.1's note) and one correcting this
checklist, whose Phase 2 and Phase 6 boxes had been left unticked while
their work was done.  Phase 7 took 4, Phases 8, 9 and 10 took 2 each, and Phase 11 took 1, one per task.
Phase 0 ▓▓▓▓ · Phase 1 ▓▓▓▓▓▓▓▓▓▓▓ · Phase 2 ▓▓▓▓▓ · Phase 3 ▓▓▓▓▓ ·
Phase 4 ▓▓ · Phase 5 ▓▓▓▓▓▓▓ · Phase 6 ▓▓▓ · Phase 7 ▓▓▓▓ · Phase 8 ▓▓ · Phase 9 ▓▓ · Phase 10 ▓▓ · Phase 11 ▓ · Phase 12 ▓▓

> Convention: tick a box in §4 in the same commit that does the work, so the
> checklist and the git history never disagree. Update the counter above too.

Status of the branch today: `LinuxGameController` + `LogitechJoystick` +
`InputControllerEvents` exist as a proof of concept in
`donkeycar/parts/controller_events.py`, plus four sample behavior parts
(`TogglePilotMode`, `UserThrottle`, `UserSteering`, `StopVehicle`) and an
untracked, unused `donkeycar/events.py`. Nothing in `donkeycar/templates/`
uses any of it, and the legacy `Joystick` / `JoystickController` hierarchy in
`donkeycar/parts/controller.py` (~1750 lines) is still what every template
runs.

Agreed constraints for this work:

- **Hard cutover.** The legacy `JoystickController` hierarchy is deleted; no
  compatibility shim, no config flag.
- **All joysticks, all templates.** Gamepads land first.
- **One commit per joystick, one commit per template.**
- **Python 3.12/3.13 idioms, strict type hints, unit tests green on every
  commit.**

---

## 1. Architecture

### 1.1 Module layout

The POC piles device drivers, the event pump, and behavior parts into one
file. Split them into a package so per-gamepad commits touch one small file:

```
donkeycar/events.py                    one-shot event bookkeeping helper
donkeycar/parts/controls/
    __init__.py                        public re-exports
    device.py                          ControlChange, AbstractInputController
    linux.py                           LinuxGameController + JsDevice seam
    gamepads.py                        per-gamepad button/axis name maps
    pygame.py                          PyGame device
    rc.py                              pigpio RC receiver as a device
    robohat.py                         MM1 as a device
    network.py                         networked joystick as a device
    events.py                          InputControllerEvents
    behaviors.py                       behavior parts + behavior-event names
    mapping.py                         event -> behavior translation + defaults
    factory.py                         get_input_controller(cfg)
```

`donkeycar/parts/controller.py` keeps only `LocalWebController` / `WebFpv`
re-exports until Phase 6, then goes away with its importers updated.

### 1.2 The device contract

Today `poll()` returns a bare 4-tuple of optionals and is annotated
`tuple[str | None, int | None, str | ModuleNotFoundError, float | None]`
(that `ModuleNotFoundError` is a typo). Replace with a `NamedTuple`, which is
tuple-compatible so every existing unpack site keeps working:

```python
class ControlChange(NamedTuple):
    button: str | None = None
    button_state: int | None = None
    axis: str | None = None
    axis_value: float | None = None

NO_CHANGE = ControlChange()


class AbstractInputController(abc.ABC):
    @abc.abstractmethod
    def init(self) -> bool: ...
    @abc.abstractmethod
    def show_map(self) -> bool: ...
    @abc.abstractmethod
    def poll(self) -> ControlChange: ...
    def shutdown(self) -> None: ...
```

Note the POC's `init()` docstring promises `Self` but the implementation
returns `bool`; `bool` is the honest contract, and `typing_extensions.Self`
goes away entirely (3.12 has `typing.Self`).

### 1.3 The seam that makes gamepads testable in CI

This is the single most important design decision in the plan. CI has no
`/dev/input/js0`, so `LinuxGameController.init()` — which is nothing but
`fcntl.ioctl` calls — currently cannot run under test, and neither can any
name map that depends on it. Push the ioctl work behind an injectable
protocol:

```python
class JsDeviceInfo(NamedTuple):
    name: str
    axis_codes: tuple[int, ...]
    button_codes: tuple[int, ...]


class JsDevice(Protocol):
    def open(self) -> JsDeviceInfo: ...
    def read_event(self) -> tuple[int, int, int, int] | None: ...  # tval, value, type, number
    def close(self) -> None: ...
```

`LinuxJsDevice` does the real `open()` + `ioctl` + `struct.unpack`.
`FakeJsDevice` (in `donkeycar/tests/`) is constructed with a device name, the
axis/button code lists, and a scripted list of raw events to replay.

`LinuxGameController(device: JsDevice, button_names=..., axis_names=...)`.

With that, **every gamepad commit gets a real test**: feed the controller's
own declared button/axis codes plus synthetic press/release/axis events
through `FakeJsDevice` and assert `poll()` emits the mapped names. No
hardware, no skips, no `on_pi` guard.

### 1.4 One-shot events

`donkeycar/events.py` currently holds an unused `Events` class whose
`expire_events()` mutates a dict while iterating it (a `RuntimeError` waiting
to happen) and whose lifetime arithmetic drops an event a tick early.
`InputControllerEvents` ignores it and hand-rolls the same bookkeeping with
`previous_button_events` / `previous_axis_events`.

Rewrite `events.py` into the helper both event-emitting parts actually need:

```python
class OneShotEvents:
    """Writes events to memory and removes them on the next emit."""
    def __init__(self, memory: Memory) -> None: ...
    def emit(self, events: Mapping[str, object]) -> None: ...
    def clear(self) -> None: ...
```

Expiry stays owned by the emitting part (removed on that part's *next* pass),
not by `Vehicle` at end-of-loop. That is deliberate: end-of-loop expiry would
mean parts added *before* the emitter never observe the event at all, whereas
the current semantics give them the event one loop later — which is what
DocGarbanzo asked for in #1097 and what makes the non-DAG part topology work.

`BehaviorEventMapper` (§3) reuses `OneShotEvents` so translated behavior
events are one-shot too, for free.

### 1.5 Shared drive state moves into memory

The legacy `JoystickController` kept `throttle_scale`, `constant_throttle`,
`chaos_monkey_steering`, `estop_state`, `mode`, and `recording` as fields on
one object, which is exactly why the behaviors could not be separated. Once
each behavior is its own part, that shared state has to be named memory:

| key | owner part(s) | readers |
|---|---|---|
| `user/mode` | `TogglePilotMode` | `DriveMode`, `ToggleRecording` |
| `user/steering` | `UserSteering`, `ChaosMonkey` | `DriveMode` |
| `user/throttle` | `UserThrottle`, `ConstantThrottle`, `EmergencyStop` | `DriveMode` |
| `user/throttle_scale` | `AdjustMaxThrottle` | `UserThrottle`, `ConstantThrottle` |
| `user/constant_throttle` | `ToggleConstantThrottle` | `UserThrottle` |
| `user/estop` | `EmergencyStop` | `UserThrottle`, `DriveMode` |
| `recording` | `ToggleRecording`, `AutoRecordOnThrottle` | `TubWriter` |

This table is the real content of "complete the plan for behaviors in the
templates" — the parts are easy once the state has names.

---

## 2. Defects in the POC to fix (each with a regression test)

Found while reading the branch; all are in Phase 0 unless noted:

1. **Mutable default arguments.** `LinuxGameController.__init__(self,
   button_names={}, axis_names={}, ...)` — and `init()` *writes into them*
   (`self.axis_names[axis] = axis_name`). Two controllers share one dict.
2. **Subclass maps clobber constructor args.** `LogitechJoystick.__init__`
   assigns `self.axis_names = {...}` *after* `super().__init__()`, so a
   caller-supplied map is silently discarded. This blocks the "custom control
   names from `myconfig.py`" feature #1097 calls for. Fix: subclasses pass
   built-in maps up as defaults, caller entries win.
3. **`Memory.remove()` raises `KeyError`** on a missing key (`del self.d[key]`).
   `InputControllerEvents` is the only caller today and happens to be safe;
   `BehaviorEventMapper` will not be. Use `pop(key, None)`.
4. **Bare `except:` in `poll()` and `update()`** swallows everything —
   including `KeyboardInterrupt` — and silently flips `running = False` with
   no log line. This is the failure mode where the joystick "just stops
   working" mid-drive with nothing in the log.
5. **`time.time()` for click timing.** Wall-clock, and untestable. Inject
   `clock: Callable[[], float] = time.monotonic`.
6. **Blocking init in the constructor.** `InputControllerEvents.__init__`
   calls `init_controller()`, which blocks up to 5 s and raises if the pad
   isn't paired yet — at template-assembly time. Move the retry loop into the
   threaded `update()`, as legacy `JoystickController.update()` did.
7. **`PS4Joystick.button_names` has duplicate keys** — `0x13a` is written as
   both `L3` and `share`, `0x13b` as both `R3` and `options`. Python keeps the
   last, so **`L3` and `R3` are unreachable on PS4 today**. Fixed in 1.6, and
   the AST check was run against the legacy class to confirm it reports exactly
   those two codes. Two neighbouring errors turned up with it: legacy PS4 and
   legacy PS3 disagree over which codes are the shoulders and which the
   triggers (the kernel headers side with PS3), and `0x13d` was named `pad` for
   the touchpad when it is `BTN_THUMBL` — the touchpad is a separate input
   device and never appears on the joystick node.
8. **`WiiU` button `548: 'PAD_DOWN,'`** — trailing comma inside the string, so
   the event key carried it too. Fixed in 1.9, along with a worse defect found
   beside it: `548` is `0x224`, not a dpad code at all. The dpad is `0x220`-
   `0x223` and legacy had the other three right, so **dpad down could never
   fire** and `0x221` went unnamed.
9. **No axis jitter filter.** #1097 notes stick jitter floods the event stream
   (visible in the logged sample: five `right_stick_horz` events for one
   `right_stick_vert` push). Fixed in 0.2 as `axis_epsilon`, a deadband on
   *change* measured against the last reported value, so jitter is suppressed
   but slow sustained movement still accumulates through. A return to exact
   center is always reported — swallowing it would leave throttle or steering
   stuck slightly off zero. Note this is **not** `JOYSTICK_DEADZONE`, which is
   a deadband around center and belongs with `UserThrottle`/`UserSteering` in
   3.1, where it gated auto-record in the legacy code.
10. **`Nimbus` axes named `hmm` and `what`.** Placeholder names shipping in
    the public map. Resolved in 1.8 with evidence rather than a guess: they are
    `0x10`/`0x11`, the hat axes, which the Xbox capture measured as the dpad.
11. **Shutdown deadlocked against its own reader.** (Found on the car; fixed
    in 0.4.) Reads went through a buffered file object, whose `peek()` blocks
    on an idle gamepad — nearly always — while holding the file object's
    internal lock. `close()` from the vehicle thread then waited forever on
    the reader thread. Thread dump showed the reader parked in `read_event`
    and the main thread parked in `close`. **A car with an idle gamepad hung
    on shutdown.**
12. **A vanished device was reported as "no event", forever.** (Found on the
    car; fixed in 0.4.) The Xbox pad dropped off USB and re-enumerated; the
    reader kept the old descriptor and returned "nothing happened" every 50ms
    for the rest of the run — no error, no log line, `running` still true.
    This is the same silent-failure class as the bare `except:` in defect 4.
    `select.select()` cannot tell "quiet" from "gone"; `select.poll()` reports
    `POLLHUP`/`POLLERR`/`POLLNVAL`, so a vanished device now raises `OSError`,
    which `InputControllerEvents` already logs and stops on.
13. **`Memory.__setitem__` assigns keys as values.** For a non-tuple sequence
    key the branch read `key = tuple(key); value = tuple(key)` — the second
    line should have been `tuple(value)`, so `mem[['a','b']] = [1,2]` stored
    `'a'` and `'b'` as the *values*. The existing test only passed a tuple
    key, which takes the other branch and misses it. (Fixed in 0.1.)

---

## 3. Design decisions — all ACCEPTED

**D1 — Click disambiguation (#1097's own open TODO). ACCEPTED: defer.**
The POC fires `/click/1` immediately on release, then `/click/2` on the next
fast release, so a part bound to `/click/1` *also fires on the first click of
a double-click*. Instead, hold the click event until the fast-click window
closes and emit only the final count. `defer_clicks: bool = True`; costs
`fast_click` (200 ms) of latency on click behaviors only — press/release stay
instant.

**D2 — Long press. ACCEPTED: `hold` only.**
Implement `/event/button/X/hold`, fired once when a press passes
`long_press_time`. Defer long-click *counting* and short-long/long-short
sequences until something asks for them. `hold` covers the RC 3-channel use
case DocGarbanzo described.

**D3 — Web controller joins the event namespace. ACCEPTED.**
The web controller emits `/event/button/web_w1/press` etc. This deletes the
per-binding `web/w*`-vs-joystick branching in `path_follow.py` and
`cv_control.py` and lets one behavior map cover both input paths. Adds commit
2.5.

**D4 — Package name. ACCEPTED: `donkeycar/parts/controls/`.**

---

## 4. Commit checklist

Every commit: green `pytest`, green `mypy --strict` on the new package, no
hardware required.

### Phase 0 — Foundation (4 / 4) ✅

- [x] **0.1** `Memory.remove` uses `pop`; rewrite `events.py` as `OneShotEvents`
      — *tests:* extend `test_memory.py`; new `test_events.py` (emit/expire/re-emit, missing-key removal)
      — also typed `memory.py`, added the scoped strict-mypy config (§5) and a
      `mypy` step to CI, and fixed a latent `Memory.__setitem__` bug (see below)
- [x] **0.2** `controls/` package: `ControlChange`, `AbstractInputController`, `JsDevice` seam, typed `LinuxGameController` with defects 1, 2, 9 fixed
      — *tests:* new `test_linux_game_controller.py` + `FakeJsDevice` fixture: enumeration, name mapping, unmapped-code fallback names, axis scaling, init-event suppression, jitter filter
      — the Phase 1 test kit lives in `donkeycar/tests/fake_js.py`: `FakeJsDevice`,
      the `button_event`/`axis_event`/`init_event` builders, `duplicate_values()`,
      and `duplicate_literal_keys()` (an AST check, since a duplicate dict key is
      already gone from the built dict — this is what catches defect 7). The
      helpers have their own self-tests, and `fake_js.py` is type-checked so the
      fake cannot drift from the `JsDevice` protocol.
- [x] **0.3** `InputControllerEvents` rewrite: injected clock, deferred clicks (D1), `hold` (D2), real exception handling, retry moved into `update()`
      — *tests:* new `test_input_controller_events.py`: press/release/click ordering, multi-click counts, one-shot expiry across loops, persistent state keys, clock-driven with zero `sleep`
      — lives at `controls/events.py`; `FakeInputController` and `FakeClock` joined
      the shared test kit. A hold suppresses the click that press would otherwise
      have produced (a long press is its own gesture, not a slow click) — that was
      an open question D2 did not settle, and it is now tested.
- [x] **0.4** Fix two device-layer defects found running against a real Xbox pad
      on the car (defects 12 and 13) — `LinuxJsDevice` reads through `select.poll()`
      on a raw non-blocking descriptor instead of a buffered file object
      — *tests:* `TestLinuxJsDeviceReads` against a real `os.pipe()`, since
      `FakeJsDevice` returns immediately and cannot reproduce either bug

### Phase 1 — Gamepads, one commit each (11 / 11) ✅

Each commit adds one name map to `gamepads.py` plus its test. A gamepad is
now pure data — a `LinuxGameController` subclass declaring the class
constants `BUTTON_NAMES` and `AXIS_NAMES`, keyed by driver code:

```python
class LogitechJoystick(LinuxGameController):
    AXIS_NAMES = {0x00: 'left_stick_horz', ...}
    BUTTON_NAMES = {0x130: 'A', ...}
```

Every commit gets the same three assertions — `duplicate_literal_keys()` (no
duplicate device codes), `duplicate_values()` (no duplicate control names),
and a synthetic-event round trip through `FakeJsDevice` — which is what
catches defects 7 and 8.

**Those three are not enough on their own**, as 1.7 showed: the legacy Xbox
map passed all of them and still described a different controller. Add
whichever of these applies:

- **Pad on the bench** — pin the enumeration the real device reports, assert
  every reported control resolves to a real name, and assert the map names
  nothing the device lacks (which is how legacy's Forza mode came to be bound
  to codes that are never sent). Verify on the car before ticking the box.
- **No pad** — say so in the class docstring, and cross-check against a map
  that *was* measured on the same driver. Codes are a property of the driver,
  not the pad, so an `xpad` device must agree with the measured `xpad` device.
- **No pad and a different driver** — the cross-check weakens to "this driver
  follows the kernel's ABS conventions", which is an assumption, not a fact.
  Say which it is. And where a driver genuinely departs from the convention
  (1.3 `sixad`), assert the departure so it is not later tidied away.

The shared soundness checks live in `GamepadMapChecks` in the test kit. They
check a map against *itself* and so can never catch a map that describes the
wrong device — which is exactly how the legacy Xbox map passed for years.

- [x] **1.1** `LogitechF710` — re-landed on the new base. **Not verified against
      hardware** (no F710 available), so the tests cross-check it against the Xbox
      measurement instead: the F710 in XInput mode runs on the same `xpad` driver,
      so shared codes must mean the same thing on both pads. That check fails if
      the legacy Xbox defect is reintroduced, so it is not inert.
- [x] **1.2** `PS3` — `hid-sony`. **Partly verified on 2026-10-26** against a
      third-party clone over Bluetooth: the right stick's vertical axis, the left
      stick's horizontal axis and both triggers (see the docstring). Differs in
      shape from the Xbox-style pads: the dpad is four buttons rather than an axis
      pair, and each trigger reports twice (analog axis *and* digital button). The
      axis cross-check against the measured pad is weaker here than for the F710,
      since this is a different driver and only the ABS-code *convention* is shared
      — noted in the docstring. Also fixes the naming convention for the whole of
      Phase 1 (see `gamepads.py` module docstring): shared controls get shared
      names, pad identity lives in the face buttons.
- [x] **1.3** `PS3SixAd` — **the case that proves the cross-check is about drivers,
      not hardware.** Same physical pad as 1.2, sharing only two axis codes and one
      button code with it. `sixad` numbers axes sequentially, so the right stick sits
      on the codes that mean *triggers* everywhere else — and it reports no analog
      triggers at all. Tests assert the disagreement deliberately, so nobody later
      "fixes" it into agreement and moves steering onto a control that is never sent.
- [x] **1.4** `PS3Old` — Jessie-era `hid-sony`. A third layout for the same pad,
      agreeing with neither of the others: right stick at `0x02/0x05` here,
      `0x03/0x04` on 1.2, `0x02/0x03` on 1.3. Exposes the DualShock 3's pressure
      sensitivity as twelve extra axes. Fills a gap the legacy map left at `0x2f`,
      where a left-dpad press surfaced as an anonymous `axis(0x2f)`.
- [x] **1.5** `PS3PC` — the one PlayStation variant that is *not* a different
      layout: every code it shares with 1.2 means the same thing, and it only adds
      the pressure and tilt axes. So it subclasses 1.2 rather than restating it.
      **Resolved (Ed): they stay separate.** Merging into one map that named
      everything would name axes a given driver does not report, which is exactly how
      the legacy Forza mode became dead code. A map describes the driver in front of
      it, not the union of every driver that pad has ever had. A user whose pad reports
      `axis(0x2c)` chooses `ps3pc`; one whose pad does not chooses `ps3`. Pinned by a
      test so neither is later "completed" with the other's axes.
- [x] **1.6** `PS4` — fixes defect 7. Confirmed the AST check catches the real
      legacy map: `duplicate_literal_keys(legacy.PS4Joystick)` reports `['314',
      '315']`, i.e. `0x13a`/`0x13b`. Also resolves a disagreement between the two
      shipped Sony maps over which codes are shoulders and which are triggers, and
      drops the `pad` name for `0x13d`, which is `BTN_THUMBL`.
- [x] **1.7** `XboxOne` — done first, out of order, while the pad was on the
      bench; written from the measured capture below rather than from convention,
      and verified against the real device (every control named, no fallbacks)
- [x] **1.8** `Nimbus` — resolves defect 10 without needing a call: `hmm`/`what`
      are `0x10`/`0x11`, i.e. `ABS_HAT0X`/`ABS_HAT0Y`, the codes *measured* as the
      dpad on the Xbox pad. Named `dpad_horiz`/`dpad_vert` like every other pad
      with a hat. Its buttons run consecutively `0x130`-`0x137` because
      `hid-generic` numbers them in descriptor order, so they deliberately do not
      line up with the Xbox-style pads — asserted, so it is not tidied away.
- [x] **1.9** `WiiU` — fixes defect 8, and a worse one beside it: legacy put dpad
      *down* on `0x224`, which is not a dpad code, so that direction could never
      fire and `0x221` went unnamed. Nintendo's face buttons are transposed
      relative to every other pad (B is the bottom button), which is correct and
      is asserted so it does not look like a bug.
- [x] **1.10** `RC3Chan` — not a gamepad: two channels named `steering` and
      `throttle`, plus a switch reported as two position buttons. Shares no control
      name with any gamepad, which is the case the per-controller behavior map in
      Phase 4 has to cope with.
- [x] **1.11** `custom` — `CustomJoystick` declares nothing, so an unsupported pad
      is usable immediately with default `button(0x133)` names that tell the user
      exactly what to put in `myconfig.py`. The same layering renames one control
      on a *supported* pad without restating the map or forking a class — which is
      what 6.2 turns `donkey createjs` into.

> **No `XboxOneSwapped`.** The legacy class only swaps which stick drives
> steering and which drives throttle. That is a *behavior* binding, not a
> device naming, so in the new architecture it is a line in the Phase 4
> behavior map rather than a controller class. Dropped from Phase 1.

Legacy `controller.py` is untouched and still working throughout Phase 1, so
every one of these commits is independently mergeable.

**Measured on a real Xbox One S pad through `xpad` (2026-08-31), which the
1.7 commit must act on.** Each control was moved in isolation with pauses
between, and every axis event timestamped, so these are attributions rather
than inferences from convention. The driver reports 8 axes and 11 buttons.

| code | legacy name | verified as | how |
|---|---|---|---|
| `0x00`, `0x01` | `left_stick_horz/vert` | correct | — |
| `0x02` | `right_stick_horz` | **left trigger** | isolated squeeze at t=181.6s moved only this |
| `0x05` | `right_stick_vert` | **right trigger** | isolated squeeze at t=184.3s, and again at t=196.4s |
| `0x03` | *(unmapped)* | **right stick X** | stick pushed left at t=190.1s drove this to `-0.94`, returning to `0.0` |
| `0x04` | *(unmapped)* | **right stick Y** | stick pushed up at t=193.2s drove this to `-1.0`, returning to `0.0` |
| `0x10`, `0x11` | `dpad_horiz/vert` | correct | discrete -1 / 0 / +1 |
| `0x09`, `0x0a` | `right_trigger`, `left_trigger` | **do not exist** | absent from the driver's axis list |

Buttons unmapped by the legacy map: `0x13a` (back/view), `0x13c` (guide),
`0x13d`/`0x13e` (stick presses).

Triggers rest at `-1.0` and travel to `+1.0`; sticks rest at `0.0` and travel
both ways. That difference is what identifies them, and it also means the
legacy "Forza mode" was dead code on this driver: `magnitude()` was bound to
`right_trigger`/`left_trigger`, names that map to `0x09`/`0x0a`, which the
device never reports. So on `main` today an Xbox user's "right stick" *is*
their triggers, pegged at `-1.0` at rest, the real right stick has no name,
and Forza mode never runs.

Directions are conventional: +x is right, and up is negative on the vertical
axes.

This is the class of error the `duplicate_*` assertions cannot catch — a map
can be perfectly self-consistent and still describe a different device. Any
gamepad map we cannot verify against hardware should say so in a comment.

### Phase 2 — Non-gamepad input devices (5 / 5) ✅

- [x] **2.1** PyGame device + `PyGamePS4` map — integer-keyed, so it shares no numbering
      with the evdev PS4 map; hats expand to four pseudo-buttons. Fixed a real defect:
      PyGame reports *positions*, not events, and the legacy scan overwrote one return
      value while walking every control — so simultaneous changes were recorded but
      never reported, and a diagonal stick lost half its movement on every scan.
      `poll()` now drains a queue.
- [x] **2.2** pigpio `RCReceiver` as `AbstractInputController` — now reports three
      channels as axes and nothing else; deciding pilot mode and recording moved out
      to behavior parts, which is the whole point. Fixed: legacy `shutdown()` indexed
      its callback list with a `Channel` object, so it raised `TypeError` every time
      and never released pigpio.
- [x] **2.3** RoboHAT MM1 as `AbstractInputController` — arithmetic pinned against the
      exact readings `test_robohat.py` uses, so an MM1 car's steering feel cannot change
      quietly; that legacy test still passes untouched. Two parsing fixes: legacy split
      on `', '` exactly (so `1500,1500` parsed to nothing) and used `str.isnumeric()`
      (which rejects `1600.0`). **Resolved (Ed):** `MM1_STOPPED_PWM`,
      `MM1_MAX_FORWARD` and `MM1_MAX_REVERSE` are output-side settings only — they
      limit how hard the car drives, in `RoboHATDriver`. The input path's apparent use
      of them cancelled exactly and never had any effect, so preserving the behaviour
      was right. Now stated as a deliberate choice and pinned by tests, so nobody later
      "fixes" the unused constants and silently changes every MM1 car's throttle.
- [x] **2.4** Networked `JoyStickSub` as a device — `NetworkedController` is an ordinary
      input controller, so the `ctr.js = netwkJs` monkey-patch is gone. Wire format is
      JSON now: the old space-separated one broke on any control name containing a
      space and used `'0'` to mean "nothing", so a control named `0` was unreportable.
      Three defects fixed — a malformed message killed the receiving thread outright;
      a burst overwrote all but the last change (losing a release leaves a button stuck
      down); and `shutdown()` could never work because `recv()` blocked forever, the
      same shape as the deadlock found on the car in 0.4.
- [x] **2.5** Web controller emits button events (D3) — `WebButtonController` is an input
      controller fed from the vehicle loop, so a web push goes through the *same* event
      pump as a gamepad and gets press, release, click and multi-click for free. That is
      what let Phase 5 delete the `web/w*`-versus-joystick branching rather than port it.
      No `hold` from this controller: the web interface does not report how long a button
      was held.

### Phase 3 — Behavior parts (5 / 5) ✅

Every legacy `JoystickController` method becomes a part. These are pure
functions of their inputs, so tests are plain `run()` calls — the
highest-value tests in the whole plan, since this logic has never had any.

- [x] **3.1** driving — `UserSteering`, `UserThrottle` (deadzone, scale, direction),
      `TriggerThrottle` (the Xbox "Forza" mode). Throttle scale arrives as an *input*
      so 3.3 can change it while driving. Two safety points, both tested: an untouched
      trigger has no value in memory and reading that absence as centre would mean
      half throttle at startup; and `TriggerThrottle` takes both triggers together, so
      squeezing both cancels rather than last-writer-wins. **`JOYSTICK_DEADZONE`
      defaults to off here** — legacy applied it only to the record decision, never to
      steering or throttle. **Changed at Ed's direction:** it is now on by default
      at the shipped `JOYSTICK_DEADZONE` of 0.01. Note that is *smaller than the
      jitter measured on the test pad* (0.048-0.099), so it stops a tidy pad
      drifting but not a worn one — Phase 5 should pass `cfg.JOYSTICK_DEADZONE`
      through, and a car with loose sticks needs it raised in `myconfig.py`.
- [x] **3.2** mode + recording — `TogglePilotMode`, `ToggleRecording`,
      `AutoRecordOnThrottle`, `ShowRecordCount`, `EraseLastNRecords`. The toggles read
      their current value as an *input* rather than remembering it, so anything else
      may change the mode and they still step on from where the car actually is.
      `complete.py`'s `ToggleRecording` is superseded — in it, a manual toggle
      silently did nothing whenever auto-record was on. **Its deletion happens in
      5.1**, since deleting it now would break the template before it is rewritten.
- [x] **3.3** throttle limits — `AdjustMaxThrottle` (one part with a *signed* step,
      so up and down cannot drift apart), `ToggleConstantThrottle` and
      `ConstantThrottle`. Splitting the toggle from the part that acts on it is what
      makes constant throttle rebindable. Turning it off gives zero rather than
      handing back a stale stick reading — that would lurch at speed. This closes
      the `user/throttle_scale` loop opened in 3.1, replacing the legacy shared
      mutable field; a test drives `AdjustMaxThrottle` into `UserThrottle` to check
      the two ends meet.

      **Not carried over:** the legacy methods also wrote `self.throttle` directly
      on each press, recomputing it from a remembered last axis value. That is
      unnecessary now — `UserThrottle` recomputes from the live scale on the next
      pass — and it was the mechanism by which changing the limit could move a
      stationary car.
- [x] **3.4** safety — `EmergencyStop`, `ChaosMonkey`, `StopVehicle`. The e-stop's
      full 23-step throttle sequence is pinned against the legacy machine replayed
      verbatim; how hard a car brakes is not something to change in passing.
      **It takes the button event as an `input`, not a `run_condition`** — the stop
      spans many loop passes, so a run condition would fire it once and abandon it
      mid-sequence, leaving the car in reverse. Pressing again mid-stop is ignored
      rather than restarting.
- [x] **3.5** template-specific — **smaller than planned, deliberately.** Only
      `AdjustPid` was written: one part, signed step, replacing four closures, and it
      floors the gain at zero (legacy subtracted with no floor, and a negative gain
      inverts the controller so the car steers *away* from the line).

      The other six named parts were **not** written. `SavePath`, `LoadPath`,
      `ErasePath`, `ResetOrigin`, `EnableAiLaunch` and `IncrementBehaviorState` are
      all "call this when the event fires", which `Lambda` already does — and
      `path_follow.py` already uses it that way for its web buttons. Six one-line
      wrapper classes would be worse than the part that exists. They close over
      template locals (the path, the gps player, `cfg`), which do not belong in a
      general part anyway. Only the *binding* changes, in Phase 5. Tests pin the
      `Lambda` patterns so the claim is checked rather than assumed.

      Also deletes `donkeycar/parts/controller_events.py`, the POC — everything in
      it is now ported and nothing imported it.

### Phase 4 — Behavior mapping layer (2 / 2) ✅

This is what keeps users out of the templates: remapping a button is a
dictionary edit in `myconfig.py`.

- [x] **4.1** `BehaviorEventMapper` part + behavior-event name constants
      (`/behavior/toggle_pilot_mode`, …), built on `OneShotEvents`. **The map is
      behavior → control, not control → behavior**, because that is the question a
      user is answering, and because it lets one behavior take *several* controls —
      which is exactly the gamepad-or-web-button case the templates currently
      handle by writing every binding twice. Value is carried through unchanged, so
      a behavior can be a part's input and run condition at once. A behavior lives
      exactly as long as what caused it: one-shot events drive one-shot behaviors,
      persistent states drive persistent ones. `unknown_behaviors()` catches typos —
      a behavior nothing listens to does nothing and says nothing.
- [x] **4.2** Default `CONTROLLER_BEHAVIOR_MAP` per controller type + `custom`;
      `factory.get_input_controller(cfg)` and `get_behavior_map(cfg)`; new
      `cfg_complete.py` entries. Defaults follow the legacy bindings so muscle memory
      carries over — except where legacy named a control the driver never sends.
      **A test checks every default map against the pad it is for**, and it catches a
      dead binding when one is injected: that is the Forza-mode defect class, now
      impossible to ship. Also added `AxisButton` (scope found here, not planned):
      some pads report the dpad as buttons and others as an axis pair, so a behavior
      bound to "dpad up" needs an edge detector on the second kind. Legacy solved
      this inside the Logitech class, which is why it worked there and nowhere else.

### Phase 5 — Templates, one commit each (7 / 7) ✅

Each commit drops `isinstance(ctr, JoystickController)` and
`ctr.set_button_down_trigger(...)` in favour of `V.add(part, ...,
run_condition=BEHAVIOR_X)`. `InputControllerEvents` is added at the **top** of
the loop so every part sees events in the same iteration (§#1097).
`test_template.py` must stay green on every one.

- [x] **5.1** `complete.py` — every binding now goes through a behavior. `drive()`
      builds a working vehicle and the existing `test_drive` runs ten real loops of
      it. `add_user_controller()` rewritten; `add_behavior_mapping()` and
      `add_controller_behaviors()` added beside it. The superseded `ToggleRecording`
      class is deleted. `cfg_complete.py` gains `ERASE_LAST_N_RECORDS`,
      `THROTTLE_STEP` and `CHAOS_MONKEY_STEERING`.

      > **Known temporary regression.** `add_user_controller()` now returns the *web*
      > controller, so `isinstance(ctr, JoystickController)` in `cv_control.py` and
      > `path_follow.py` is False and their gamepad button bindings do not fire until
      > 5.2 and 5.3. Their `web/w*` bindings still work, and both templates still
      > import and run. This is the ordering constraint the plan already noted.
      > **Closed by 5.3.**
- [x] **5.2** `cv_control.py` — **the `web/w*`-vs-joystick branching is deleted, not
      ported**, which is what 2.5 was built for: each binding was written twice, once
      per route in, and both routes now name one behavior. Four PID closures with no
      floor became two `AdjustPid` parts. Verified by running the template for real
      loops on the car. Its five `*_BTN` config settings are superseded by
      `CONTROLLER_BEHAVIOR_MAP` — worth noting they named controls in the legacy
      vocabulary (`"option"`, `"R2"`), which does not match what the drivers report.
- [x] **5.3** `path_follow.py` — nine doubled bindings collapse to nine single ones.
      Verified by running the template for real loops on the car. **This closes the
      temporary regression from 5.1**: no template now depends on
      `isinstance(ctr, JoystickController)`.
- [x] **5.4** `basic.py` — not thin after all. **Its `USE_RC` path was broken on
      `main`**: it called `RCReceiver(pin, invert=True, jitter=..., no_action=...)`
      against a class whose signature is `(cfg, debug=False)`, so `USE_RC=True`
      raised `TypeError` at startup, and it bound two outputs to a `run()` returning
      four. Written against a receiver that no longer exists. Rewritten on the new
      one, in `drive()` and in the calibrate helper, which was broken identically.
      This template names its steering `user/angle`, so it binds the driving parts
      itself rather than using `complete.py`'s.

      > Separately and **not** fixed here: `basic.py` hardcodes PCA9685 and ignores
      > `DRIVE_TRAIN_TYPE`, so it cannot run on a machine without that hardware. Out
      > of scope for a controller refactor.
- [x] **5.5** `arduino_drive.py` — genuinely thin, the one template that was. A
      single `get_js_controller` call site. It has no camera, tub or pilot, so it
      binds only steering, throttle and the mode toggle rather than pulling in
      behaviors it cannot use.
- [x] **5.6** `simulator.py` — done out of order, at Ed's request. As the plan
      predicted, it carries its own inline copy of the controller logic and could not
      ride along with 5.1. Like `basic.py` it names its steering `user/angle`, so it
      binds the driving parts itself. Also gained `EraseLastNRecords`, which it
      never had — the legacy template called `ctr.set_tub()` but never bound
      anything to erasing, so the tub it passed in went unused.
- [x] **5.7** `calibrate.py` — dropped the dead `JoystickController` import, and
      `WebFpv` with it, which was unused on the same line. **No template anywhere
      now references `JoystickController`, `set_button_down_trigger`,
      `get_js_controller`, `JoyStickSub`, `ctr.js`, `MyJoystickController`,
      `print_controls`, `set_tub` or `set_deadzone`** — swept and verified, which is
      the precondition Phase 6 needs before it can delete the legacy hierarchy.

`square.py` and `just_drive.py` need no change; neither imports a controller.

Ordering constraint: 5.1 must land before 5.2 and 5.3, since both import
`add_user_controller` from `complete.py`. 5.4–5.7 are independent.

### Phase 6 — Cutover (3 / 3) ✅

> **6.1 and 6.2 had to swap.** `management/base.py` imports `CreateJoystick` at
> module scope, and the old wizard imported `JoystickCreatorController` at module
> scope, so deleting the legacy hierarchy first would have made **every** `donkey`
> command fail with an ImportError, not just `createjs`. 6.2 went first.

- [x] **6.2** *(done first)* Rework `donkey createjs` — 584 lines down to ~200, emitting
      `JOYSTICK_BUTTON_NAMES`/`JOYSTICK_AXIS_NAMES` to paste into `myconfig.py` rather
      than generating a controller class and a behavior map. A test feeds its output
      back through the factory to check the names actually take. Axis jitter below half
      travel is ignored, so a twitching stick cannot answer for the control the user
      pressed.
- [x] **6.1** Delete `Joystick`, `JoystickController`, all `*JoystickController`
      subclasses, `get_js_controller`; rewrite `test_controller.py`.
      **`parts/controller.py`: 1750 lines → 33** — just the `LocalWebController`/`WebFpv`
      re-export five templates import, plus a docstring recording where everything went.
      The old test called methods in sequence and asserted *nothing*, and was skipped
      entirely without a joystick attached; the new one asserts the legacy names are
      gone and that each moved somewhere, so the "where it went" list cannot go stale
      unnoticed.
- [x] **6.3** Docs + migration note — `CONTROLLER_MIGRATION.md`, covering every way a
      legacy config can break, with `test_migration_guide.py` checking each claim it
      makes: a guide that has drifted is worse than none. Writing it **found three
      `CONTROLLER_TYPE` values that no longer worked** — `pygame` and `xboxswapped`
      were dropped by the new factory (regressions introduced in 4.2), and `mock` had
      never worked at all on `main`, importing a `MockController` from a module that
      never defined one. All twelve legacy values now build and have a behavior map.

**Total: 38 commits.** Phases 0–2 were mergeable independently; Phases 5–6
landed together as planned, except that 6.1 and 6.2 had to swap. Phases 0–2 are mergeable independently; Phases 5–6
must land together to keep the templates working.

### Phase 7 — Xbox over Bluetooth (4 / 4) ✅

> **Why.** The `xbox` map (1.7) was measured over USB, on the `xpad` driver.
> Over Bluetooth the same pad is driven by `hid-microsoft` and reports
> different codes — and Bluetooth is how nearly everyone connects it.
> Measured on a 'Xbox Wireless Controller' (045e:02fd) on Debian trixie,
> kernel 6.18, 2026-10-07, each control moved in isolation:
>
> | Control | USB (`xpad`) | Bluetooth (`hid-microsoft`) |
> |---|---|---|
> | right stick horz / vert | 0x03 / 0x04 | **0x02 / 0x05** |
> | left trigger / right trigger | 0x02 / 0x05 | **0x0A / 0x09** (rest −1.0) |
> | left stick, dpad | 0x00/0x01, 0x10/0x11 | same |
> | A B X Y LB RB menu, stick clicks | 0x130…0x13E | same |
> | view, xbox | 0x13A, 0x13C | **not on js0 at all** |
>
> The driver also declares 0x132, 0x135, 0x138, 0x139, 0x13A and 0x13C, but
> none of them moved. View and Xbox appear to be sent as keyboard keys
> (the device advertises `KEY_BACK` and `KEY_HOMEPAGE`), which `joydev` does
> not carry — so over Bluetooth they cannot be bound at all.
>
> That breaks the `xbox` STOP_VEHICLE gesture (Xbox while holding View).
> **Decided:** over Bluetooth, STOP_VEHICLE is *both triggers squeezed fully*.
> Nothing else is bound to the triggers by default, and squeezing both at once
> is deliberate.

- [x] **7.1** Save the capture tool as `python -m donkeycar.parts.controls.capture`.
      It walks through each control, records which code moved and over what
      range, and writes JSON. Adds a **redo** option (`r` after a step's result)
      so a fumbled step can be repeated without starting over. Tests drive it
      with a fake device and scripted input.
- [x] **7.2** STOP_VEHICLE on a chord of two axes. A new `AxisChord` part
      outputs true on the one pass where both axes are past +0.6 (80% of a
      trigger's squeeze from rest), whichever was squeezed first — so the order
      the triggers go in does not matter, and holding them does not fire twice.
      `complete.py` uses it when STOP_VEHICLE is bound to an axis, and keeps the
      button path otherwise: wired the button way, a released trigger's -1.0
      is truthy and would stop the car on the first pass — a test pins that.
      A trigger with no value yet in memory counts as released.
- [x] **7.3** Add `xbox-usb`: the 1.7 map, unchanged, as `XboxOneUsbJoystick`
      with its existing behavior map. The tests that cross-check other `xpad`
      pads (F710) and conventional layouts against "the Xbox pad" now name the
      USB class, which is the one they meant. `xbox` is unchanged in this commit.
- [x] **7.4** Make `xbox` the Bluetooth map: `XboxOneJoystick` gets the measured
      codes above and names neither view nor xbox; its behavior map moves
      STOP_VEHICLE to the triggers. `xboxswapped` follows `xbox` (it is a
      binding, not hardware). The docstring's "Bluetooth does not work" note
      becomes the trixie pairing note. Migration guide and the `CONTROLLER_TYPE`
      option lists in the templates updated. *(Correction, made in 8.2: this
      also added a test that every default map binds only controls its pad
      names, and its commit message claimed the Bluetooth map would otherwise
      have passed every test. Both were wrong —
      `TestTheDefaultMapsAreSound` already did exactly that check, and does
      catch View and Xbox. 8.2 removed the duplicate.)*

### Phase 8 — RC receivers in the templates (2 / 2) ✅

> **Why.** Reported on the PR by someone testing an MM1 at `896353f7`, and
> reproduced here through the real `add_user_controller()` /
> `add_controller_behaviors()` wiring. `MM1` and `pigpio_rc` are both RC
> receivers that the templates build themselves rather than through
> `get_input_controller()`, so neither ever got a default behavior map —
> and `test_all_but_custom_have_a_behavior_map` never listed them.
>
> | Forward stick at +0.5 | Default config | Bindings added by hand |
> |---|---|---|
> | MM1 → `user/throttle` | 0.0 — never arrives | **−0.25** — reversed |
> | pigpio_rc → `user/throttle` | 0.0 — never arrives | **−0.25** — reversed |
>
> Two defects. No map, so input stops at the event layer. And once bound,
> throttle goes through `UserThrottle(direction=JOYSTICK_THROTTLE_DIR)`,
> whose default −1.0 exists because a gamepad stick reads negative when
> pushed *up*. An RC receiver already reads positive-forward; legacy never
> applied the joystick inversion to either.
>
> Legacy also wrote RC input to `user/throttle` unscaled. Now it is
> multiplied by `JOYSTICK_MAX_THROTTLE` (0.5 by default), so even with the
> sign fixed an upgraded RC car would run at half power.
>
> **Out of scope, recorded:** `cfg_complete.py` lists `pigpio_rc` but has had
> no `STEERING_RC_GPIO` / `THROTTLE_RC_GPIO` / `DATA_WIPER_RC_GPIO` /
> `PIGPIO_*` since #1220 on `main`, so `pigpio_rc` on the complete template
> raises `AttributeError` at startup — on `main` too. Legacy `pigpio_rc` also
> held the pilot mode at `local` while the third-channel switch was up; that
> switch stays unbound here, since binding an axis state straight to
> `TOGGLE_PILOT_MODE` would toggle the mode on every pass.

- [x] **8.1** RC throttle is forward-positive. `get_control_scaling(cfg)`,
      next to `get_behavior_map()`, returns direction +1.0 and scales of 1.0
      for `MM1` and `pigpio_rc`, and the `JOYSTICK_*` settings for everything
      else; `complete.py` and `simulator.py` use it. Same for the scale: RC throttle and steering are
      not scaled by `JOYSTICK_MAX_THROTTLE` / `JOYSTICK_STEERING_SCALE`, as in
      legacy — the transmitter's endpoints and `MM1_MAX_FORWARD` are the
      limits. `basic.py`'s RC path changes to match. A deliberately reversed
      receiver is fixed where legacy fixed it: the transmitter's reverse
      switch, or `PIGPIO_INVERT`. The config templates say
      `JOYSTICK_THROTTLE_DIR` and `JOYSTICK_MAX_THROTTLE` are for gamepads.
      Unit tests, plus `basic.py`'s RC path through a real drive loop (skipped
      where `albumentations` is missing, since `basic.py` imports it).
- [x] **8.2** Default behavior maps for `MM1` and `pigpio_rc`: steering and
      throttle. A template integration test, as the reviewer asked, feeds
      MM1 serial lines and `pigpio_rc` pulse widths through the real template
      wiring with **no custom map**, and asserts propagation to
      `user/steering` / `user/throttle`, forward and reverse signs, and return
      to neutral. A new test reads the `CONTROLLER_TYPE` options
      `cfg_complete.py` offers and requires each to be buildable and, but for
      `custom`, to have a map — the factory-only checks are the gap that let
      this through. `RC_RECEIVER_TYPES` names each receiver's class, so the
      existing check that a map binds only real controls now covers these too.

### Phase 9 — Controller input reaches the drivetrain (2 / 2) ✅

> **Why.** Reported in review at `13e9c22b`, and reproduced by running
> `complete.drive()` itself with a scripted gamepad and a recording
> drivetrain: with the throttle stick pushed forward and held, the
> drivetrain receives `(0.0, 0.0)` on every pass. **No physical controller
> can drive a car built from `complete.py`, `cv_control.py` or
> `path_follow.py` on this branch.**
>
> Two defects, and fixing either alone is not enough:
>
> 1. **Order.** `add_controller_behaviors()` is called after `DriveMode`,
>    the drivetrain and the tub writer. The controller's steering and
>    throttle land in memory after their consumers have run, and the next
>    pass starts with `LocalWebController` writing its own values (0.0 unless
>    the web page is driving) over them. The emergency-stop braking sequence
>    is lost the same way.
> 2. **A held stick.** `UserSteering`/`UserThrottle` run only on the pass
>    where the control moves. Moved earlier, a stick held still would drive
>    for one pass and then lose to the web controller's 0.0 on the next.
>    Legacy did not have this problem because its joystick part output its
>    position on every pass, after the web controller.
>
> `basic.py` and `simulator.py` are not affected: `basic.py`'s web controller
> writes `webcontroller/angle`, and `simulator.py` adds no web controller when
> a physical one is configured.
>
> **Precedence, as legacy:** once the physical controller has reported a
> position it owns steering and throttle, and the web page's sliders do
> not. Until it has reported anything, the web page drives.
>
> **Open decision — Forza mode (deferred by Ed, 2026-10-13).** No template
> wires `THROTTLE_FORWARD` / `THROTTLE_REVERSE` to `TriggerThrottle`, so the
> migration guide's "Forza mode" recipe binds behaviors nothing uses and
> silently does nothing. To decide: wire it in the templates (and how it
> shares `user/throttle` with `THROTTLE` when both are bound), or drop the
> recipe and the two behaviors. Note that on `xbox` the triggers are also
> the default stop gesture.

- [x] **9.1** The driving parts hold their position. `UserSteering`,
      `UserThrottle` and `TriggerThrottle` run on every pass: on a pass with a
      new position they compute and remember it, and on a pass without one
      they return the remembered value — or `None` until the control has
      reported at all, which the vehicle loop does not write, so the web page
      drives until then. The templates drop the run condition that made
      them event-only — in `complete.py`, `simulator.py`, `basic.py` and
      `arduino_drive.py`. Unit tests; no visible change on its own, since the
      order still puts these parts after their consumers (checked: a held
      stick now survives every pass in memory, and the drivetrain still
      receives 0.0).
- [x] **9.2** Driving and safety behaviors run before their consumers.
      `add_controller_behaviors()` splits in two: `add_driving_behaviors()` —
      steering, throttle, constant throttle, chaos monkey, throttle limits,
      emergency stop, pilot mode, the recording toggle and stop-vehicle — is
      called straight after `add_user_controller()` in `complete.py`,
      `cv_control.py` and `path_follow.py`; `add_record_behaviors()` — erase
      records and show record count, which need the tub — stays where the
      tub exists. An integration test drives `complete.drive()` with a
      scripted gamepad and a recording drivetrain: a held stick reaches the
      drivetrain on every pass, centring it returns to neutral, and the
      emergency-stop sequence reaches the drivetrain. The same test checks
      `cv_control` and `path_follow` put the driving parts before `DriveMode`
      (`path_follow` from its source, since it imports `distutils` and
      cannot be imported on Python 3.12+).
      **Found while testing it:** with 9.1's held position, a stick still
      held forward drove the car off again the moment an emergency stop
      finished, and so did constant throttle. Legacy's stop set the throttle
      to zero until the stick moved and turned constant throttle off.
      `UserThrottle` now takes `user/estop` and lets go of the stick while a
      stop is in progress, and the stop clears `user/constant_throttle`.
      The 8.2 RC test moved onto the same harness, so it too checks the
      drivetrain rather than memory.

### Phase 10 — Letting go of a held stick (2 / 2) ✅

> **Why.** Copilot review of `352d9d7d`
> ([r4242814034](https://github.com/autorope/donkeycar/pull/1249#discussion_r4242814034)):
> a disconnected controller only stops its polling thread. Reproduced with
> the drive harness: stick forward, then the pad's `poll()` raises `OSError`
> — the drivetrain keeps receiving +0.5 indefinitely. 9.1 made this
> dangerous: `UserThrottle` now holds the stick's last position, so a lost
> pad's last throttle is held for ever. The PR's hardware test plan, T5.5,
> expects "a log line saying the controller disconnected, and the loop
> stops".
>
> The same cause breaks T4.5 ("turning [constant throttle] off gives zero,
> not a lurch to whatever the stick reads"). Reproduced: stick held at 60%,
> constant throttle on, then off — the drivetrain gets 0.0 for one pass and
> then lurches back to 0.3. Legacy set the throttle to 0 until the stick
> moved. 9.2 already fixed the emergency-stop case of this; these are the
> other two.
>
> **Decided (Ed, 2026-10-13): a lost controller stops the vehicle**, rather
> than a failsafe that keeps the loop running. A Bluetooth pad that goes to
> sleep mid-run therefore ends the program.
>
> **Out of scope, recorded:** `Vehicle.stop()` relies on each drivetrain's
> `shutdown()` to leave the motor at neutral. `PWMThrottle` does; some
> others do nothing. That affects every way the loop ends, not just this
> one, so here the last pass is made to send zero throttle explicitly.

- [x] **10.1** A lost controller stops the vehicle. `InputControllerEvents`
      publishes `CONTROLLER_LOST` once its device fails — an `OSError` from
      `poll()`, or any error that ends polling — distinct from an ordinary
      shutdown. `add_driving_behaviors()` binds it: on that pass the user
      throttle and steering go to 0.0 and the mode to `user`, so the
      drivetrain's last command is neutral whatever was driving, and
      `StopVehicle` ends the loop. Tests: the event pump publishes it on a
      disconnect and not on a shutdown; through `complete.drive()`, a pad
      lost mid-acceleration gives the drivetrain 0.0 and the loop ends, in
      autopilot too. The migration guide says so, since `main` carried on.
- [x] **10.2** A held stick is released whenever something else takes the
      throttle. 9.2 gave `UserThrottle` one such signal, the emergency stop;
      it becomes a general "let go" input taking any number of them —
      emergency stop, constant throttle on, controller lost — and forgets
      the held position while any is true, so afterwards the throttle stays
      at zero until the stick moves, as legacy did. Test through
      `complete.drive()`: T4.5 as written — stick held, constant throttle on
      then off — gives zero, not the stick's value.

> **Verified on hardware (Ed, 2026-10-13)**, Phases 9 and 10 together at
> `160aa3da`: a fresh `complete` car (`~/mycar1249`, wheels off the ground),
> an Xbox Wireless Controller over Bluetooth (`CONTROLLER_TYPE = 'xbox'`),
> Raspberry Pi on Debian trixie. All passed — a held stick keeps the motor
> running; Y brakes and the motor stays stopped with the stick still held,
> then drives again once it moves; T4.5, constant throttle off gives zero;
> both triggers end the loop; and T5.5, switching the pad off logs the
> disconnect, stops the motor and ends the loop.

### Phase 11 — `basic.py`'s gamepad toggles (1 / 1) ✅

> **Why.** Item 3 of the GPT Astra review Ed posted on the PR
> ([comment](https://github.com/autorope/donkeycar/pull/1249#issuecomment-6154931489)).
> Reproduced on the car through `basic.drive()` with a scripted Xbox pad:
> pressing A (toggle pilot mode) and B (toggle recording) changes nothing —
> `user/mode` stays `'user'` and `recording` stays `False`.
>
> `basic.py`'s joystick branch adds a `LocalWebController` after
> `TogglePilotMode` and `ToggleRecording`, giving it only the camera image as
> input. It writes its own `user/mode` and `recording` on every pass, so it
> undoes both toggles in the same pass they happen. Legacy `basic.py` had no
> web controller in this branch — the gamepad was the controller — so this
> came in with Phase 5. Its RC branch also adds one that writes the mode, but
> that is legacy's own wiring and nothing else toggles the mode there.
>
> **Open decision — item 4, `simulator.py` starts with no mode (noted, not
> planned; Ed, 2026-10-13).** In the simulator's joystick branch nothing
> writes `user/mode` until the first toggle press. Legacy's joystick wrote
> `'user'` from the start; now `user/mode` is `None`, which `PilotCondition`
> reads as "not user", so the car starts under the pilot and ignores the
> sticks until the mode is toggled. Ed: some users may depend on that
> behaviour, so it is to be decided before anything changes it.

- [x] **11.1** `basic.py`'s web controller takes the current mode and
      recording state as inputs — `'cam/image_array', 'tub/num_records',
      'user/mode', 'recording'`, as `complete.py` gives it — so it adopts a
      toggled value rather than writing its own over it, and the web page
      shows what the gamepad set. A test drives `basic.drive()` with a
      scripted pad: A cycles the mode, B toggles recording, and each sticks
      on the passes after. `basic.py` imports `albumentations`, so the test
      skips without it and runs on the car — where it fails against the
      unfixed `basic.py` and passes with the fix.

### Phase 12 — An emergency stop that brakes only what is moving (2 / 2) ✅

> **Why.** Found by Ed on hardware, 2026-10-26: `~/mycar1249`, wheels off
> the ground, throttle at zero, with both a PS3 pad and the Xbox pad —
> pressing the emergency stop spins the motor on and off. The car was
> standing still, so there was nothing to stop.
>
> `EmergencyStop` sends the sequence legacy did, whatever the car is doing:
> full reverse at the throttle limit (−0.5 on this car), +0.01, full
> reverse again, then back to zero in steps of 0.05 — about 0.65 s at
> 20 Hz. It assumes an ESC that reads reverse as "brake" while moving
> forward. This car's ESC drives reverse directly, and its motor turns past
> about ±0.25, so the sequence becomes roughly half a second of reverse
> drive.
>
> **Decided (Ed, 2026-10-26):** the reverse should be proportional to the
> forward throttle, and allow for a fast car that is still coasting after
> the throttle is released. Once the throttle has been at zero for long
> enough, an emergency stop applies no reverse at all.
>
> **Design.** `EmergencyStop` keeps a decaying estimate of how hard the car
> was recently driven forward. On each pass it reads the throttle the drivetrain was
> given on the previous pass (`throttle`, written by `DriveMode`), so it
> covers the pilot and constant throttle as well as the stick; templates
> that do not pass it fall back to `user/throttle`. The estimate takes any
> new forward throttle at once, and otherwise falls linearly to zero over
> `ESTOP_COAST_TIME` seconds (default 1.0) from its last peak. On a stop,
> the brake level *b* is the estimate at that moment: the sequence is −*b*,
> neutral, −*b*, then back to zero in `recovery_step` steps. If *b* is 0,
> the throttle goes straight to 0. Either way the mode drops to `user`,
> recording stops and `user/estop` is true for that pass, so `UserThrottle`
> still releases a held stick (10.2). The reverse no longer depends on the
> throttle limit, so `user/throttle_scale` and `default_scale` go.
>
> **Out of scope, recorded:** a car driving *backwards* gets a plain stop
> (throttle 0), not a forward brake pulse — legacy did not brake reverse
> either. `~/mycar1249/manage.py` is a copy of the template and Ed's to
> edit; until it passes `throttle` to the stop, it falls back to
> `user/throttle` and so does not brake for the pilot.

- [x] **12.1** `EmergencyStop` brakes in proportion to recent forward
      throttle. New input for the drivetrain's last throttle, a
      `coast_time` and an injectable clock; `default_scale` and the
      throttle-scale input removed, and `complete.py`'s call drops them in
      the same commit so the inputs still line up. Unit tests with a fake clock: standing
      still (never driven, or released longer ago than `coast_time`) gives
      0.0 and no reverse; driving at 0.5 gives −0.5, neutral, −0.5, then
      back to zero; released half the coast time ago gives −0.25; the pilot's
      throttle counts as well as the user's; and a stop still sets the mode,
      recording and `user/estop` as before.
- [x] **12.2** `complete.py` passes `throttle` to the stop and
      `ESTOP_COAST_TIME` from the config (`cfg_complete.py` gets the
      setting, and the template reads it with a default so older car
      directories still start). Tests through `complete.drive()`: at a
      standstill the drivetrain never gets a negative throttle; with the
      stick held at 0.5 it gets −0.5 then returns to zero; in autopilot it
      brakes with the pilot's throttle. Hardware check for Ed: wheels off
      the ground, e-stop at zero throttle gives no movement; stick forward,
      then e-stop, gives a short reverse kick.

> **Hardware check: not yet done.**

### Proposed follow-up — `basic.py`'s drivetrain (not started; outside the task count)

> **Postponed (Ed, 2026-10-13).** `basic` is not an important template, and
> the templates may be thinned out in a separate PR — which could remove
> `basic.py` rather than fix it. Nothing below is to be done on this branch;
> it stays here so that PR has the findings.

> **Found (Ed, 2026-10-13)** while trying 11.1 on hardware: a new `basic`
> car (`~/mycar-basic-1249`) fails at startup, before any controller code
> runs:
>
> ```
> File ".../Adafruit_GPIO/I2C.py", line 55, in get_default_bus
>     raise RuntimeError('Could not determine default I2C bus for platform.')
> ```
>
> **Not caused by this branch**: `basic.py`'s drivetrain code is identical on
> `main`. `cfg_basic.py` ships `PCA9685_I2C_BUSNUM = None`, which asks the
> deprecated Adafruit library to detect the bus, and its platform detection
> returns "unknown" (0) on a Raspberry Pi 4 Model B on Debian trixie — and on
> Jetsons, whose users have always had to set the bus. The car's PCA9685 is
> on bus 1, address 0x40 (`~/mycar` drives it as `PCA9685.1:40`).
> `complete.py` never hits this, because its pin strings name the bus.
>
> Workaround for the hardware check, in `myconfig.py`:
> `PCA9685_I2C_BUSNUM = 1` (or `DRIVE_TRAIN_TYPE = "MOCK"` to skip the
> PCA9685 entirely), plus `USE_JOYSTICK_AS_DEFAULT = True` — `basic.py` has
> no `--js` flag, so without it the gamepad is never used.
>
> **A larger defect behind it.** `cfg_basic.py` advertises seven drivetrain
> types — `SERVO_ESC`, `DC_STEER_THROTTLE`, `DC_TWO_WHEEL`,
> `SERVO_HBRIDGE_PWM`, `PIGPIO_PWM`, `MM1`, `MOCK` — but `basic.py` checks
> only for `MOCK` and sends every other value to the deprecated PCA9685
> servo/ESC path. A `basic` car configured for `DC_TWO_WHEEL` or `MM1`
> silently tries to drive a PCA9685 it does not have.
>
> **Options considered**, smallest first:
>
> 1. **Default the bus to 1** — one line in `cfg_basic.py`,
>    `PCA9685_I2C_BUSNUM = 1`. On the Raspberry Pis the library did
>    recognise, detection always answered 1; where it does not, it fails. So
>    this keeps what worked and fixes what did not, and anyone on a
>    different bus overrides it in `myconfig.py` as they already must.
>    Recommended if `basic.py` is kept, as a one-line PR to `main` like #1254.
> 2. **Fall back to bus 1 in `parts/actuator.py`'s `PCA9685`** when no bus is
>    given and detection fails. **Not recommended**: that class is shared
>    and deprecated, and its bus override works by replacing
>    `Adafruit_GPIO.I2C.get_default_bus` for the whole process, so the change
>    reaches past `basic` for no gain over option 1.
> 3. **Give `basic.py` `complete.py`'s drivetrain** — call `add_drivetrain()`,
>    which supports every advertised type through the pin-based
>    `PWM_STEERING_THROTTLE` setup. Needs: mapping `basic.py`'s
>    `angle`/`throttle` onto the `steering`/`throttle` that `add_drivetrain`
>    reads (a `Pipe` or renamed `DriveMode` outputs); a `PWM_STEERING_THROTTLE`
>    block in `cfg_basic.py`; and a compatibility path so existing users'
>    `STEERING_CHANNEL` / `THROTTLE_CHANNEL` / `PCA9685_I2C_*` keep working —
>    mapped onto pin strings, or `SERVO_ESC` kept as the legacy path. One or
>    two commits, but it changes every existing `basic` user's configuration
>    and `basic` is meant to stay minimal, so it wants its own plan and a
>    hardware check on more than one drivetrain type. **Open decision.**
>
> Neither 1 nor 3 depends on this branch.

- [ ] *(postponed, option 1)* PR to `main`: `PCA9685_I2C_BUSNUM = 1` in
      `cfg_basic.py`, with a comment saying why and how to override it.
- [ ] *(postponed, option 3 — open decision)* `basic.py` uses
      `add_drivetrain()`, with a compatibility path for existing configs.

---

## 5. Type-hint and test standards

- Add a scoped strict-mypy block to `pyproject.toml`
  (`[[tool.mypy.overrides]] module = "donkeycar.parts.controls.*"`,
  `strict = true`) rather than turning strict on repo-wide. `mypy` is already
  a `dev` dependency; add a `mypy` step to `python-package.yml`.
- No `Any` in the new package. `Protocol` for the device seam, `NamedTuple`
  for value types, `abc.ABC` for the device base, PEP 604 unions, PEP 585
  builtin generics. Drop `typing_extensions` (defect 5).
- Tests use the injected clock — **no `time.sleep` in any test**, so the
  fast-click and hold logic is deterministic. Note `pytest.ini` sets
  `reruns = 3`, which would otherwise paper over exactly this kind of flake.
- CI runs 3.12 today while the Pi targets 3.13 (`PYTHON312_MIGRATION.md`).
  Worth adding 3.13 to the CI matrix for this package, since none of it needs
  TensorFlow.

---

## 6. Suggested first step

Phase 0.2 is the keystone — the `JsDevice` seam is what makes the twelve
gamepad commits testable, and getting it wrong means redoing Phase 1. Build
0.1–0.3 and one gamepad (PS3, the most widely used), then pause to run it on
the real car before grinding through the remaining eleven maps.
