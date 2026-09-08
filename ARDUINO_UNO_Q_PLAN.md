# Plan: run donkeycar on the Arduino Uno Q

**IN PROGRESS — 13 / 19 tasks.**

Phase 0 ▓▓▓ · Phase 2 ▓▓▓ · Phase 3 ░░░ · Phase 4 ░░ · Phase 5 ▓▓▓▓▓▓▓░

> Convention: tick a box in §4 in the same commit that does the work, so the
> checklist and the git history never disagree. Update the counter above too.

---

## 1. Where things stand

### 1.1 The board

Verified over ssh against a real board on 2026-09-07:

| | |
|---|---|
| OS | Debian 13 (trixie), `6.16.7` kernel |
| Arch | aarch64, 4× Kryo-V2 (Qualcomm QRB2210) |
| RAM | 3.6 GB total, ~750 MB available (App Lab + chromium hold ~2.8 GB) |
| Disk | 9.8 GB root, **2.4 GB free** |
| Python | system CPython 3.13.5; venv at `~/env` (`include-system-site-packages = true`) |
| uv | 0.12.10 at `~/.local/bin/uv` |
| Camera | `1b3f:1162` Macally mZoomCam on `/dev/video0` |
| I2C | `/dev/i2c-0`, `-1`, `-2` — all `root:i2c 0660` |
| GPIO | `/dev/gpiochip0..2` (libgpiod; **no** sysfs, **no** RPi.GPIO) |
| SPI | `/dev/spidev0.0`, `root:root 0600` |

`donkeycar 5.4.dev1` is installed editable from
`/home/arduino/projects/donkeycar`, now on branch `arduino-uno-q` at
`ba25266b` (same commit as the Mac).

### 1.2 What already works, verified on the hardware

- **Install**, after `sudo apt-get install build-essential python3-dev`.
  The only thing that needed a compiler was `spidev`, which has no wheel and
  arrives via `Adafruit_PCA9685` → `Adafruit-GPIO` → `spidev`. Everything
  else in `[pi,dev]` resolved to prebuilt aarch64 wheels.
- **Inference.** `ai-edge-litert 2.2.0` imports, so `interpreter.TfLite` and
  a `.tflite` autopilot are viable. No tensorflow needed on the car.
- **Camera.** OpenCV opens `/dev/video0` and returns 640×480×3 frames. That
  makes `CAMERA_TYPE = "CVCAM"` (→ `donkeycar.parts.cv.CvCam`) the correct
  choice, and it needs no new code. Note `WEBCAM` is the wrong choice here:
  `parts/camera.py:Webcam` is built on pygame, which no extra installs.

So the camera → inference → recording path is already supported. The gaps are
all in the actuator/I2C layer and in the install extra itself.

### 1.3 The four real blockers

**(a) `Adafruit_PCA9685` needs a C compiler.** It is Adafruit's deprecated
pre-Blinka library and the sole reason a bare Uno Q image cannot
`uv pip install -e ".[pi]"`. Its replacement,
`adafruit-circuitpython-pca9685`, is pure Python and pulls no new
dependencies on this board (verified: `adafruit-blinka`,
`-busdevice`, `-register` were already present, and **no** `spidev`).

**(b) Blinka does not recognise the Uno Q.** This is the interesting one:

```
adafruit_platformdetect: chip.id = None, board.id = None
>>> import board
  ... your board may not yet be supported. Please open a New Issue ...
```

So the whole `board` / `busio` entry point is unavailable, which would break
`adafruit_pca9685` — and today breaks `parts/imu.py`, `parts/lidar.py` and
`parts/oled.py`, all of which `import board`.

Forcing a generic board **does not rescue it.** With
`BLINKA_FORCECHIP=GENERIC_X86 BLINKA_FORCEBOARD=GENERIC_LINUX_PC` you do get
`board.SCL` / `board.SDA`, but constructing the bus then dies:

```
busio.I2C(board.SCL, board.SDA)
ImportError: cannot import name 'i2cPorts' from 'microcontroller.pin'
```

This matters for branch `1177-update-i2c-driver-for-bookwork`, which already
migrates the PCA9685 driver but does it via `busio.I2C(board.SCL, board.SDA)`
— that approach will not work on the Uno Q as written. See §2.

What *does* work is going one layer down, addressing the bus by number:

```python
from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
I2C(2)            # OK, no board detection involved
```

That object is 3 methods short of the `busio.I2C` API the CircuitPython
drivers require:

| `busio.I2C` | `generic_linux.i2c.I2C` |
|---|---|
| `readfrom_into`, `writeto`, `writeto_then_readfrom`, `scan` | present |
| `try_lock`, `unlock`, `deinit` | **missing** |

Hence a ~20-line shim (§1.4) rather than a fork of Blinka. Addressing by bus
number is also a better fit for donkeycar than `board.SDA` ever was, because
the bus number is already part of the pin id: `"PCA9685.1:40.1"` is
*provider.busnum:address.channel*, and `PCA9685_I2C_BUSNUM` is already a
config value that the current `board`/`busio` code in 1177 silently ignores.

**(c) The Arduino header pins belong to the MCU, not Linux.** This is the
one that changes the architecture, and it was only settled by wiring a real
PCA9685 up. The UNO-shaped header — including the SDA/SCL pins — is owned by
the STM32U585, so a device on it is invisible to Linux `/dev/i2c-*` no matter
what the Linux-side code does. Four confirmations:

1. App Lab's `unoq-pin-toggle` example maps `D0`–`D21` and `A0`–`A5` to
   *sketch* pins; Linux Python reaches them only through
   `Bridge.call("set_pin_by_name", ...)` into a sketch built on
   `Arduino_RouterBridge.h`.
2. The board's Zephyr overlay declares `i2cs = <&i2c2>, <&i2c4>, <&i2c3>`
   under its `arduino` node, and `libraries/Wire/Wire.cpp` maps that array to
   `Wire`, `Wire1`, `Wire2` in order.
3. The Linux-side Python API (`arduino.app_peripherals`) offers speaker,
   microphone, camera and remote_sensor — **no I2C at all**.
4. Empirically: with the PCA9685 wired to the header and powered, a Linux
   rescan was byte-for-byte unchanged, while a scan from an MCU sketch found
   it immediately (see §6).

So no amount of Linux-side I2C code can reach a header device on this board,
which is why this branch carries none: the route has to go through the MCU.
That is §6, and §2 explains where the Linux-side I2C work went.

**(d) No GPIO story.** `RPi.GPIO` and `pigpio` are both Pi-only, so
`PinProvider.RPI_GPIO` and `PinProvider.PIGPIO` are dead on this board. Only
`PinProvider.PCA9685` is reachable. That is enough for
`PWM_STEERING_THROTTLE` (a standard RC car: servo + ESC on a PCA9685), which
is the target configuration. Native GPIO is deferred to Phase 4.

### 1.4 The `unoq` extra

```toml
unoq = [
    "msgpack",                  # to talk MsgPack-RPC to arduino-router
    "ai-edge-litert>=2.1.4",
    "opencv-contrib-python",
    "matplotlib",
    "pandas",
    "plotly",
    "albumentations",
]
```

Differences from `pi`, and why:

- **No PCA9685 driver and no `adafruit-circuitpython-*` at all.** The header
  belongs to the MCU (§1.3c), so no I2C device on it is reachable from Linux,
  and `import board` raises here anyway (§1.3b). Installing those drivers
  would mean shipping packages that cannot work.
- **`msgpack` added.** It is the only thing needed to reach the MCU; see §6.1.
- **`gpiozero` dropped.** Nothing under `donkeycar/` imports it, and its pin
  factories are Pi-only.
- **`kivy` and `kivy-garden.matplotlib` dropped.** They are only for
  `donkey ui`, which belongs on the training machine, and cost ~250 MB on a
  board with 2.4 GB free. Both install and import fine if wanted.
- **`pandas-stubs` dropped** — a typing-only dependency, `dev`'s business.

## 2. The PCA9685 work lives on another branch

An earlier version of this plan had a Phase 1 that replaced the deprecated
`Adafruit_PCA9685` with the CircuitPython driver across `pins.py` and
`actuator.py`, plus an `ExplicitBusI2C` that opened a bus by number so the
driver would work on boards Blinka cannot detect.

**None of that is needed here, and it has been moved out.** The Uno Q's
header belongs to its MCU (§1.3c), so there is no Linux-side I2C to reach a
PCA9685 on, and the MCU emits the servo pulses itself (§6.3). This branch
therefore leaves `pins.py` and `actuator.py` exactly as `main` has them.

That work was worth keeping, though — it is a Raspberry Pi and Jetson Nano
improvement that stands on its own, and it is what
`1177-update-i2c-driver-for-bookwork` set out to do. It now lives on
**`pca9685-circuitpython-driver`**, branched from `main`, where it:

- retires the deprecated library in `pins.py`, `actuator.py` and the `pi` and
  `nano` extras
- removes the last C-toolchain requirement from `[pi]`, since
  `Adafruit_PCA9685` was what pulled `Adafruit-GPIO` → `spidev`
- fixes two real bugs: `pca9685()` never wrote into its `_pca9685` cache, so
  the board re-initialised on every call and the frequency-conflict check
  could never fire; and `OutputPinPCA9685` derived from `ABC` rather than
  `OutputPin`
- adds 49 tests, where that provider previously had none that ran off a Pi

It needs its own review and a regression run on a real Pi car before merging.
Nothing on this branch depends on it.

## 3. Open hardware questions

None of these block Phases 0–1, but all block Phase 3:

- **~~Which `/dev/i2c-N` is on the Arduino headers?~~ Answered: none of
  them.** The headers are MCU-owned (§1.3c). On the Linux side, `i2c-0` is
  quiet, `i2c-1` carries eight SoC-internal peripherals
  (`0x2a 0x2c 0x38 0x39 0x3d 0x3f 0x42`, plus `0x58` bound by a kernel
  driver) and must be left alone, and `i2c-2` ACKs all 112 addresses — no
  pull-ups, nothing attached, and no known connector. The PCA9685 lives on
  the MCU's `Wire2` (`i2c3`, PC0/PC1) at `0x40`.
- **Level shifting.** The header I2C is 3.3 V (STM32 side). A PCA9685
  breakout tolerated it fine at `Wire2`, but confirm before relying on it.
- **Servo/ESC power.** The PCA9685 needs its own V+ rail; do not try to feed
  a steering servo from the board.
- **`arduino` is not in the `i2c` group.** Confirmed: `open('/dev/i2c-1')`
  fails with `EACCES`. The group exists (gid 106) and is empty. Phase 0.2.

---

## 4. The checklist

### Phase 0 — install path

- [x] **0.1** Add the `unoq` extra to `pyproject.toml` per §1.4.
- [x] **0.2** Add `ARDUINO_UNO_Q_SETUP.md`: the `build-essential
      python3-dev` finding and why it is no longer needed after 0.1,
      `usermod -aG i2c arduino`, the `i2c-tools` hint, and the §3
      power/level-shift warnings. (Not `docs/`: that directory was removed
      from the repo in #875, and root-level `*_MIGRATION.md` is the
      surviving convention.)
- [x] **0.3** Verify on the board that `uv pip install -e ".[unoq]"` succeeds
      in a *fresh* venv with no usable C compiler, proving 0.1 removed the
      toolchain requirement. Record the result in `ARDUINO_UNO_Q_SETUP.md`.
      (Done by forcing `CC=/bin/false CXX=/bin/false` rather than removing
      `build-essential`, which keeps the board's toolchain intact: 69
      packages resolved, only `donkeycar` built, install clean.)

### Phase 2 — car configuration

- [x] **2.1** `donkey createcar` config defaults for the Uno Q:
      `CAMERA_TYPE = "CVCAM"`, `DRIVE_TRAIN_TYPE = "PWM_STEERING_THROTTLE"`,
      `PCA9685_I2C_BUSNUM` set to whatever §3 resolves to. (Delivered as a
      documented `myconfig.py` block, not a `cfg_unoq.py` template pair:
      nothing about the board needs different *code*, and a template would
      fork ~470 lines of `cfg_complete.py` to change five values. Note
      `arduino_drive` is a different thing — a host driving a separate
      Arduino over Firmata.)
- [x] **2.2** Create a car on the board and confirm `manage.py drive` starts,
      serves the web controller, and streams camera frames — with the
      actuator pins still unwired. (Done with `DRIVE_TRAIN_TYPE = "MOCK"`:
      up in 4s, 20 Hz loop, ~17 distinct MJPEG fps, 68% of one core, no
      errors. Test car left at `~/mycar-unoq` on the board.)
- [x] **2.3** Note in `ARDUINO_UNO_Q_SETUP.md` that `donkey ui` is not
      installed by the `unoq` extra, and how to add kivy if wanted.

### Phase 3 — on-car validation (needs the wired car)

- [ ] **3.1** `donkey calibrate` against the car's real steering linkage and
      ESC, and record the resulting pulse limits. The wide 600-2400 us range
      used to prove the hardware will drive the wheels past their lock.
- [ ] **3.2** Drive and record a tub on the track; check frame rate and the
      thermal/CPU headroom while recording.
- [ ] **3.3** Train off-board, copy a `.tflite` back, and confirm an
      autopilot lap via `interpreter.TfLite`.

### Phase 4 — beyond the minimum (optional, later)

- [ ] **4.1** Reach I2C sensors through the MCU, the way the servo is: a
      sketch exposing `i2c_write` / `i2c_write_read` over the bridge, and a
      `busio.I2C`-compatible object on the Linux side, so `imu.py`,
      `lidar.py` and `oled.py` can work on this board.
- [ ] **4.2** Add a libgpiod-backed `PinProvider` for `/dev/gpiochip*`, so
      native GPIO input/output works on the Uno Q (§1.3c).

---

## 5. Found on the way, out of scope here

**The `nano` extra cannot be resolved at all, and this predates any of the
work above.** On current `main`, `donkeycar[nano]` pins `numpy==1.23.*` while
the base `dependencies` require `numpy>=1.26.0`:

```
× No solution found when resolving dependencies:
╰─▶ Because donkeycar[nano]==5.4.dev1 depends on numpy==1.23.* and
    donkeycar==5.4.dev1 depends on numpy>=1.26.0, we can conclude that
    donkeycar==5.4.dev1 and donkeycar[nano]==5.4.dev1 are incompatible.
```

`matplotlib==3.7.*` and `pandas==2.0.*` in that extra are likely to be stuck
the same way. It looks like the Python 3.12/3.13 migration (ba25266b) raised
the floor on the base dependencies without revisiting `nano`, whose pins exist
because the Jetson Nano's JetPack is tied to an older Python.

Deliberately not fixed here: it needs a Jetson Nano to validate against, and
whether `nano` should be re-pinned or retired is a separate call. Task 1.5
swapped its PCA9685 driver along with the Pi's for consistency, which changes
nothing about this conflict either way.

**`POST /drive` cannot start recording, and this is nothing to do with the
Uno Q.** `DriveAPI.post` in `parts/web_controller/web.py` sets
`application.recording`, but `LocalWebController.run_threaded` takes
`recording` as an *input* wired from `ToggleRecording`'s *output*:

```python
if recording is not None and self.recording != recording:
    self.recording = recording     # clobbers what the POST just set
```

So the POSTed value is overwritten on the next loop tick before
`ToggleRecording` ever sees it. The websocket path (`WebSocketDriveAPI`) also
sets `recording_latch`, which is applied after that block and therefore
survives — which is why the browser UI records correctly and only the plain
HTTP API is affected. `drive_mode` looks to have the same asymmetry:
`DriveAPI` sets `mode` without `mode_latch`.

Not fixed here because it is outside this work and the browser is unaffected;
worth its own change. Found while trying to measure the loop rate through the
HTTP API, which is why the measurement now uses the websocket.

**The `[pi]` toolchain requirement.** `Adafruit_PCA9685` is what pulls
`Adafruit-GPIO` -> `spidev`, which ships no wheel, so a Raspberry Pi install
needs `build-essential` too. Retiring it fixes that, but that change lives on
`pca9685-circuitpython-driver` (§2), not here.

---

## 6. The MCU bridge route

Settled by flashing `arduino/unoq_i2c_scan/` (a throwaway diagnostic that
scans all three `Wire` buses and echoes a `ping`) and calling it from Linux:

```
i2c_scan -> Wire:none|Wire1:none|Wire2:0x40,0x70
```

`0x40` is the PCA9685 and `0x70` its all-call address — so the chip sits on
`Wire2`, which is `i2c3` on PC0/PC1. The wiring is good; only the software
route was missing.

### 6.1 The transport is usable from donkeycar

`Bridge` comes from `arduino_app_bricks`, which App Lab ships inside a Docker
image (`ghcr.io/arduino/app-bricks/python-apps-base`) and which is **not** on
PyPI. It is, however, an ordinary pip package — source at
`github.com/arduino/app-bricks-py`, requiring only msgpack, Pillow, pyyaml and
requests. Importing `arduino.app_utils.bridge` in a plain venv on the host,
outside any container, works: it reaches `arduino-router` on `127.0.0.1:7500`
and RPCs into the sketch. For donkeycar only **msgpack** and **watchdog** are
new; numpy, Pillow, pyyaml and requests are already dependencies.

### 6.2 Latency

Measured against the flashed sketch's `ping`, 60 calls:

| leg | median | p95 |
|---|---|---|
| host → router (error path, no MCU) | 0.24 ms | 0.31 ms |
| host → router → MCU → back | **5.79 ms** | 6.40 ms |

Two round trips per frame is 11.6 ms of the 50 ms available at 20 Hz. That is
workable but not free, so the design below wants one I2C transaction per pin
per frame and no chatter.

### 6.3 Design: the MCU emits the servo PWM; no PCA9685 on this board

**This supersedes an earlier version of this section, which was wrong.** It
had Linux driving a PCA9685 over raw I2C through the bridge, on the grounds
that the MCU could not produce servo pulses. That grounding was mistaken.

What is true is narrower: **`analogWrite()` cannot do servo PWM.** It calls
`pwm_set_pulse_dt()`, which takes the period from the devicetree, and the
overlay fixes every PWM pin at `PWM_HZ(500)`. But `pwm_set_dt()` sets period
*and* pulse, and a sketch can call it directly, so the real limit is only
what each timer can reach given its devicetree prescaler and counter width.

Measured on the board with `arduino/unoq_pwm_probe/`, which asks the driver
to program a real 20 ms / 1.5 ms signal and reports Zephyr's return code:

| Pin | Timer | cycles/sec | step | counts per 20 ms | 20 ms accepted | rejects 1 s | verdict |
|---|---|---|---|---|---|---|---|
| **D2** | TIM2_CH2 | 32 MHz | 31 ns | 640,000 | yes | no | **good** — TIM2 is 32-bit, so it genuinely reaches these periods |
| D3 | TIM3_CH3 | 32 MHz | 31 ns | 640,000 | yes | **no** | **avoid** |
| **D5** | TIM1_CH4 | 2.5 MHz | 400 ns | 50,000 | yes | yes | **good** |
| D7 | TIM8_CH4N | 2.5 MHz | 400 ns | 50,000 | yes | yes | usable, but complementary output |
| D9 | TIM4_CH3 | 32 MHz | 31 ns | 640,000 | yes | **no** | **avoid** |
| D13 | TIM1_CH1N | 2.5 MHz | 400 ns | 50,000 | yes | yes | usable, but complementary output |

The "rejects 1 s" column is what makes this trustworthy. TIM1 and TIM8 refuse
an impossible 1-second period with `-134` (`-ENOTSUP`), so the driver is
validating and their `0` at 20 ms means something. TIM3 and TIM4 accept a
**10-second** period, which a 16-bit counter cannot hold at 32 MHz, so they
are not validating and their `0` proves nothing — the waveform on those pins
is unverified and probably wrong.

That matters because D9 and D10 are the pins an Arduino habit would reach for
first, and they are exactly the ones to avoid.

**Use D2 (TIM2_CH2) for one channel and D5 (TIM1_CH4) for the other.** Both
are validated, both are plain non-complementary outputs, and 400 ns is still
2,500 steps across a 1000 µs servo range — far finer than a servo resolves.

**Confirmed on hardware.** A Miuzei MG90S was driven from D5 and tracked
commanded pulse widths correctly through its full travel, so the pad really
does carry a correct 50 Hz waveform — `rc == 0` was not merely the driver
accepting a period it could not deliver. **D2 was then checked the same way
and behaves identically**, so both intended channels are measured rather
than inferred.

One calibration trap worth recording. The first test used 1000–2000 µs, the
conservative RC-standard range, and produced only about half the servo's
travel — which reads exactly like a broken PWM configuration. It is not: an
MG90S wants roughly **500–2500 µs** for a full 180°, and at 600–2400 µs the
sweep was correct and smooth. Do not diagnose the PWM path from a servo that
moves but under-travels.

So the Uno Q needs **no PCA9685 at all**, and no I2C for the drive train.
This is the donkeyhat architecture: MCU reads the RC receiver and drives the
servo and ESC; the host does vision and inference. Reaching *other* header
I2C devices (IMU, OLED) would use the same MCU route, which is Phase 4.1.

### 6.3.1 Protocol: donkeycar's host side already exists

The RC hat's `code.py` writes `b"%i, %i\r\n"` at 40 Hz and reads a
fixed-width 4+4 character command, which is exactly what
`donkeycar/parts/robohat.py` speaks — `RoboHATController` for RC input and
`RoboHATDriver` for output, under `DRIVE_TRAIN_TYPE = "MM1"`, with the
scaling, trim and bounds logic already written and field-tested.

So the sketch should carry MM1 semantics: two pulse widths in microseconds
each way. Over the bridge rather than a UART, because `/dev/ttyHS1` (the
SoC-to-MCU UART, already at 115200) is held exclusively by `arduino-router`,
which also drives MCU reset via `gpiochip1`. Taking the UART would mean
disabling the router and losing App Lab; the bridge costs 5.79 ms per round
trip, and RC input can be *pushed* with `Bridge.notify` so only the output
direction pays it.

### 6.4 Tasks

- [x] **5.1** Commit the diagnostic sketch and record §6's findings.
- [x] **5.2** Establish whether the MCU can emit servo PWM directly, which
      pins are trustworthy, and at what resolution (§6.3). Supersedes the
      PCA9685-over-bridge design.
- [x] **5.3** Write the donkeyhat-equivalent sketch: three RC channels in via
      `attachInterrupt`/`micros`, two servo outputs via `pwm_set_dt` on D2 and
      D5, RC values pushed with `Bridge.notify` at ~40 Hz, and a provided
      `set_pulse(steering, throttle)`. (Both D2 and D5 confirmed against a
      real servo. Output, clamping and failsafe verified; the three RC input
      channels are written but **unproven** — no receiver to hand.)
- [x] **5.4** Add a `UnoQRcHat` donkeycar part reusing `robohat.py`'s scaling
      and trim logic over the bridge instead of a serial port, with
      hardware-free tests against a fake bridge. (47 tests; also verified
      against the real router and MCU.)
- [x] **5.5** ~~Pin down how donkeycar gets `arduino_app_bricks`~~ —
      **dissolved.** donkeycar does not need it. The router speaks standard
      MsgPack-RPC, so `parts/unoq_bridge.py` speaks it directly and the only
      new dependency is `msgpack`, which is on PyPI with aarch64 wheels.
      That avoids all three bad options: no MPL-2.0 files vendored into an
      MIT tree, no PEP 508 direct URL (which PyPI rejects in published
      metadata), and nothing to ask Arduino for.
- [x] **5.6** Drop the PCA9685 packages from the `unoq` extra — the board does
      not need them — keeping them in `pi` and `nano`. (Also dropped the four
      `adafruit-circuitpython-*` sensor drivers: all of them need
      `import board`, which raises on this board, so the extra was installing
      things that cannot work. They return if Phase 4.1 routes I2C through
      the MCU.)
- [x] **5.7** Measure the real drive loop with the bridge drive train and
      confirm 20 Hz holds. (**19.93 Hz** over 400 loops; recording at
      **19.8 Hz**, 200 frames in 10.1 s.)
- [ ] **5.8** Wire encoders, as the RC hat does, and feed donkeycar's
      odometry parts.

### 6.5 Verified against real hardware

Our own client, the sketch and the donkeycar parts, end to end on the board:

| | |
|---|---|
| `get_rc` / `set_pulse` / `get_last_pulse` | all answer correctly |
| **Pushed `rc_input` notifications** | 77–78 frames in 2 s = **38–39 Hz**, inter-frame median 26.4 ms against the sketch's 25 ms cadence |
| `UnoQRcHatDriver.run(-1, 0)` → `750 µs`, `run(1, 0)` → `2250 µs` | servo tracked it |
| Sustained 20 Hz through the part | median **7.4 ms**, p95 9.1 ms of a 50 ms budget |
| `shutdown()` | returns the car to `1500, 1500` |

One router quirk found this way: **the arduino-router build on this board does
not implement `$/unregister`**. `unprovide()` drops the local handler first,
so dispatch stops regardless, and the failed call is now logged at debug
rather than warned about. There is a regression test for it.

### 6.6 A driveable car

`DRIVE_TRAIN_TYPE = "UNOQ"` in `complete.py` builds a car from these parts,
and `CONTROLLER_TYPE = "UNOQ"` adds RC input for anyone with a receiver.
Both are wired next to the MM1's, and `UNOQ` joins `MM1` and `pigpio_rc` in
the checks that skip joystick-only button wiring.

Measured on the board, driving from the web controller with a servo attached:

| | |
|---|---|
| Drive loop | **19.93 Hz** — 400 steps in 20.07 s against a 20 Hz target |
| Recording while steering | **19.8 Hz** — 200 frames and 200 images in 10.1 s |
| Web angle → pulse | −1.0 → 750 µs, −0.5 → 1125, 0 → 1500, 0.5 → 1875, 1.0 → 2250 |
| CPU | 46% of one core, load average 0.17 |
| Errors in the log | none |

The failsafe was also confirmed the hard way: after `kill -9` of the drive
process, so `shutdown()` never ran, the MCU was left at `1500, 1500, 1` —
throttle neutralised and the tripped flag set.
