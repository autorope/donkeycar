# Running donkeycar on the Arduino Uno Q

The Uno Q pairs a Qualcomm QRB2210 (aarch64, running Debian 13 trixie) with an
STM32U585 MCU. donkeycar runs on the Linux side. Everything below was verified
on a real board; see `ARDUINO_UNO_Q_PLAN.md` for the work still outstanding.

## What works, and what does not

| | |
|---|---|
| Camera | **Yes** — OpenCV reads `/dev/video0`. Use `CAMERA_TYPE = "CVCAM"`. |
| Autopilot inference | **Yes** — `ai-edge-litert` imports, so `.tflite` models run. |
| Servo/ESC output | **Not yet wired up in donkeycar**, but the MCU can do it directly — no PCA9685 needed. See "Servo PWM from the MCU". |
| `RPI_GPIO` / `PIGPIO` pin providers | **No** — both are Raspberry Pi only. |
| `parts/imu.py`, `parts/lidar.py`, `parts/oled.py` | **No** — see "Blinka" below. |
| `donkey ui` | Not installed by the `unoq` extra; see "Optional: kivy". |

A full `manage.py drive` loop has been run on the board with
`DRIVE_TRAIN_TYPE = "MOCK"` (no actuators wired): it started in 4 seconds,
served the web controller, and streamed live MJPEG at ~17 distinct frames per
second from a 20 Hz vehicle loop, using 68% of one core and 89 MB, at a load
average of 0.27. No errors or tracebacks. There is ample headroom on the
board's four cores.

Set `CAMERA_TYPE = "CVCAM"`, **not** `"WEBCAM"`. Despite the name, the
`WEBCAM` path uses `parts/camera.py:Webcam`, which is built on pygame — a
dependency no extra installs. `CVCAM` uses `parts/cv.py:CvCam` over OpenCV,
which is already in the `unoq` extra.

## Install

The board ships `uv` at `~/.local/bin/uv`, which is only on `PATH` after
sourcing its env file. A non-interactive `ssh` command gets neither that nor
the virtualenv, so source both first:

```bash
. ~/.local/bin/env
. ~/env/bin/activate          # the board's stock venv; adjust if you made your own

git clone https://github.com/autorope/donkeycar.git ~/projects/donkeycar
cd ~/projects/donkeycar
uv pip install -e ".[unoq]"
```

No compiler is required, and that is verified rather than assumed: on a real
board, `uv pip install -e ".[unoq]"` into a fresh venv with
`CC=/bin/false CXX=/bin/false` resolves 69 packages, builds only `donkeycar`
itself (pure Python), and succeeds. The same install of `[pi,dev]` resolves 96
packages and has to compile `spidev`.

If you install `[pi]` instead, it will fail with:

```
× Failed to build `spidev==3.8`
    error: [Errno 2] No such file or directory: 'aarch64-linux-gnu-gcc'
hint: `spidev` was included because `donkeycar[pi]` depends on
      `adafruit-pca9685` -> `adafruit-gpio` -> `spidev`
```

`spidev` publishes no wheels, and the stock image has neither a C toolchain
nor the Python headers. You can work around that with
`sudo apt-get install build-essential python3-dev`, but prefer `[unoq]`,
which drops the deprecated library that pulls `spidev` in at all.

Mind the disk: the stock image leaves about 2.4 GB free on `/`, and the
`unoq` extra uses a good part of it. Do not add torch or tensorflow to the
car — train off-board and copy a `.tflite` across.

## The header pins belong to the MCU

**A PCA9685 on the UNO header SDA/SCL is invisible to Linux.** The
UNO-shaped header is wired to the STM32U585, not the Qualcomm SoC: App Lab's
`unoq-pin-toggle` example drives `D0`–`D21` and `A0`–`A5` from a *sketch*,
the Zephyr overlay declares the header I2C as `i2c3` on the STM32, and the
Linux-side Python API exposes no I2C at all. Confirmed by measurement — with
a powered PCA9685 on the header, a Linux bus scan is unchanged, while a scan
from an MCU sketch finds it at once:

```
i2c_scan -> Wire:none|Wire1:none|Wire2:0x40,0x70
```

(`0x40` is the chip, `0x70` its all-call address. `Wire2` is `i2c3`.)

Reaching it therefore means going through the MCU: a sketch that exposes I2C
over the router bridge, and a Linux-side bus object that calls it. That work
is Phase 5 of `ARDUINO_UNO_Q_PLAN.md` and is not finished yet. A round trip
through the bridge to the MCU measures ~5.8 ms median, so two per frame fits
inside a 20 Hz loop.

## Servo PWM from the MCU

The Uno Q does **not** need a PCA9685. The MCU drives the steering servo and
ESC directly, as the DIY Robocars RC hat does.

`analogWrite()` will not do it — it calls `pwm_set_pulse_dt()`, which takes
the period from the devicetree, and the overlay pins every PWM channel at
500 Hz. Call Zephyr's `pwm_set_dt()` from the sketch instead, which sets
period and pulse together.

**Use D2 and D5.** Measured on the board (`arduino/unoq_pwm_probe/`):

| Pin | Timer | step | verdict |
|---|---|---|---|
| **D2** | TIM2_CH2 | 31 ns | good — 32-bit counter |
| **D5** | TIM1_CH4 | 400 ns | good |
| D7, D13 | TIM8/TIM1 | 400 ns | usable, but complementary outputs |
| D3, D9 | TIM3/TIM4 | — | **avoid** |

Avoid D3 and D9 even though they *appear* to work. A 20 ms frame needs 640,000
counts at their 32 MHz clock, which a 16-bit counter cannot hold, and the
driver does not validate: those pins accept a 10-second period and return
success. TIM1 and TIM8 correctly reject an impossible period with `-ENOTSUP`,
so their success means something. D9 and D10 are the pins Arduino habit
reaches for first, and they are the wrong ones here.

400 ns still gives 2,500 steps across a 1000 µs servo range, far finer than a
servo resolves.

## Diagnostic sketches

`arduino/unoq_i2c_scan/` scans the MCU's three `Wire` buses and reports over
the bridge; `arduino/unoq_pwm_probe/` reports which pins can carry servo PWM
and at what resolution. Build and flash either with:

```bash
cd arduino/unoq_pwm_probe      # or arduino/unoq_i2c_scan
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload  --fqbn arduino:zephyr:unoq .   # overwrites the MCU sketch
```

## I2C setup for the PCA9685 (Linux-side buses)

The rest of this section applies to a PCA9685 on a **Linux** I2C bus. On the
Uno Q as shipped there is no known connector that reaches one, so this is
here for completeness and because the same code path is what the Raspberry
Pi uses.

**Add yourself to the `i2c` group.** The stock image puts `arduino` in
`gpiod`, `video` and `dialout`, but *not* `i2c`, so `/dev/i2c-*`
(`root:i2c 0660`) is unreadable and you get `PermissionError: [Errno 13]`:

```bash
sudo usermod -aG i2c arduino
```

Log out and back in — group changes do not apply to existing sessions, ssh
master connections included.

**Find the bus.** The board exposes `/dev/i2c-0`, `-1` and `-2`, and which one
reaches the Arduino headers is board-revision specific. Install the tools and
scan, with the PCA9685 attached:

```bash
sudo apt-get install i2c-tools
for n in 0 1 2; do echo "== i2c-$n"; i2cdetect -y $n; done
```

A PCA9685 shows at `0x40` by default. Use `i2cdetect`, not a hand-rolled
scan that probes by reading a byte — that reports a device at every address
on some buses.

Put the bus number in the pin ids and in `myconfig.py`. Pin ids are
`provider.busnum:address.channel`, so on bus 1 at `0x40`:

```python
PCA9685_I2C_BUSNUM = 1
PCA9685_I2C_ADDR = 0x40
DRIVE_TRAIN_TYPE = "PWM_STEERING_THROTTLE"
PWM_STEERING_THROTTLE = {
    "PWM_STEERING_PIN": "PCA9685.1:40.1",
    "PWM_THROTTLE_PIN": "PCA9685.1:40.0",
    ...
}
```

### Wiring cautions

- **Check the logic level.** The SoC's I2C lines are 3.3 V. Confirm whether
  the header bus you picked is level-shifted before connecting a 5 V PCA9685
  breakout.
- **Power the servo rail separately.** The PCA9685 needs its own V+ for the
  steering servo and ESC. Do not try to draw that through the Uno Q.

## Car configuration

Create the car with the stock `complete` template. There is no separate Uno Q
template, because nothing about the board needs different *code* — only
different config values:

```bash
donkey createcar --path ~/mycar
```

Then put the following in `~/mycar/myconfig.py`. Pin ids are
`provider.busnum:address.channel`, so the `1` in `PCA9685.1:40.0` is the bus
number: change every occurrence to whichever bus you found above, and keep
`PCA9685_I2C_BUSNUM` in step with it.

```python
# --- camera: USB webcam through OpenCV ---
CAMERA_TYPE = "CVCAM"          # not "WEBCAM", which is the pygame path
CAMERA_INDEX = 0               # /dev/video0
IMAGE_W = 160
IMAGE_H = 120
IMAGE_DEPTH = 3

# --- drive train: steering servo + ESC on a PCA9685 ---
DRIVE_TRAIN_TYPE = "PWM_STEERING_THROTTLE"
PCA9685_I2C_BUSNUM = 1         # set to the bus you found; see "Find the bus"
PCA9685_I2C_ADDR = 0x40
PWM_STEERING_THROTTLE = {
    "PWM_STEERING_PIN": "PCA9685.1:40.1",
    "PWM_STEERING_SCALE": 1.0,
    "PWM_STEERING_INVERTED": False,
    "PWM_THROTTLE_PIN": "PCA9685.1:40.0",
    "PWM_THROTTLE_SCALE": 1.0,
    "PWM_THROTTLE_INVERTED": False,
    # replace these five with what `donkey calibrate` gives you
    "STEERING_LEFT_PWM": 460,
    "STEERING_RIGHT_PWM": 290,
    "THROTTLE_FORWARD_PWM": 500,
    "THROTTLE_STOPPED_PWM": 370,
    "THROTTLE_REVERSE_PWM": 220,
}

# --- autopilot: train off-board, run a .tflite here ---
DEFAULT_MODEL_TYPE = "tflite_linear"
```

The steering and throttle PWM values above are the template's defaults, **not
calibration values for your car**. Run `donkey calibrate` and replace them, or
the car will drive its servo into its end stops.

Train on a real machine and copy the `.tflite` across. Do not install
tensorflow or torch on the board.

## Blinka does not detect this board

`adafruit-platformdetect` does not recognise the Uno Q — it reports both chip
and board as `None` — so `import board` raises:

```
>>> import board
  ... your board may not yet be supported. Please open a New Issue ...
```

donkeycar's PCA9685 support works anyway, because it addresses the bus by
number through `donkeycar/parts/i2c_bus.py` rather than going through
`board`/`busio`. But any part that still does `import board` will fail on
this board: `parts/imu.py`, `parts/lidar.py` and `parts/oled.py`. Converting
them is Phase 4 of the plan.

Forcing a generic board does not help, so do not spend time on it. With
`BLINKA_FORCECHIP=GENERIC_X86 BLINKA_FORCEBOARD=GENERIC_LINUX_PC` you do get
`board.SCL` and `board.SDA`, but constructing the bus then fails:

```
ImportError: cannot import name 'i2cPorts' from 'microcontroller.pin'
```

## Deprecated parts that need the old library

`JHat` and `JHatReader` in `parts/actuator.py` still import
`Adafruit_PCA9685`, which no extra installs any more. Both are deprecated and
undocumented, and they are for a Teensy emulating a PCA9685 rather than a real
one. If you genuinely need them, `uv pip install Adafruit_PCA9685` — which
will want `build-essential` and `python3-dev` for `spidev`.

## Optional: kivy

`donkey ui` is **not** installed by the `unoq` extra: it needs kivy, which is
left out to save ~250 MB on a board with little disk to spare, and the UI
belongs on the machine you train on.
The board does have an XFCE desktop, and kivy installs and imports fine there
if you want the UI locally:

```bash
uv pip install kivy "kivy-garden.matplotlib"
```
