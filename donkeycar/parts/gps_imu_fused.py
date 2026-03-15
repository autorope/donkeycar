"""
GPS/IMU sensor fusion for maintaining a car robot's pose (x, y, angle).

Uses an Extended Kalman Filter to fuse GPS position updates (5-20 Hz)
with higher-rate IMU data (gyroscope for heading, accelerometer for velocity).
"""

from __future__ import annotations

import argparse
import logging
import math
import threading
import time
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)


class GpsSource(Protocol):
    """Protocol for GPS position sources."""

    def run_threaded(self) -> list[tuple[float, float, float]] | None:
        """Return list of (timestamp, x, y) positions or None."""
        ...


class ImuSource(Protocol):
    """Protocol for IMU data sources."""

    def run_threaded(self, odometer_speed: float | None = None) -> tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray
    ]:
        """Return (euler, accel, gyro, pos) arrays."""
        ...


class SerialGps:
    """
    Concrete GpsSource implementation that reads NMEA sentences from a
    serial port via SerialLineReader and converts them to (x, y) positions
    using GpsNmeaPositions.

    Usage:
        from donkeycar.parts.serial_port import SerialPort, SerialLineReader

        serial = SerialPort('/dev/ttyUSB0', baudrate=9600, timeout=0.5)
        gps = SerialGps(serial)

        # Start the serial reader thread (reads raw NMEA lines)
        line_reader_thread = threading.Thread(target=gps.line_reader.update, daemon=True)
        line_reader_thread.start()

        # Start the GPS processing thread (converts NMEA -> positions)
        gps_thread = threading.Thread(target=gps.update, daemon=True)
        gps_thread.start()

        # Then pass gps to GpsImuFusion as gps_source
    """

    def __init__(
        self,
        serial_port: object,
        debug: bool = False,
        max_lines: int = 0,
    ) -> None:
        from donkeycar.parts.serial_port import SerialLineReader
        from donkeycar.parts.gps import GpsNmeaPositions

        self.line_reader = SerialLineReader(serial_port, max_lines=max_lines, debug=debug)
        self.position_reader = GpsNmeaPositions(debug=debug)
        self.positions: list[tuple[float, float, float]] = []
        self.lock = threading.Lock()
        self.running = True

    def update(self) -> None:
        """Thread loop: reads buffered NMEA lines and converts to positions."""
        while self.running:
            lines = self.line_reader.run_threaded()
            positions = self.position_reader.run(lines)
            if positions:
                with self.lock:
                    self.positions = positions
            time.sleep(0.01)

    def run_threaded(self) -> list[tuple[float, float, float]] | None:
        """Return accumulated GPS positions since last call, or None."""
        with self.lock:
            pos = self.positions
            self.positions = []
            return pos if pos else None

    def shutdown(self) -> None:
        """Stop the update loop and close the serial port."""
        self.running = False
        self.line_reader.shutdown()


class Bno055Imu:
    """
    Concrete ImuSource implementation that reads from a BNO055 IMU
    over I2C using the adafruit_bno055 library.

    This wraps the BNO055 sensor and provides the (euler, accel, gyro, pos)
    tuple expected by GpsImuFusion.

    Usage:
        imu = Bno055Imu()

        # Start the IMU polling thread
        imu_thread = threading.Thread(target=imu.update, daemon=True)
        imu_thread.start()

        # Then pass imu to GpsImuFusion as imu_source
    """

    def __init__(self, sensor: object | None = None, alpha: float = 0.8) -> None:
        """
        Args:
            sensor: An existing BNO055 sensor instance, or None to auto-detect
                    via I2C. Pass a sensor for testing or custom wiring.
            alpha: Exponential moving average smoothing factor (0-1).
                   1.0 = no smoothing, lower = more smoothing.
        """
        if sensor is not None:
            self.sensor = sensor
        else:  # pragma: no cover - requires I2C hardware
            import adafruit_bno055
            import board

            i2c = board.I2C()
            self.sensor = adafruit_bno055.BNO055_I2C(i2c)
        self.alpha = alpha

        self.euler = np.zeros(3)
        self.accel = np.zeros(3)
        self.gyro = np.zeros(3)
        self.pos = np.zeros(3)

        self.lock = threading.Lock()
        self.running = True

        logger.info("BNO055 IMU initialized")

    def _read_sensor(self) -> None:
        """Read raw sensor values with exponential smoothing."""
        raw_euler = self.sensor.euler
        raw_accel = self.sensor.linear_acceleration
        raw_gyro = self.sensor.gyro

        if raw_euler is not None and all(v is not None for v in raw_euler):
            new_euler = np.array(raw_euler[::-1], dtype=float)
            self.euler = self.alpha * new_euler + (1 - self.alpha) * self.euler

        if raw_accel is not None and all(v is not None for v in raw_accel):
            new_accel = np.array(raw_accel, dtype=float)
            self.accel = self.alpha * new_accel + (1 - self.alpha) * self.accel

        if raw_gyro is not None and all(v is not None for v in raw_gyro):
            new_gyro = np.array(raw_gyro, dtype=float)
            self.gyro = self.alpha * new_gyro + (1 - self.alpha) * self.gyro

    def update(self) -> None:
        """Thread loop: continuously polls the BNO055 sensor."""
        while self.running:
            try:
                self._read_sensor()
            except OSError:
                logger.warning("I2C read error from BNO055, retrying")
            time.sleep(0)  # yield to other threads

    def run_threaded(self, odometer_speed: float | None = None) -> tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray
    ]:
        """Return the latest smoothed (euler, accel, gyro, pos) readings."""
        return (
            self.euler.copy(),
            self.accel.copy(),
            self.gyro.copy(),
            self.pos.copy(),
        )

    def shutdown(self) -> None:
        """Stop the polling loop."""
        self.running = False


class GpsImuFusion:
    """
    Fuses GPS positions with IMU data using an Extended Kalman Filter
    to maintain a robot car's pose (x, y, angle).

    The state vector is [x, y, heading] where heading is in radians.

    Prediction step (IMU rate):
        - Uses gyroscope z-axis for heading rate
        - Uses accelerometer for velocity estimation

    Correction step (GPS rate):
        - Uses GPS (x, y) to correct position
    """

    def __init__(
        self,
        gps_source: GpsSource | None = None,
        imu_source: ImuSource | None = None,
        process_noise: float = 0.1,
        gps_noise: float = 1.0,
        imu_poll_interval: float = 0.01,
    ) -> None:
        self.gps_source = gps_source
        self.imu_source = imu_source
        self.imu_poll_interval = imu_poll_interval

        # EKF state: [x, y, heading]
        self.state = np.zeros(3)
        self.covariance = np.eye(3) * 100.0  # high initial uncertainty

        # Process noise (Q) - tunable
        self.process_noise = process_noise
        self.Q = np.eye(3) * process_noise

        # Measurement noise (R) for GPS [x, y]
        self.gps_noise = gps_noise
        self.R = np.eye(2) * gps_noise

        # Measurement matrix H maps state [x, y, heading] -> [x, y]
        self.H = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])

        # Tracking
        self.last_imu_time: float | None = None
        self.velocity = 0.0  # estimated forward velocity (m/s)

        # Thread-safe output
        self.lock = threading.Lock()
        self.pose: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.running = False
        self.initialized = False

    def predict(self, gyro_z: float, accel_x: float, accel_y: float, dt: float) -> None:
        """
        EKF prediction step using IMU data.

        Args:
            gyro_z: Gyroscope z-axis angular velocity (rad/s)
            accel_x: Accelerometer x-axis (m/s^2) in body frame
            accel_y: Accelerometer y-axis (m/s^2) in body frame
            dt: Time delta in seconds
        """
        if dt <= 0:
            return

        heading = self.state[2]

        # Update heading from gyroscope
        new_heading = heading + gyro_z * dt

        # Estimate velocity from accelerometer in body frame
        # Project body-frame acceleration to forward direction
        forward_accel = accel_x * math.cos(heading) + accel_y * math.sin(heading)
        self.velocity += forward_accel * dt

        # Clamp velocity to reasonable range for a car robot
        self.velocity = max(-5.0, min(5.0, self.velocity))

        # Position update using velocity and heading
        dx = self.velocity * math.cos(new_heading) * dt
        dy = self.velocity * math.sin(new_heading) * dt

        self.state[0] += dx
        self.state[1] += dy
        self.state[2] = _normalize_angle(new_heading)

        # Jacobian of the state transition
        F = np.eye(3)
        F[0, 2] = -self.velocity * math.sin(new_heading) * dt
        F[1, 2] = self.velocity * math.cos(new_heading) * dt

        # Update covariance
        self.covariance = F @ self.covariance @ F.T + self.Q * dt

    def correct(self, gps_x: float, gps_y: float) -> None:
        """
        EKF correction step using GPS measurement.

        Args:
            gps_x: GPS x position in meters
            gps_y: GPS y position in meters
        """
        z = np.array([gps_x, gps_y])

        # Innovation
        y = z - self.H @ self.state

        # Innovation covariance
        S = self.H @ self.covariance @ self.H.T + self.R

        # Kalman gain
        K = self.covariance @ self.H.T @ np.linalg.inv(S)

        # Update state
        self.state = self.state + K @ y
        self.state[2] = _normalize_angle(self.state[2])

        # Update covariance
        identity = np.eye(3)
        self.covariance = (identity - K @ self.H) @ self.covariance

    def _initialize_from_gps(self, positions: list[tuple[float, float, float]]) -> None:
        """Initialize state from first GPS readings."""
        if len(positions) >= 2:
            _, x1, y1 = positions[-2]
            _, x2, y2 = positions[-1]
            heading = math.atan2(y2 - y1, x2 - x1)
            self.state = np.array([x2, y2, heading])
        else:
            _, x, y = positions[-1]
            self.state = np.array([x, y, 0.0])

        self.covariance = np.eye(3) * self.gps_noise
        self.initialized = True
        logger.info(
            f"Initialized pose: x={self.state[0]:.2f}, y={self.state[1]:.2f}, "
            f"heading={math.degrees(self.state[2]):.1f} deg"
        )

    def _process_imu(self) -> None:
        """Read IMU and run prediction step."""
        if self.imu_source is None:
            return

        result = self.imu_source.run_threaded()
        if result is None:
            return

        euler, accel, gyro, _ = result

        now = time.time()
        if self.last_imu_time is not None:
            dt = now - self.last_imu_time
            if dt > 0:
                gyro_z = float(gyro[2]) if len(gyro) > 2 else 0.0
                accel_x = float(accel[0]) if len(accel) > 0 else 0.0
                accel_y = float(accel[1]) if len(accel) > 1 else 0.0
                self.predict(gyro_z, accel_x, accel_y, dt)
        self.last_imu_time = now

    def _process_gps(self) -> None:
        """Read GPS and run correction step."""
        if self.gps_source is None:
            return

        positions = self.gps_source.run_threaded()
        if not positions:
            return

        if not self.initialized:
            self._initialize_from_gps(positions)
            return

        # Correct with each GPS position
        for _, gps_x, gps_y in positions:
            self.correct(gps_x, gps_y)

        # Update heading from GPS if we have multiple points and are moving
        if len(positions) >= 2:
            _, x1, y1 = positions[-2]
            _, x2, y2 = positions[-1]
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if dist > 0.1:  # only update heading if moving
                gps_heading = math.atan2(y2 - y1, x2 - x1)
                # Blend GPS heading into state
                heading_diff = _normalize_angle(gps_heading - self.state[2])
                self.state[2] = _normalize_angle(self.state[2] + 0.3 * heading_diff)

    def update(self) -> None:
        """
        Called in a thread to continuously update the fused pose.
        Reads IMU at high rate, processes GPS when available.
        """
        self.running = True
        while self.running:
            if self.initialized:
                self._process_imu()

            self._process_gps()

            # Update the thread-safe output
            with self.lock:
                self.pose = (
                    float(self.state[0]),
                    float(self.state[1]),
                    float(self.state[2]),
                )

            time.sleep(self.imu_poll_interval)

    def run_threaded(self) -> tuple[float, float, float]:
        """
        Return the most recently calculated robot pose.

        Returns:
            Tuple of (x, y, angle) where x and y are in meters
            and angle is in radians.
        """
        with self.lock:
            return self.pose

    def shutdown(self) -> None:
        """Stop the update loop."""
        self.running = False


def _normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


if __name__ == "__main__":  # pragma: no cover
    import sys

    import matplotlib.pyplot as plt
    import matplotlib.animation as animation

    from donkeycar.parts.serial_port import SerialPort

    parser = argparse.ArgumentParser(description="GPS/IMU Fusion Visualizer")
    parser.add_argument("-s", "--serial", type=str, help="GPS serial port (e.g. '/dev/ttyUSB0')")
    parser.add_argument("-b", "--baudrate", type=int, default=9600, help="GPS serial baud rate")
    parser.add_argument("-t", "--timeout", type=float, default=0.5, help="Serial timeout")
    parser.add_argument("--demo", action="store_true", help="Run with simulated data")
    args = parser.parse_args()

    if args.demo:
        # Simulated GPS/IMU sources for demo
        class DemoGps:
            def __init__(self) -> None:
                self.t = 0.0
                self.noise = 0.5

            def run_threaded(self) -> list[tuple[float, float, float]] | None:
                self.t += 0.1
                # Simulate a figure-8 path with GPS noise
                x = 10.0 * math.sin(self.t * 0.2) + np.random.normal(0, self.noise)
                y = 5.0 * math.sin(self.t * 0.4) + np.random.normal(0, self.noise)
                return [(time.time(), x, y)]

        class DemoImu:
            def __init__(self) -> None:
                self.t = 0.0

            def run_threaded(self, odometer_speed: float | None = None) -> tuple[
                np.ndarray, np.ndarray, np.ndarray, np.ndarray
            ]:
                self.t += 0.01
                heading_rate = 0.2 * math.cos(self.t * 0.2)
                return (
                    np.array([0.0, 0.0, math.degrees(heading_rate)]),
                    np.array([0.1, 0.0, 0.0]),
                    np.array([0.0, 0.0, heading_rate]),
                    np.zeros(3),
                )

        gps: GpsSource = DemoGps()
        imu: ImuSource = DemoImu()
        print("Running demo with simulated sensors...")
    elif args.serial:
        serial_port = SerialPort(args.serial, baudrate=args.baudrate, timeout=args.timeout)
        serial_gps = SerialGps(serial_port)
        gps = serial_gps

        # Placeholder IMU (zeros) when no real IMU hardware is available
        class NullImu:
            def run_threaded(self, odometer_speed: float | None = None) -> tuple[
                np.ndarray, np.ndarray, np.ndarray, np.ndarray
            ]:
                return (np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3))
        imu = NullImu()

        # Start GPS line reader thread (reads raw NMEA from serial)
        line_reader_thread = threading.Thread(target=serial_gps.line_reader.update, daemon=True)
        line_reader_thread.start()
        # Start GPS processing thread (converts NMEA -> positions)
        gps_thread = threading.Thread(target=serial_gps.update, daemon=True)
        gps_thread.start()
        print(f"Reading GPS from {args.serial}...")
    else:
        print("Specify --serial for live GPS or --demo for simulated data")
        parser.print_help()
        sys.exit(1)

    fusion = GpsImuFusion(
        gps_source=gps,
        imu_source=imu,
        process_noise=0.1,
        gps_noise=1.0,
    )

    # Start fusion in a thread
    fusion_thread = threading.Thread(target=fusion.update, daemon=True)
    fusion_thread.start()

    # Set up live plot
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_title("GPS/IMU Fused Position")
    ax.set_xlabel("X (meters)")
    ax.set_ylabel("Y (meters)")
    ax.set_aspect("equal")
    ax.grid(True)

    trail_x: list[float] = []
    trail_y: list[float] = []
    (trail_line,) = ax.plot([], [], "b-", linewidth=1, alpha=0.5, label="Trail")
    (current_point,) = ax.plot([], [], "ro", markersize=8, label="Current")
    heading_arrow = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(0, 0),
        arrowprops={"arrowstyle": "->", "color": "green", "lw": 2},
    )
    status_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, verticalalignment="top", fontsize=9)

    def animate(frame: int) -> tuple:
        x, y, angle = fusion.run_threaded()
        trail_x.append(x)
        trail_y.append(y)

        # Keep last 500 points
        if len(trail_x) > 500:
            trail_x.pop(0)
            trail_y.pop(0)

        trail_line.set_data(trail_x, trail_y)
        current_point.set_data([x], [y])

        # Heading arrow
        arrow_len = 1.0
        hx = x + arrow_len * math.cos(angle)
        hy = y + arrow_len * math.sin(angle)
        heading_arrow.set_position((x, y))
        heading_arrow.xy = (hx, hy)

        status_text.set_text(
            f"x={x:.2f}m  y={y:.2f}m  heading={math.degrees(angle):.1f}°"
        )

        # Auto-scale
        if trail_x:
            margin = 5
            ax.set_xlim(min(trail_x) - margin, max(trail_x) + margin)
            ax.set_ylim(min(trail_y) - margin, max(trail_y) + margin)

        return trail_line, current_point, heading_arrow, status_text

    ax.legend(loc="upper right")
    ani = animation.FuncAnimation(fig, animate, interval=100, blit=False, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        fusion.shutdown()
        if not args.demo and args.serial:
            serial_gps.shutdown()
        print("Shutdown complete.")
