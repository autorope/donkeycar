# Plan: finish the game-controller event refactor (#1097)

**Progress: 2 / 36 commits.**
Phase 0 ▓▓░ · Phase 1 ░░░░░░░░░░░░ · Phase 2 ░░░░░ · Phase 3 ░░░░░ ·
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
   last, so **`L3` and `R3` are unreachable on PS4 today**. (Phase 1, PS4
   commit; the duplicate-key test catches it.)
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
11. **`Memory.__setitem__` assigns keys as values.** For a non-tuple sequence
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

### Phase 0 — Foundation (2 / 3)

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
- [ ] **0.3** `InputControllerEvents` rewrite: injected clock, deferred clicks (D1), `hold` (D2), real exception handling, retry moved into `update()`
      — *tests:* new `test_input_controller_events.py`: press/release/click ordering, multi-click counts, one-shot expiry across loops, persistent state keys, clock-driven with zero `sleep`

### Phase 1 — Gamepads, one commit each (0 / 12)

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

- [ ] **1.1** `LogitechF710` — re-land the POC map on the new base
- [ ] **1.2** `PS3`
- [ ] **1.3** `PS3SixAd`
- [ ] **1.4** `PS3Old`
- [ ] **1.5** `PS3PC`
- [ ] **1.6** `PS4` — fixes defect 7 (`L3`/`R3` unreachable)
- [ ] **1.7** `XboxOne`
- [ ] **1.8** `XboxOneSwapped` — mapping-only, no new device
- [ ] **1.9** `Nimbus` — needs a call on the `hmm` / `what` axis names (defect 10)
- [ ] **1.10** `WiiU` — fixes defect 8 (`'PAD_DOWN,'`)
- [ ] **1.11** `RC3Chan`
- [ ] **1.12** `custom` — the `donkey createjs` name dict

Legacy `controller.py` is untouched and still working throughout Phase 1, so
every one of these commits is independently mergeable.

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
- [ ] **3.5** template-specific — `EnableAiLaunch`, `IncrementBehaviorState`, `SavePath`/`LoadPath`/`ErasePath`/`ResetOrigin`, `AdjustPidP`/`AdjustPidD`

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

**Total: 36 commits.** Phases 0–2 are mergeable independently; Phases 5–6
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
