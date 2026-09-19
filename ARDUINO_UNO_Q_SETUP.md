# Running donkeycar on the Arduino Uno Q

The Uno Q pairs a Qualcomm QRB2210 (aarch64, running Debian 13 trixie) with an
STM32U585 MCU. donkeycar runs on the Linux side. Everything below was verified
on a real board; see `ARDUINO_UNO_Q_PLAN.md` for the work still outstanding.

## What works, and what does not

| | |
|---|---|
| Camera | **Yes** — OpenCV reads `/dev/video0`. Use `CAMERA_TYPE = "CVCAM"`. |
| Autopilot inference | **Yes** — `ai-edge-litert` imports, so `.tflite` models run. |
| Servo/ESC output | **Yes** — `DRIVE_TRAIN_TYPE = "UNOQ"`, driven by the board's own MCU. No PCA9685 needed. |
| Driving from a browser | **Yes** — 19.93 Hz loop, recording at 19.8 Hz. |
| Driving from an RC transmitter | Code is in place (`CONTROLLER_TYPE = "UNOQ"`) but **untested** — no receiver was available. |
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

If you have no virtualenv yet, make one first — `--system-site-packages`
matches how the board's stock venv is built:

```bash
uv venv --python 3.13 --system-site-packages ~/env   # or: python3 -m venv --system-site-packages ~/env
source ~/env/bin/activate
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

### Wiring the servo

Signal to D2 (steering) or D5 (throttle), and ground to any header GND.

- **Power the servo externally.** A small servo idles at tens of milliamps but
  can pull over an amp when it stalls or slews under load, which will brown
  out the SoC and reboot Linux. Use a separate pack or BEC, not the board.
- **Ground must be common.** The servo's ground has to reach both its own
  supply's negative *and* a header GND, or the pulse has no reference. This is
  the usual cause of "the signal looks right but nothing moves".
- **The MCU drives 3.3 V logic.** Most hobby servos read a 3.3 V pulse fine,
  but some older analogue ones expect 5 V and will be jittery or dead.

**Verified on hardware:** a Miuzei MG90S driven from D5, and then from D2,
tracked commanded pulse widths correctly across its full travel on both.

**Mind the pulse range when testing.** 1000–2000 µs is the conservative
RC-standard range and yields only about half an MG90S's travel — which looks
convincingly like a broken PWM setup but is not. That servo wants roughly
500–2500 µs for a full 180°. Note this is only for proving the hardware: on a
real car the steering servo is deliberately driven over a *narrower* range so
the linkage never pushes the wheels past their lock, which is what
`STEERING_LEFT_PWM` / `STEERING_RIGHT_PWM` and `donkey calibrate` are for.

## Diagnostic sketches

`arduino/unoq_i2c_scan/` scans the MCU's three `Wire` buses and reports over
the bridge; `arduino/unoq_pwm_probe/` reports which pins can carry servo PWM
and at what resolution. Build and flash either with:

```bash
cd arduino/unoq_pwm_probe      # or arduino/unoq_i2c_scan
arduino-cli compile --fqbn arduino:zephyr:unoq .
arduino-cli upload  --fqbn arduino:zephyr:unoq .   # overwrites the MCU sketch
```

## Talking to the MCU from a shell

For bring-up and debugging, `unoq_bridge` has a command line.

**Activate the venv first.** There is no `python` outside it, and the system
`python3` has no donkeycar:

```bash
source ~/env/bin/activate
```

Without that you get `python: command not found`, or
`No module named 'donkeycar'`. If you would rather not activate, call the
venv's interpreter directly: `~/env/bin/python -m donkeycar.parts.unoq_bridge ...`

To have it activated for you on every login, append this to `~/.bashrc`:

```bash
if [ -f "$HOME/env/bin/activate" ]; then
    . "$HOME/env/bin/activate"
fi
```

Debian's `~/.bashrc` returns early for non-interactive shells, so this does
not affect `scp`, `rsync` or `ssh host "<command>"`.

```bash
# what the MCU last applied: "steering, throttle, failsafe_tripped"
# the third field is 1 when nothing has commanded for 500ms, which is normal
# after a one-shot call like this -- it is the failsafe doing its job
python -m donkeycar.parts.unoq_bridge get_last_pulse

# command a pulse pair (microseconds)
python -m donkeycar.parts.unoq_bridge set_pulse 1500 1500

# the RC receiver, as the MCU sees it: "steering, throttle, mode, age_ms"
python -m donkeycar.parts.unoq_bridge get_rc

# watch what the MCU pushes, and at what rate
python -m donkeycar.parts.unoq_bridge --listen rc_input --seconds 3
```

`python -m donkeycar.parts.unoq_bridge --help` lists the rest. If the router
is not running you get
`Cannot reach arduino-router at /var/run/arduino-router.sock`.

These are the same calls the drive train makes; the class behind them is
`UnoQBridge` in `donkeycar/parts/unoq_bridge.py`. It is donkeycar's own
MsgPack-RPC client, **not** part of Arduino's `arduino_app_bricks` — that
package ships only inside App Lab's Docker image and is not installed on the
board, which is why this speaks the router's protocol directly.

## Car configuration

Create the car with the stock `complete` template. There is no separate Uno Q
template, because nothing about the board needs different *code* — only
different config values:

```bash
donkey createcar --path ~/mycar
```

Then put the following in `~/mycar/myconfig.py`:

```python
# --- camera: USB webcam through OpenCV ---
CAMERA_TYPE = "CVCAM"          # not "WEBCAM", which is the pygame path
CAMERA_INDEX = 0               # /dev/video0
IMAGE_W = 160
IMAGE_H = 120
IMAGE_DEPTH = 3

# --- drive train: servo and ESC driven by the board's own MCU ---
# Flash arduino/unoq_rc_hat/ to the MCU first.  Steering goes to D2,
# throttle to D5; see "Servo PWM from the MCU" for why those pins.
DRIVE_TRAIN_TYPE = "UNOQ"
UNOQ_STEERING_MID = 1500       # pulse width for straight ahead
UNOQ_MAX_FORWARD = 2000        # full throttle
UNOQ_STOPPED_PWM = 1500        # neutral
UNOQ_MAX_REVERSE = 1000        # full reverse

# Optional: drive from an RC transmitter instead of the browser.
# Untested -- no receiver was available.  Channels on D3, D4, D6.
# CONTROLLER_TYPE = "UNOQ"

# --- autopilot: train off-board, run a .tflite here ---
DEFAULT_MODEL_TYPE = "tflite_linear"
```

The pulse widths above are conservative defaults, **not calibration values
for your car**. Run `donkey calibrate` and replace them, or the steering
linkage will be driven past the wheels' lock.

Then drive it:

```bash
cd ~/mycar
python manage.py drive
```

and open `http://<board>:8887/drive`. Measured on the board: a 19.93 Hz drive
loop and recording at 19.8 Hz, at 46% of one core.

If the drive train cannot reach the MCU you will see
`Cannot reach arduino-router at /var/run/arduino-router.sock` — check that
`arduino-router.service` is running and that the sketch is flashed.

Train on a real machine and copy the `.tflite` across. Do not install
tensorflow or torch on the board.

## Why the sketch is C++ and not Python

donkeycar is a Python project, and the two boards this drive train is modelled
on — the Robo HAT MM1 and the DIY Robocars RC hat — both run **CircuitPython**
on the microcontroller. So the obvious question is why `arduino/unoq_rc_hat/`
is a `.ino`.

**Because on the UNO Q the MCU cannot run Python, and does not need to.**

The MM1 and the RC hat put a SAMD51 or an RP2040 on a car that has no Linux.
The microcontroller is the only computer there, so everything — pulse maths,
scaling, trim, the serial protocol — has to live on it, and CircuitPython is
what makes that bearable. The UNO Q is a different machine: it *has* a Linux
side, and Arduino's own model for it is
["Python code running on Linux with C code running as a Sketch on the
microcontroller"](https://docs.arduino.cc/tutorials/uno-q/user-manual/).

So the Python did not go away, it moved to where the board puts it:

| | MM1 / DIY hat | UNO Q |
|---|---|---|
| Pulse maths, scaling, trim | CircuitPython on the MCU | **Python** — `parts/unoq.py` |
| Transport to the host | CircuitPython UART | **Python** — `parts/unoq_bridge.py` |
| Pin timing and PWM generation | CircuitPython on the MCU | C++ sketch |

What stays in C++ is only what must be on the MCU: interrupt-driven RC pulse
capture, `pwm_set_dt()` output, and the failsafe.

The failsafe is the clearest case. It neutralises the throttle when the host
stops commanding — a crashed drive loop, a hung process, a killed ssh session.
That was verified by `kill -9`-ing the drive process so its `shutdown()` never
ran; the MCU returned the throttle to neutral on its own. Written in Python on
the Linux side it would die alongside the very thing it exists to protect
against.

### Python on the MCU is not available today

Checked on the board and upstream, as of this writing:

- `arduino-cli core search micropython` → *"No platforms matching your
  search."* The only core for this board is `arduino:zephyr`.
- All 27 App Lab example sketches are `.ino`. None is Python. The `python/`
  directories in those examples are the **Linux** half of an app.
- CircuitPython has no STM32U5 port at all — the
  [STM32 port](https://docs.circuitpython.org/en/latest/ports/stm/README.html)
  covers F4, F7 and H7. A draft PR for the UNO Q (adafruit/circuitpython
  #10674) was closed without merging.

### The MicroPython alternative

[MicroPython v1.28 does support STM32U5](https://www.cnx-software.com/2026/04/08/weact-stm32u585ciu6-core-mini-stm32u5-board-supported-by-micropython-v1-28/),
so a Python MCU firmware is not impossible in principle — just not through
Arduino's toolchain. Going that way would mean flashing MicroPython over the
Zephyr firmware, which gives up the Arduino core, `Arduino_RouterBridge` and
App Lab. The MCU would then talk over `/dev/ttyHS1` raw, and since that is
already 115200 and the MM1 protocol is two pulse widths each way, donkeycar's
existing `parts/robohat.py` would drive it with **no new Python part at all**.

That is the most Pythonic end state and reuses the most existing code. It also
means disabling `arduino-router`, which owns that UART and drives MCU reset
over `gpiochip1`, and nobody appears to have run MicroPython on this board's
STM32 yet. It is a spike worth doing before it is a plan worth committing to.

## Why there are no CircuitPython sensor drivers

`adafruit-platformdetect` does not recognise the Uno Q — it reports both chip
and board as `None` — so `import board` raises, and every
`adafruit-circuitpython-*` driver needs it:

```
>>> import board
  ... your board may not yet be supported. Please open a New Issue ...
```

Forcing a generic board does not help, so do not spend time on it. With
`BLINKA_FORCECHIP=GENERIC_X86 BLINKA_FORCEBOARD=GENERIC_LINUX_PC` you do get
`board.SCL` and `board.SDA`, but constructing the bus then fails with
`ImportError: cannot import name 'i2cPorts' from 'microcontroller.pin'`.

This costs the drive train nothing, since the MCU handles it. It does mean
`parts/imu.py`, `parts/lidar.py` and `parts/oled.py` will not import on this
board, and the `unoq` extra deliberately omits those drivers rather than
installing packages that cannot work. Reaching an I2C sensor here means going
through the MCU, the same way the servo does — see Phase 4 of
`ARDUINO_UNO_Q_PLAN.md`.

## Optional: kivy

`donkey ui` is **not** installed by the `unoq` extra: it needs kivy, which is
left out to save ~250 MB on a board with little disk to spare, and the UI
belongs on the machine you train on.
The board does have an XFCE desktop, and kivy installs and imports fine there
if you want the UI locally:

```bash
uv pip install kivy "kivy-garden.matplotlib"
```
