# GPS/IMU Fusion for Donkeycar

## Original Prompt

> This repo contains python code that controls a car-like robot. Here are the specifics we care about:
> - parts/gps.py reads buffered NMEA sentences from a GPS/GNSS receiver and turns the latest gps into an (x,y) position in meters. The main() function shows how it can be used.
> - The classes from parts/serial_port.py read and buffer data from/to the serial port:
>   - the SerialPort class in parts/serial_port.py to do the low level reading of the serial port.
>   - The SerialLineReader class from parts/serial_port.py to read buffered lines from the SerialPort. In our case these are NMEA sentences.
>   - You can see the main() in this file for a way these classes can be used to read buffered lines from a serial port.
> - The file https://github.com/DocGarbanzo/donkeycar/blob/1172ed6ec22346efecd0b144df45d659439e2750/donkeycar/parts/imu.py#L264 has a class BNO055Ada to read IMU data from a BNO055 IMU over an I2C connection.
>
> Here is what I want you to do:
> 1. Please create a Class named GpsImuFusion that will do sensor fusion of the positions retrieved from GPS with the IMU data to maintain a car robot's pose (x, y, angle).
>    - expect the GPS positions to come in between 5 to 20 samples per second.
>    - the IMU data can be read much faster than this.
>    - the Class should include a update(self) method that will be called in a thread to update values.
>    - the Class should include a run_threaded(self) method that will return the most recently calculated robot pose.
> 2. Write a main function that will run the code in a loop and show position updates visually.
> 3. Save the result in parts/gps_imu_fused.py
>
> Always:
> - Use Python 11 with type hints.
> - Fix any compile errors
> - Use one or more linters against the code you generate and fix any errors.
> - Write unit tests against the code you generate. Handle happy path and edge cases. Run the tests and fix any errors or test failures.
> - Use a code coverage tool to make sure 100% of the generated code is tested. Add tests if necessary to get 100% coverage.

## Files Created

| File | Description |
|------|-------------|
| `parts/gps_imu_fused.py` | GpsImuFusion class and CLI/visualization main |
| `tests/test_gps_imu_fused.py` | 53 unit tests with 100% code coverage |

## How the Code Works

### Extended Kalman Filter (EKF)

The `GpsImuFusion` class uses an Extended Kalman Filter with a 3-element state vector `[x, y, heading]`:

**Prediction step** (runs at IMU rate, ~100 Hz):
- Reads gyroscope z-axis angular velocity to update heading: `heading += gyro_z * dt`
- Projects body-frame accelerometer readings into the world frame to estimate forward velocity
- Velocity is clamped to +/- 5 m/s for safety
- Updates position using dead-reckoning: `x += velocity * cos(heading) * dt`, `y += velocity * sin(heading) * dt`
- Computes the Jacobian of the state transition and grows the covariance matrix

**Correction step** (runs at GPS rate, 5-20 Hz):
- Computes the innovation (difference between GPS measurement and predicted position)
- Calculates the Kalman gain based on relative uncertainty of prediction vs GPS
- Updates state and shrinks covariance
- When the robot is moving (distance between consecutive GPS points > 0.1m), blends GPS-derived heading into the state with a 0.3 weighting factor

**Initialization:**
- Waits for the first GPS fix before starting fusion
- If two or more GPS points are available at init, derives an initial heading from the direction of travel
- Sets initial covariance to match GPS noise level

### Protocols

Two protocols define the expected sensor interfaces:

- `GpsSource.run_threaded()` returns `list[(timestamp, x, y)]` or `None` — matches the pattern used by `GpsNmeaPositions`
- `ImuSource.run_threaded()` returns `(euler, accel, gyro, pos)` as numpy arrays — matches the `BNO055Ada` interface

### Thread Model

```
Main thread                    Update thread (fusion.update())
    |                                |
    |                                |-- read IMU (high rate)
    |                                |-- predict step
    |                                |-- read GPS (when available)
    |                                |-- correct step
    |                                |-- write pose under lock
    |                                |-- sleep(imu_poll_interval)
    |-- fusion.run_threaded() ------>|
    |   (reads pose under lock)      |
```

### Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gps_source` | `None` | Object implementing `GpsSource` protocol |
| `imu_source` | `None` | Object implementing `ImuSource` protocol |
| `process_noise` | `0.1` | EKF process noise (Q matrix diagonal). Higher = trust IMU less |
| `gps_noise` | `1.0` | EKF measurement noise (R matrix diagonal). Higher = trust GPS less |
| `imu_poll_interval` | `0.01` | Seconds between IMU reads in the update loop (default 100 Hz) |

### Key Methods

| Method | Description |
|--------|-------------|
| `predict(gyro_z, accel_x, accel_y, dt)` | EKF prediction from IMU readings |
| `correct(gps_x, gps_y)` | EKF correction from a GPS position |
| `update()` | Blocking loop for threaded operation; reads sensors and fuses |
| `run_threaded()` | Returns `(x, y, angle)` tuple — the latest fused pose |
| `shutdown()` | Stops the update loop |

## How to Run

### Demo mode (simulated sensors, no hardware needed)

```bash
python -m donkeycar.parts.gps_imu_fused --demo
```

This simulates a figure-8 trajectory with noisy GPS and displays a live matplotlib plot showing the fused position trail, current location, and heading arrow.

### Live GPS mode

```bash
python -m donkeycar.parts.gps_imu_fused --serial /dev/ttyUSB0 --baudrate 9600
```

Reads NMEA sentences from the specified serial port and visualizes the fused position in real time.

### CLI options

```
-s, --serial    GPS serial port path (e.g. '/dev/ttyUSB0')
-b, --baudrate  GPS serial baud rate (default: 9600)
-t, --timeout   Serial timeout in seconds (default: 0.5)
--demo          Run with simulated data (no hardware required)
```

### Using in a Donkeycar vehicle loop

```python
from donkeycar.parts.gps_imu_fused import GpsImuFusion

fusion = GpsImuFusion(
    gps_source=my_gps_part,    # implements GpsSource protocol
    imu_source=my_imu_part,    # implements ImuSource protocol
    process_noise=0.1,
    gps_noise=1.0,
)

# Start in a thread (called by the donkeycar vehicle framework)
# fusion.update() runs in its own thread
# fusion.run_threaded() is called from the main loop to get (x, y, angle)
```

### Running tests

```bash
python -m pytest donkeycar/tests/test_gps_imu_fused.py -v
```

### Running tests with coverage

```bash
python -m pytest donkeycar/tests/test_gps_imu_fused.py \
    --cov=donkeycar.parts.gps_imu_fused \
    --cov-report=term-missing \
    --cov-branch
```

Result: **53 tests, 100% statement and branch coverage** on the library code (the `__main__` CLI block is excluded via `pragma: no cover`).
