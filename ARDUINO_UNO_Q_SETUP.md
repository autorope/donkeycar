# Running donkeycar on the Arduino Uno Q

The Uno Q pairs a Qualcomm QRB2210 (aarch64, running Debian 13 trixie) with an
STM32U585 MCU. donkeycar runs on the Linux side. Everything below was verified
on a real board; see `ARDUINO_UNO_Q_PLAN.md` for the work still outstanding.

## What works, and what does not

| | |
|---|---|
| Camera | **Yes** — OpenCV reads `/dev/video0`. Use `CAMERA_TYPE = "CVCAM"`. |
| Autopilot inference | **Yes** — `ai-edge-litert` imports, so `.tflite` models run. |
| PCA9685 servo/ESC output | **Yes**, via `PinProvider.PCA9685`. Needs the I2C setup below. |
| `RPI_GPIO` / `PIGPIO` pin providers | **No** — both are Raspberry Pi only. |
| `parts/imu.py`, `parts/lidar.py`, `parts/oled.py` | **No** — see "Blinka" below. |
| `donkey ui` | Not installed by the `unoq` extra; see "Optional: kivy". |

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

## I2C setup for the PCA9685

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

`donkey ui` needs kivy, which the `unoq` extra leaves out to save ~250 MB.
The board does have an XFCE desktop, and kivy installs and imports fine there
if you want the UI locally:

```bash
uv pip install kivy "kivy-garden.matplotlib"
```
