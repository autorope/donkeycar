# Plan: finish the game-controller event refactor (#1097)

**Progress: 11 / 36 commits.**
Phase 0 ▓▓▓▓ · Phase 1 ▓▓▓▓▓▓▓░░░░ · Phase 2 ░░░░░ · Phase 3 ░░░░░ ·
Phase 4 ░░ · Phase 5 ░░░░░░░ · Phase 6 ░░░

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
8. **`WiiU` button `548: 'PAD_DOWN,'`** — trailing comma inside the string.
   (Phase 1, WiiU commit.)
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
    the public map. (Phase 1, Nimbus commit — needs a call on real names.)
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

### Phase 1 — Gamepads, one commit each (7 / 11)

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
- [x] **1.2** `PS3` — `hid-sony`. **Not verified against hardware.** Differs in
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
      **Open question for someone with the hardware:** if this is the same driver
      with more axes surfaced, then 1.2 is not different but *incomplete*, and a Pi
      user is getting anonymous `axis(0x2c)` events for pressure the pad really
      sends — in which case these two should merge.
- [x] **1.6** `PS4` — fixes defect 7. Confirmed the AST check catches the real
      legacy map: `duplicate_literal_keys(legacy.PS4Joystick)` reports `['314',
      '315']`, i.e. `0x13a`/`0x13b`. Also resolves a disagreement between the two
      shipped Sony maps over which codes are shoulders and which are triggers, and
      drops the `pad` name for `0x13d`, which is `BTN_THUMBL`.
- [x] **1.7** `XboxOne` — done first, out of order, while the pad was on the
      bench; written from the measured capture below rather than from convention,
      and verified against the real device (every control named, no fallbacks)
- [ ] **1.8** `Nimbus` — needs a call on the `hmm` / `what` axis names (defect 10)
- [ ] **1.9** `WiiU` — fixes defect 8 (`'PAD_DOWN,'`)
- [ ] **1.10** `RC3Chan`
- [ ] **1.11** `custom` — the `donkey createjs` name dict

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

### Phase 2 — Non-gamepad input devices (0 / 5)

- [ ] **2.1** PyGame device + `PyGamePS4` map — integer-keyed maps; hats expand to buttons
- [ ] **2.2** pigpio `RCReceiver` as `AbstractInputController` — restructure: today it's a full part emitting steering/throttle/mode/recording, not a `poll()` device
- [ ] **2.3** RoboHAT MM1 as `AbstractInputController` — same restructure; `test_robohat.py` already covers `read_serial()` and must keep passing
- [ ] **2.4** Networked `JoyStickSub` as a device — replaces the `ctr.js = netwkJs` monkey-patch in the templates
- [ ] **2.5** Web controller emits button events (D3)

### Phase 3 — Behavior parts (0 / 5)

Every legacy `JoystickController` method becomes a part. These are pure
functions of their inputs, so tests are plain `run()` calls — the
highest-value tests in the whole plan, since this logic has never had any.

- [ ] **3.1** driving — `UserSteering`, `UserThrottle` (deadzone, scale, direction), `TriggerAxisThrottle` (Xbox "Forza" mode from `magnitude()`)
- [ ] **3.2** mode + recording — `TogglePilotMode`, `ToggleRecording`, `AutoRecordOnThrottle`, `ShowRecordCount`, `EraseLastNRecords`; deletes `complete.py`'s `ToggleRecording`, which #1097 explicitly calls out for removal
- [ ] **3.3** throttle limits — `AdjustMaxThrottle`, `ToggleConstantThrottle`
- [ ] **3.4** safety — `EmergencyStop` (the 4-state ES machine as a part), `ChaosMonkey`, `StopVehicle`
- [ ] **3.5** template-specific — `EnableAiLaunch`, `IncrementBehaviorState`, `SavePath`/`LoadPath`/`ErasePath`/`ResetOrigin`, `AdjustPidP`/`AdjustPidD`; also deletes `donkeycar/parts/controller_events.py`, the POC, whose parts have all been ported by this point

### Phase 4 — Behavior mapping layer (0 / 2)

This is what keeps users out of the templates: remapping a button is a
dictionary edit in `myconfig.py`.

- [ ] **4.1** `BehaviorEventMapper` part + behavior-event name constants (`/behavior/toggle_pilot_mode`, …), built on `OneShotEvents`
- [ ] **4.2** Default `CONTROLLER_BEHAVIOR_MAP` per controller type + `custom`; `factory.get_input_controller(cfg)`; new `cfg_*.py` entries

### Phase 5 — Templates, one commit each (0 / 7)

Each commit drops `isinstance(ctr, JoystickController)` and
`ctr.set_button_down_trigger(...)` in favour of `V.add(part, ...,
run_condition=BEHAVIOR_X)`. `InputControllerEvents` is added at the **top** of
the loop so every part sees events in the same iteration (§#1097).
`test_template.py` must stay green on every one.

- [ ] **5.1** `complete.py` — the big one: mode toggle, recording, erase-N, e-stop, throttle scaling, constant throttle, chaos monkey, AI launch, behavior increment; also rewrites `add_user_controller()`, which `cv_control.py` and `path_follow.py` both import
- [ ] **5.2** `cv_control.py` — toggle recording, PID tuning buttons
- [ ] **5.3** `path_follow.py` — save/load/erase path, reset origin, PID tuning
- [ ] **5.4** `basic.py` — thin: `get_js_controller` call site plus the `ctr.js = netwkJs` monkey-patch
- [ ] **5.5** `arduino_drive.py` — thin: `get_js_controller` call site, no button bindings
- [ ] **5.6** `simulator.py` — carries its own inline copy of the `add_user_controller` logic plus `circle`/`L1`/AI-launch bindings; does not share `complete.py`'s helper
- [ ] **5.7** `calibrate.py` — imports `JoystickController` but never uses it; drop the dead import so nothing references the legacy module before Phase 6 deletes it

`square.py` and `just_drive.py` need no change; neither imports a controller.

Ordering constraint: 5.1 must land before 5.2 and 5.3, since both import
`add_user_controller` from `complete.py`. 5.4–5.7 are independent.

### Phase 6 — Cutover (0 / 3)

- [ ] **6.1** Delete `Joystick`, `JoystickController`, all `*JoystickController` subclasses, `get_js_controller`; move `RCReceiver`; rewrite `test_controller.py` (it imports `PS3Joystick`/`PS3JoystickController` directly and will not survive)
- [ ] **6.2** Rework `donkey createjs` (`management/joystick_creator.py`, 584 lines) to emit a name dictionary instead of a controller class
- [ ] **6.3** Docs + `myconfig.py` template + a migration note for users with a custom `my_joystick.py`

**Total: 35 commits.** Phases 0–2 are mergeable independently; Phases 5–6
must land together to keep the templates working.

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
