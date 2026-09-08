# Plan: run donkeycar on the Arduino Uno Q

**IN PROGRESS — 11 / 19 tasks.**

Phase 0 ▓▓▓ · Phase 1 ▓▓▓▓▓ · Phase 2 ▓▓▓ · Phase 3 ░░░░ · Phase 4 ░░░░

> Convention: tick a box in §4 in the same commit that does the work, so the
> checklist and the git history never disagree. Update the counter above too.

---

## 1. Where things stand

### 1.1 The board

Verified over ssh on `arduino@10.0.0.75` (`Edunoq.local`) on 2026-09-07:

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

### 1.3 The three real blockers

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

**(c) No GPIO story.** `RPi.GPIO` and `pigpio` are both Pi-only, so
`PinProvider.RPI_GPIO` and `PinProvider.PIGPIO` are dead on this board. Only
`PinProvider.PCA9685` is reachable. That is enough for
`PWM_STEERING_THROTTLE` (a standard RC car: servo + ESC on a PCA9685), which
is the target configuration. Native GPIO is deferred to Phase 4.

### 1.4 The I2C shim

New file, `donkeycar/parts/i2c_bus.py`, no Blinka board detection anywhere:

```python
class ExplicitBusI2C:
    """A busio.I2C-compatible bus addressed by /dev/i2c-N bus number.

    Blinka's board detection does not support every SBC (the Arduino Uno Q
    among them), so `import board` can fail on an otherwise fine Linux I2C
    bus. This wraps the generic-Linux backend directly and adds the locking
    and deinit methods the CircuitPython drivers expect.
    """
    def __init__(self, busnum: int) -> None: ...
    def try_lock(self) -> bool: ...      # threading.Lock, non-blocking
    def unlock(self) -> None: ...
    def deinit(self) -> None: ...
    # readfrom_into / writeto / writeto_then_readfrom / scan delegate
```

Because it is duck-typed against `busio.I2C`, the same object also unblocks
`imu.py`, `lidar.py` and `oled.py` on boards Blinka does not detect — but
converting those parts is out of scope here and left to Phase 4.

### 1.5 The `unoq` extra

```toml
unoq = [
    "adafruit-circuitpython-pca9685",   # replaces legacy Adafruit_PCA9685
    "adafruit-circuitpython-ssd1306",
    "adafruit-circuitpython-rplidar",
    "adafruit-circuitpython-mpu6050",
    "adafruit-circuitpython-bno055",
    "ai-edge-litert>=2.1.4",
    "opencv-contrib-python",
    "matplotlib",
    "pandas",
    "plotly",
    "albumentations",
]
```

Differences from `pi`, and why:

- `Adafruit_PCA9685` → `adafruit-circuitpython-pca9685`. This is the change
  that removes the compiler requirement (§1.3a).
- **`gpiozero` dropped.** Nothing under `donkeycar/` imports it, and its pin
  factories are Pi-only.
- **`kivy` and `kivy-garden.matplotlib` dropped.** They are only for
  `donkey ui`, which belongs on the training machine. Worth ~250 MB on a
  board with 2.4 GB free. Both do install and import fine on this board, so
  anyone who wants the UI on the Uno Q's XFCE desktop can add them by hand.
- **`pandas-stubs` dropped** — a typing-only dependency, `dev`'s business.
- The four `adafruit-circuitpython-*` sensor drivers are kept because they
  are small and pure Python, but note that `imu.py` / `lidar.py` / `oled.py`
  still `import board` and so remain non-functional until Phase 4.

---

## 2. Decision: one shared implementation

**Agreed (option 1).** `PinProvider.PCA9685` keeps its name and gets the
CircuitPython driver over `ExplicitBusI2C`, so one implementation serves the
Pi and the Uno Q, honours `PCA9685_I2C_BUSNUM` on both, and retires the
deprecated library. This touches the Pi path, so Phase 3 must include a
regression run on the real car before this is considered done.

`1177-update-i2c-driver-for-bookwork` is **subsumed, not merged** — it has no
PR, so its useful work is lifted onto current `main` and the branch is left
alone. What is worth taking:

- the split of the old monolithic `PCA9685` into a `PCA9685board` (one board)
  plus a `PCA9685Pin` (one channel, wrapping `adafruit_pca9685.PWMChannel`),
  which is what lets pin objects stop passing a channel into every call
- the move from 12-bit (`4096`) to 16-bit (`0x10000`) duty-cycle resolution,
  which is what the CircuitPython driver expects
- a genuine bug fix: `main`'s `pca9685()` factory never writes into its
  `_pca9685` cache, so the "singleton" is allocated fresh every call
- `OutputPinPCA9685` inheriting `OutputPin` rather than `ABC`

Three things must **not** be carried over as-is:

1. `busio.I2C(board.SCL, board.SDA)` — does not work on the Uno Q (§1.3b),
   and it is why 1177's docstring says "the busnum argument is now ignored".
   Replaced by `ExplicitBusI2C(busnum)`, which restores `busnum`.
2. `super().__init__(self, pca_pin, frequency / 60, False)` in
   `actuator.PCA9685` passes four arguments to a three-parameter
   `PulseController.__init__`, so `pwm_pin` binds to `self` and `pwm_scale`
   to the pin. Must be `super().__init__(pwm_pin, frequency / 60, False)`.
3. That same call hands `PulseController` a `PCA9685Pin`, but
   `PulseController` requires a `PwmPin` — it calls `.state()`, `.start()`
   and `.duty_cycle()`, none of which `PCA9685Pin` has. It must be given a
   `PwmPinPCA9685`.

### 2.1 The two deprecated Teensy classes

`JHat` and `JHatReader` in `actuator.py` also import the legacy library, but
they are **not** being ported. Both are `@deprecated` and documented as
"unsupported/undocumented in the framework", and `JHatReader` drives the chip
through `self.pwm._device.writeRaw8(0x06)` — reaching into `Adafruit_GPIO`
internals that have no equivalent in the CircuitPython driver. Porting them
blind, with no Teensy to test against, would be guesswork.

Instead they keep their lazy `import Adafruit_PCA9685`, which now simply is
not installed by any extra. They already import inside `__init__`, so nothing
breaks until someone instantiates one, and Task 1.3 gives that path a clear
message saying the dependency was dropped and how to install it by hand.

## 3. Open hardware questions

None of these block Phases 0–1, but all block Phase 3:

- **Which `/dev/i2c-N` is on the Arduino headers?** Narrowed by task 1.1's
  `scan()`: `i2c-0` is quiet, `i2c-1` carries seven SoC-internal peripherals
  (`0x2a 0x2c 0x38 0x39 0x3d 0x3f 0x42`) and must be left alone, and `i2c-2`
  ACKs all 112 addresses, which is the signature of a bus with no pull-ups
  and nothing attached — so `i2c-2` is the likely header bus. Confirm by
  attaching the PCA9685 and rescanning: it should then show `0x40` alone.
- **Level shifting.** The Uno Q's SoC I2C is 3.3 V. Confirm whether the
  chosen bus is level-shifted on the header before hanging a 5 V PCA9685 hat
  off it.
- **Servo/ESC power.** The PCA9685 needs its own V+ rail; do not try to feed
  a steering servo from the board.
- **`arduino` is not in the `i2c` group.** Confirmed: `open('/dev/i2c-1')`
  fails with `EACCES`. The group exists (gid 106) and is empty. Phase 0.2.

---

## 4. The checklist

### Phase 0 — install path

- [x] **0.1** Add the `unoq` extra to `pyproject.toml` per §1.5.
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

### Phase 1 — I2C and the PCA9685

- [x] **1.1** Add `donkeycar/parts/i2c_bus.py` with `ExplicitBusI2C` (§1.4),
      typed, plus unit tests against an injected fake backend (19 tests),
      and verify it against the real buses on the board.
- [x] **1.2** Rebase 1177's `pins.py` PCA9685 work onto current `main`,
      replacing `busio.I2C(board.SCL, board.SDA)` with
      `ExplicitBusI2C(busnum)`.
- [x] **1.3** Convert `actuator.PCA9685` (line ~138) the same way, fixing
      both `super().__init__` defects from §2. Leave `JHat`/`JHatReader`
      (~404, ~447) on the legacy import per §2.1, but give the failure a
      message that names the dropped dependency.
- [x] **1.4** Unit tests for the PCA9685 pin provider with the I2C layer
      mocked: pin-id parsing (`"PCA9685.1:40.1"` → busnum 1, addr 0x40,
      channel 1), duty-cycle bounds, frequency. (30 tests, hardware-free.)
- [x] **1.5** Drop `Adafruit_PCA9685` from the `pi` and `nano` extras and add
      `adafruit-circuitpython-pca9685`, completing 1177's intent.

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

- [ ] **3.1** `donkey calibrate` against a real PCA9685: confirm steering and
      throttle channels respond and find the pulse limits.
- [ ] **3.2** Drive and record a tub on the track; check frame rate and the
      thermal/CPU headroom while recording.
- [ ] **3.3** Train off-board, copy a `.tflite` back, and confirm an
      autopilot lap via `interpreter.TfLite`.
- [ ] **3.4** Regression-run the shared PCA9685 path on the Pi car
      (`murmurpi64.local`) per the §2 caveat: calibrate, drive, record.

### Phase 4 — beyond the minimum (optional, later)

- [ ] **4.1** Convert `imu.py`, `lidar.py` and `oled.py` to accept an
      injected bus so they work without Blinka board detection (§1.4).
- [ ] **4.2** Add a libgpiod-backed `PinProvider` for `/dev/gpiochip*`, so
      native GPIO input/output works on the Uno Q (§1.3c).
- [ ] **4.3** Investigate driving actuators through the STM32U585 MCU over
      the Arduino bridge (`~/.arduino-bricks`) instead of a PCA9685, which
      would remove the I2C hat from the bill of materials entirely.
- [ ] **4.4** Upstream a board definition to `adafruit-platformdetect` /
      Blinka so `import board` works natively on the Uno Q and the shim
      becomes a fallback rather than the only path.

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

**A side benefit for the Pi.** Because task 1.5 removed the last dependency on
`Adafruit_PCA9685`, `donkeycar[pi]` no longer pulls `Adafruit-GPIO` and so no
longer pulls `spidev` — the `pi` extra now resolves to 79 packages with no
sdist that needs compiling. A Raspberry Pi install stops needing a C toolchain
for the same reason the Uno Q one does.
