"""Tests for GPS/IMU fusion module."""

import math
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from donkeycar.parts.gps_imu_fused import (
    GpsImuFusion, SerialGps, Bno055Imu, _normalize_angle,
)


# ============================================================
# _normalize_angle tests
# ============================================================

class TestNormalizeAngle:
    def test_zero(self) -> None:
        assert _normalize_angle(0.0) == 0.0

    def test_within_range(self) -> None:
        assert _normalize_angle(1.0) == pytest.approx(1.0)
        assert _normalize_angle(-1.0) == pytest.approx(-1.0)

    def test_pi(self) -> None:
        assert _normalize_angle(math.pi) == pytest.approx(math.pi)

    def test_negative_pi(self) -> None:
        assert _normalize_angle(-math.pi) == pytest.approx(-math.pi)

    def test_greater_than_pi(self) -> None:
        result = _normalize_angle(3 * math.pi)
        assert -math.pi <= result <= math.pi
        assert result == pytest.approx(math.pi, abs=1e-10)

    def test_less_than_negative_pi(self) -> None:
        result = _normalize_angle(-3 * math.pi)
        assert -math.pi <= result <= math.pi
        assert result == pytest.approx(-math.pi, abs=1e-10)

    def test_two_pi(self) -> None:
        result = _normalize_angle(2 * math.pi)
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_large_positive(self) -> None:
        result = _normalize_angle(10 * math.pi + 0.5)
        assert -math.pi <= result <= math.pi
        assert result == pytest.approx(0.5, abs=1e-10)

    def test_large_negative(self) -> None:
        result = _normalize_angle(-10 * math.pi - 0.5)
        assert -math.pi <= result <= math.pi
        assert result == pytest.approx(-0.5, abs=1e-10)


# ============================================================
# GpsImuFusion.__init__ tests
# ============================================================

class TestGpsImuFusionInit:
    def test_default_init(self) -> None:
        fusion = GpsImuFusion()
        assert fusion.gps_source is None
        assert fusion.imu_source is None
        assert fusion.pose == (0.0, 0.0, 0.0)
        assert not fusion.running
        assert not fusion.initialized
        np.testing.assert_array_equal(fusion.state, np.zeros(3))
        assert fusion.velocity == 0.0

    def test_custom_noise_params(self) -> None:
        fusion = GpsImuFusion(process_noise=0.5, gps_noise=2.0)
        np.testing.assert_array_equal(fusion.Q, np.eye(3) * 0.5)
        np.testing.assert_array_equal(fusion.R, np.eye(2) * 2.0)

    def test_custom_poll_interval(self) -> None:
        fusion = GpsImuFusion(imu_poll_interval=0.05)
        assert fusion.imu_poll_interval == 0.05


# ============================================================
# predict() tests
# ============================================================

class TestPredict:
    def test_zero_dt_no_change(self) -> None:
        fusion = GpsImuFusion()
        state_before = fusion.state.copy()
        fusion.predict(0.1, 0.1, 0.1, 0.0)
        np.testing.assert_array_equal(fusion.state, state_before)

    def test_negative_dt_no_change(self) -> None:
        fusion = GpsImuFusion()
        state_before = fusion.state.copy()
        fusion.predict(0.1, 0.1, 0.1, -1.0)
        np.testing.assert_array_equal(fusion.state, state_before)

    def test_heading_update_from_gyro(self) -> None:
        fusion = GpsImuFusion()
        fusion.state = np.array([0.0, 0.0, 0.0])
        fusion.predict(gyro_z=1.0, accel_x=0.0, accel_y=0.0, dt=0.1)
        assert fusion.state[2] == pytest.approx(0.1, abs=1e-6)

    def test_position_update_with_velocity(self) -> None:
        fusion = GpsImuFusion()
        fusion.state = np.array([0.0, 0.0, 0.0])  # heading = 0 (east)
        fusion.velocity = 1.0  # 1 m/s forward
        fusion.predict(gyro_z=0.0, accel_x=0.0, accel_y=0.0, dt=1.0)
        assert fusion.state[0] == pytest.approx(1.0, abs=0.1)
        assert fusion.state[1] == pytest.approx(0.0, abs=0.1)

    def test_velocity_clamping_positive(self) -> None:
        fusion = GpsImuFusion()
        fusion.velocity = 4.5
        # Large acceleration to push velocity beyond 5.0
        fusion.predict(gyro_z=0.0, accel_x=10.0, accel_y=0.0, dt=1.0)
        assert fusion.velocity == 5.0

    def test_velocity_clamping_negative(self) -> None:
        fusion = GpsImuFusion()
        fusion.velocity = -4.5
        fusion.predict(gyro_z=0.0, accel_x=-10.0, accel_y=0.0, dt=1.0)
        assert fusion.velocity == -5.0

    def test_covariance_grows(self) -> None:
        fusion = GpsImuFusion()
        cov_before = fusion.covariance.copy()
        fusion.predict(gyro_z=0.0, accel_x=0.0, accel_y=0.0, dt=0.1)
        # Covariance should grow (or at least not shrink) after prediction
        assert np.trace(fusion.covariance) >= np.trace(cov_before) - 1e-10

    def test_heading_normalization(self) -> None:
        fusion = GpsImuFusion()
        fusion.state = np.array([0.0, 0.0, 3.0])  # near pi
        fusion.predict(gyro_z=1.0, accel_x=0.0, accel_y=0.0, dt=1.0)
        assert -math.pi <= fusion.state[2] <= math.pi

    def test_accel_y_contributes(self) -> None:
        fusion = GpsImuFusion()
        fusion.state = np.array([0.0, 0.0, math.pi / 4])  # heading 45 deg
        fusion.predict(gyro_z=0.0, accel_x=0.0, accel_y=1.0, dt=0.1)
        # accel_y with heading=pi/4 should contribute to velocity
        assert fusion.velocity != 0.0


# ============================================================
# correct() tests
# ============================================================

class TestCorrect:
    def test_correction_moves_state_toward_gps(self) -> None:
        fusion = GpsImuFusion(gps_noise=1.0)
        fusion.state = np.array([0.0, 0.0, 0.0])
        fusion.covariance = np.eye(3) * 10.0  # high uncertainty
        fusion.correct(5.0, 5.0)
        # State should move toward (5, 5)
        assert fusion.state[0] > 0.0
        assert fusion.state[1] > 0.0

    def test_correction_reduces_covariance(self) -> None:
        fusion = GpsImuFusion()
        fusion.covariance = np.eye(3) * 100.0
        cov_before = np.trace(fusion.covariance)
        fusion.correct(1.0, 1.0)
        cov_after = np.trace(fusion.covariance)
        assert cov_after < cov_before

    def test_low_uncertainty_resists_correction(self) -> None:
        fusion = GpsImuFusion(gps_noise=100.0)
        fusion.state = np.array([10.0, 10.0, 0.0])
        fusion.covariance = np.eye(3) * 0.001  # very certain of state
        fusion.correct(0.0, 0.0)
        # Should barely move because we're confident in current state
        assert fusion.state[0] > 5.0
        assert fusion.state[1] > 5.0

    def test_heading_stays_normalized(self) -> None:
        fusion = GpsImuFusion()
        fusion.state = np.array([0.0, 0.0, 3.1])
        fusion.correct(1.0, 1.0)
        assert -math.pi <= fusion.state[2] <= math.pi

    def test_multiple_corrections_converge(self) -> None:
        fusion = GpsImuFusion(gps_noise=0.1)
        fusion.covariance = np.eye(3) * 100.0
        target_x, target_y = 10.0, 20.0
        for _ in range(50):
            fusion.correct(target_x, target_y)
        assert fusion.state[0] == pytest.approx(target_x, abs=0.5)
        assert fusion.state[1] == pytest.approx(target_y, abs=0.5)


# ============================================================
# _initialize_from_gps() tests
# ============================================================

class TestInitializeFromGps:
    def test_single_position(self) -> None:
        fusion = GpsImuFusion()
        fusion._initialize_from_gps([(1.0, 5.0, 10.0)])
        assert fusion.state[0] == pytest.approx(5.0)
        assert fusion.state[1] == pytest.approx(10.0)
        assert fusion.state[2] == pytest.approx(0.0)
        assert fusion.initialized

    def test_two_positions_gives_heading(self) -> None:
        fusion = GpsImuFusion()
        fusion._initialize_from_gps([
            (1.0, 0.0, 0.0),
            (2.0, 1.0, 0.0),  # moving east
        ])
        assert fusion.state[0] == pytest.approx(1.0)
        assert fusion.state[1] == pytest.approx(0.0)
        assert fusion.state[2] == pytest.approx(0.0)  # heading east = 0 rad
        assert fusion.initialized

    def test_two_positions_heading_north(self) -> None:
        fusion = GpsImuFusion()
        fusion._initialize_from_gps([
            (1.0, 0.0, 0.0),
            (2.0, 0.0, 1.0),  # moving north
        ])
        assert fusion.state[2] == pytest.approx(math.pi / 2)

    def test_multiple_positions_uses_last_two(self) -> None:
        fusion = GpsImuFusion()
        fusion._initialize_from_gps([
            (1.0, 100.0, 100.0),
            (2.0, 0.0, 0.0),
            (3.0, 1.0, 1.0),  # last two: (0,0) -> (1,1)
        ])
        assert fusion.state[0] == pytest.approx(1.0)
        assert fusion.state[1] == pytest.approx(1.0)
        assert fusion.state[2] == pytest.approx(math.pi / 4)


# ============================================================
# _process_imu() tests
# ============================================================

class TestProcessImu:
    def test_no_imu_source(self) -> None:
        fusion = GpsImuFusion(imu_source=None)
        state_before = fusion.state.copy()
        fusion._process_imu()
        np.testing.assert_array_equal(fusion.state, state_before)

    def test_imu_returns_none(self) -> None:
        imu = MagicMock()
        imu.run_threaded.return_value = None
        fusion = GpsImuFusion(imu_source=imu)
        state_before = fusion.state.copy()
        fusion._process_imu()
        np.testing.assert_array_equal(fusion.state, state_before)

    def test_first_imu_read_sets_time(self) -> None:
        imu = MagicMock()
        imu.run_threaded.return_value = (
            np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3)
        )
        fusion = GpsImuFusion(imu_source=imu)
        assert fusion.last_imu_time is None
        fusion._process_imu()
        assert fusion.last_imu_time is not None

    def test_second_imu_read_triggers_predict(self) -> None:
        imu = MagicMock()
        imu.run_threaded.return_value = (
            np.zeros(3),
            np.array([1.0, 0.0, 0.0]),  # accel x
            np.array([0.0, 0.0, 0.5]),  # gyro z
            np.zeros(3),
        )
        fusion = GpsImuFusion(imu_source=imu)
        fusion.last_imu_time = time.time() - 0.1
        state_before = fusion.state.copy()
        fusion._process_imu()
        # State should have changed due to prediction
        assert not np.array_equal(fusion.state, state_before)

    def test_imu_zero_dt_no_predict(self) -> None:
        """When two IMU reads happen at the same time, dt=0, no prediction."""
        imu = MagicMock()
        imu.run_threaded.return_value = (
            np.zeros(3), np.zeros(3), np.array([0.0, 0.0, 1.0]), np.zeros(3)
        )
        fusion = GpsImuFusion(imu_source=imu)
        now = time.time()
        fusion.last_imu_time = now
        state_before = fusion.state.copy()
        with patch("donkeycar.parts.gps_imu_fused.time") as mock_time:
            mock_time.time.return_value = now  # same time => dt = 0
            fusion._process_imu()
        np.testing.assert_array_equal(fusion.state, state_before)

    def test_imu_with_short_arrays(self) -> None:
        """Test IMU with arrays shorter than expected."""
        imu = MagicMock()
        imu.run_threaded.return_value = (
            np.zeros(1),
            np.zeros(0),  # empty accel
            np.zeros(1),  # short gyro
            np.zeros(0),
        )
        fusion = GpsImuFusion(imu_source=imu)
        fusion.last_imu_time = time.time() - 0.1
        # Should not raise
        fusion._process_imu()


# ============================================================
# _process_gps() tests
# ============================================================

class TestProcessGps:
    def test_no_gps_source(self) -> None:
        fusion = GpsImuFusion(gps_source=None)
        assert not fusion.initialized
        fusion._process_gps()
        assert not fusion.initialized

    def test_gps_returns_empty(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = []
        fusion = GpsImuFusion(gps_source=gps)
        fusion._process_gps()
        assert not fusion.initialized

    def test_gps_returns_none(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = None
        fusion = GpsImuFusion(gps_source=gps)
        fusion._process_gps()
        assert not fusion.initialized

    def test_first_gps_initializes(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [(1.0, 5.0, 10.0)]
        fusion = GpsImuFusion(gps_source=gps)
        fusion._process_gps()
        assert fusion.initialized
        assert fusion.state[0] == pytest.approx(5.0)
        assert fusion.state[1] == pytest.approx(10.0)

    def test_subsequent_gps_corrects(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [(1.0, 5.0, 10.0)]
        fusion = GpsImuFusion(gps_source=gps)
        fusion.initialized = True
        fusion.covariance = np.eye(3) * 10.0
        state_before = fusion.state.copy()
        fusion._process_gps()
        # State should move toward GPS reading
        assert fusion.state[0] != state_before[0]

    def test_gps_heading_update_when_moving(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [
            (1.0, 0.0, 0.0),
            (2.0, 1.0, 0.0),  # moving east
        ]
        fusion = GpsImuFusion(gps_source=gps, gps_noise=0.1)
        fusion.initialized = True
        fusion.state = np.array([0.0, 0.0, math.pi / 2])  # facing north
        fusion.covariance = np.eye(3) * 0.01
        fusion._process_gps()
        # Heading should move toward 0 (east)
        assert fusion.state[2] < math.pi / 2

    def test_gps_heading_no_update_when_stationary(self) -> None:
        gps = MagicMock()
        # Very close points — distance < 0.1
        gps.run_threaded.return_value = [
            (1.0, 0.0, 0.0),
            (2.0, 0.01, 0.01),
        ]
        fusion = GpsImuFusion(gps_source=gps, gps_noise=0.001)
        fusion.initialized = True
        fusion.state = np.array([0.0, 0.0, 1.5])
        fusion.covariance = np.eye(3) * 0.001
        heading_before = fusion.state[2]
        fusion._process_gps()
        # Heading should not be blended (dist < 0.1)
        # But correction still applies, so just check it didn't use GPS heading blend
        # The heading changes only from the correct() call, not from the GPS heading blend
        assert fusion.state[2] == pytest.approx(heading_before, abs=0.5)

    def test_gps_multiple_corrections(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [
            (1.0, 1.0, 1.0),
            (2.0, 2.0, 2.0),
            (3.0, 3.0, 3.0),
        ]
        fusion = GpsImuFusion(gps_source=gps)
        fusion.initialized = True
        fusion.covariance = np.eye(3) * 10.0
        fusion._process_gps()
        # Should have applied 3 corrections
        assert fusion.state[0] > 0.0
        assert fusion.state[1] > 0.0


# ============================================================
# update() / run_threaded() / shutdown() tests
# ============================================================

class TestUpdateThread:
    def test_run_threaded_returns_default(self) -> None:
        fusion = GpsImuFusion()
        assert fusion.run_threaded() == (0.0, 0.0, 0.0)

    def test_update_loop_runs_and_stops(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [(1.0, 5.0, 10.0)]
        fusion = GpsImuFusion(gps_source=gps, imu_poll_interval=0.01)
        thread = threading.Thread(target=fusion.update, daemon=True)
        thread.start()
        time.sleep(0.1)
        assert fusion.running
        fusion.shutdown()
        thread.join(timeout=1.0)
        assert not fusion.running

    def test_update_sets_pose(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [(1.0, 5.0, 10.0)]
        fusion = GpsImuFusion(gps_source=gps, imu_poll_interval=0.01)
        thread = threading.Thread(target=fusion.update, daemon=True)
        thread.start()
        time.sleep(0.15)
        pose = fusion.run_threaded()
        fusion.shutdown()
        thread.join(timeout=1.0)
        assert pose[0] == pytest.approx(5.0, abs=1.0)
        assert pose[1] == pytest.approx(10.0, abs=1.0)

    def test_update_with_imu(self) -> None:
        gps = MagicMock()
        gps.run_threaded.return_value = [(1.0, 5.0, 10.0)]
        imu = MagicMock()
        imu.run_threaded.return_value = (
            np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3)
        )
        fusion = GpsImuFusion(
            gps_source=gps, imu_source=imu, imu_poll_interval=0.01
        )
        thread = threading.Thread(target=fusion.update, daemon=True)
        thread.start()
        time.sleep(0.15)
        x, y, angle = fusion.run_threaded()
        fusion.shutdown()
        thread.join(timeout=1.0)
        # Should be initialized and have a pose
        assert fusion.initialized
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert isinstance(angle, float)

    def test_shutdown(self) -> None:
        fusion = GpsImuFusion()
        fusion.running = True
        fusion.shutdown()
        assert not fusion.running

    def test_update_no_sources(self) -> None:
        """Update with no GPS/IMU should still run without errors."""
        fusion = GpsImuFusion(imu_poll_interval=0.01)
        thread = threading.Thread(target=fusion.update, daemon=True)
        thread.start()
        time.sleep(0.05)
        fusion.shutdown()
        thread.join(timeout=1.0)
        assert fusion.pose == (0.0, 0.0, 0.0)


# ============================================================
# Integration tests
# ============================================================

class TestIntegration:
    def test_full_predict_correct_cycle(self) -> None:
        """Test a full cycle of predict then correct."""
        fusion = GpsImuFusion(process_noise=0.1, gps_noise=1.0)
        fusion.initialized = True
        fusion.state = np.array([0.0, 0.0, 0.0])
        fusion.covariance = np.eye(3) * 1.0

        # Simulate moving east at 1 m/s
        for i in range(10):
            fusion.predict(gyro_z=0.0, accel_x=1.0, accel_y=0.0, dt=0.1)

        # GPS says we're at (1, 0)
        fusion.correct(1.0, 0.0)

        assert fusion.state[0] == pytest.approx(1.0, abs=1.0)
        assert fusion.state[1] == pytest.approx(0.0, abs=0.5)

    def test_circular_motion(self) -> None:
        """Test that the filter can track circular motion."""
        fusion = GpsImuFusion(process_noise=0.01, gps_noise=0.5)
        fusion.initialized = True
        fusion.state = np.array([1.0, 0.0, math.pi / 2])
        fusion.covariance = np.eye(3) * 0.5

        radius = 1.0
        angular_vel = 0.5  # rad/s
        dt = 0.1

        for step in range(20):
            t = step * dt
            # True position on circle
            true_x = radius * math.cos(angular_vel * t)
            true_y = radius * math.sin(angular_vel * t)

            fusion.predict(gyro_z=angular_vel, accel_x=0.0, accel_y=0.0, dt=dt)
            if step % 5 == 0:
                fusion.correct(true_x, true_y)

        # Should be somewhat near the circle
        dist_from_origin = math.sqrt(fusion.state[0] ** 2 + fusion.state[1] ** 2)
        assert dist_from_origin < 5.0  # reasonable bound

    def test_gps_only_tracking(self) -> None:
        """With no IMU, GPS corrections alone should track position."""
        fusion = GpsImuFusion(gps_noise=0.1)
        fusion.initialized = True
        fusion.covariance = np.eye(3) * 10.0

        points = [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
        for x, y in points:
            fusion.correct(x, y)

        # EKF averages corrections weighted by uncertainty,
        # so state converges toward but may not reach the last point
        assert fusion.state[0] == pytest.approx(2.0, abs=1.5)
        assert fusion.state[1] == pytest.approx(0.0, abs=1.0)


# ============================================================
# SerialGps tests
# ============================================================

class TestSerialGps:
    def _make_serial_gps(self) -> SerialGps:
        """Create a SerialGps with mocked serial port internals."""
        mock_serial = MagicMock()
        mock_serial.start.return_value = mock_serial
        mock_serial.clear.return_value = mock_serial
        mock_serial.buffered.return_value = 0
        mock_serial.is_open = True
        with patch("donkeycar.parts.serial_port.dk_platform") as mock_platform:
            mock_platform.is_mac.return_value = False
            gps = SerialGps(mock_serial, debug=False, max_lines=5)
        return gps

    def test_init(self) -> None:
        gps = self._make_serial_gps()
        assert gps.running is True
        assert gps.positions == []
        assert gps.line_reader is not None
        assert gps.position_reader is not None

    def test_run_threaded_returns_none_when_empty(self) -> None:
        gps = self._make_serial_gps()
        assert gps.run_threaded() is None

    def test_run_threaded_returns_positions_and_clears(self) -> None:
        gps = self._make_serial_gps()
        gps.positions = [(1.0, 100.0, 200.0), (2.0, 101.0, 201.0)]
        result = gps.run_threaded()
        assert result == [(1.0, 100.0, 200.0), (2.0, 101.0, 201.0)]
        # Should be cleared after read
        assert gps.run_threaded() is None

    def test_update_reads_and_stores_positions(self) -> None:
        gps = self._make_serial_gps()
        # Mock the line_reader to return NMEA-like lines
        gps.line_reader.run_threaded = MagicMock(return_value=[])
        gps.position_reader.run = MagicMock(return_value=[
            (1.0, 500.0, 600.0),
        ])

        # Run one iteration of update then stop
        call_count = 0
        original_sleep = time.sleep

        def stop_after_one(duration: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                gps.running = False
            original_sleep(0)

        with patch("donkeycar.parts.gps_imu_fused.time.sleep", side_effect=stop_after_one):
            gps.update()

        result = gps.run_threaded()
        assert result == [(1.0, 500.0, 600.0)]

    def test_update_skips_empty_positions(self) -> None:
        gps = self._make_serial_gps()
        gps.line_reader.run_threaded = MagicMock(return_value=[])
        gps.position_reader.run = MagicMock(return_value=[])

        call_count = 0
        original_sleep = time.sleep

        def stop_after_one(duration: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                gps.running = False
            original_sleep(0)

        with patch("donkeycar.parts.gps_imu_fused.time.sleep", side_effect=stop_after_one):
            gps.update()

        assert gps.run_threaded() is None

    def test_shutdown(self) -> None:
        gps = self._make_serial_gps()
        gps.running = True
        gps.shutdown()
        assert gps.running is False


# ============================================================
# Bno055Imu tests
# ============================================================

class TestBno055Imu:
    def _make_imu(self) -> Bno055Imu:
        """Create a Bno055Imu with a mock sensor (no hardware needed)."""
        mock_sensor = MagicMock()
        mock_sensor.euler = (10.0, 20.0, 30.0)
        mock_sensor.linear_acceleration = (0.1, 0.2, 0.3)
        mock_sensor.gyro = (0.01, 0.02, 0.03)
        imu = Bno055Imu(sensor=mock_sensor, alpha=0.8)
        return imu

    def test_init(self) -> None:
        imu = self._make_imu()
        assert imu.running is True
        assert imu.alpha == 0.8
        np.testing.assert_array_equal(imu.euler, np.zeros(3))
        np.testing.assert_array_equal(imu.accel, np.zeros(3))
        np.testing.assert_array_equal(imu.gyro, np.zeros(3))
        np.testing.assert_array_equal(imu.pos, np.zeros(3))

    def test_run_threaded_returns_copies(self) -> None:
        imu = self._make_imu()
        imu.euler = np.array([1.0, 2.0, 3.0])
        imu.accel = np.array([4.0, 5.0, 6.0])
        imu.gyro = np.array([7.0, 8.0, 9.0])
        imu.pos = np.array([10.0, 11.0, 12.0])

        euler, accel, gyro, pos = imu.run_threaded()
        np.testing.assert_array_equal(euler, [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(accel, [4.0, 5.0, 6.0])
        np.testing.assert_array_equal(gyro, [7.0, 8.0, 9.0])
        np.testing.assert_array_equal(pos, [10.0, 11.0, 12.0])

        # Verify they are copies, not references
        euler[0] = 999.0
        assert imu.euler[0] == 1.0

    def test_run_threaded_with_odometer_speed(self) -> None:
        imu = self._make_imu()
        result = imu.run_threaded(odometer_speed=1.5)
        assert len(result) == 4

    def test_read_sensor_applies_smoothing(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = (0.0, 0.0, 90.0)
        imu.sensor.linear_acceleration = (1.0, 0.0, 0.0)
        imu.sensor.gyro = (0.0, 0.0, 0.5)

        imu._read_sensor()

        # With alpha=0.8 and initial values of 0:
        # new = 0.8 * reading + 0.2 * 0 = 0.8 * reading
        # euler is reversed: (90, 0, 0) * 0.8
        assert imu.euler[0] == pytest.approx(90.0 * 0.8, abs=0.01)
        assert imu.accel[0] == pytest.approx(1.0 * 0.8, abs=0.01)
        assert imu.gyro[2] == pytest.approx(0.5 * 0.8, abs=0.01)

    def test_read_sensor_handles_none_euler(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = None
        imu.sensor.linear_acceleration = (1.0, 0.0, 0.0)
        imu.sensor.gyro = (0.0, 0.0, 0.5)
        imu._read_sensor()
        # euler should remain zeros
        np.testing.assert_array_equal(imu.euler, np.zeros(3))

    def test_read_sensor_handles_none_accel(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = (0.0, 0.0, 90.0)
        imu.sensor.linear_acceleration = None
        imu.sensor.gyro = (0.0, 0.0, 0.5)
        imu._read_sensor()
        np.testing.assert_array_equal(imu.accel, np.zeros(3))

    def test_read_sensor_handles_none_gyro(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = (0.0, 0.0, 90.0)
        imu.sensor.linear_acceleration = (1.0, 0.0, 0.0)
        imu.sensor.gyro = None
        imu._read_sensor()
        np.testing.assert_array_equal(imu.gyro, np.zeros(3))

    def test_read_sensor_handles_none_values_in_tuple(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = (None, 0.0, 90.0)
        imu.sensor.linear_acceleration = (1.0, None, 0.0)
        imu.sensor.gyro = (0.0, 0.0, None)
        imu._read_sensor()
        # All should remain zeros because of the `all(v is not None)` check
        np.testing.assert_array_equal(imu.euler, np.zeros(3))
        np.testing.assert_array_equal(imu.accel, np.zeros(3))
        np.testing.assert_array_equal(imu.gyro, np.zeros(3))

    def test_update_loop_runs_and_stops(self) -> None:
        imu = self._make_imu()
        imu.sensor.euler = (0.0, 0.0, 0.0)
        imu.sensor.linear_acceleration = (0.0, 0.0, 0.0)
        imu.sensor.gyro = (0.0, 0.0, 0.0)

        thread = threading.Thread(target=imu.update, daemon=True)
        thread.start()
        time.sleep(0.05)
        assert imu.running
        imu.shutdown()
        thread.join(timeout=1.0)
        assert not imu.running

    def test_update_handles_oserror(self) -> None:
        """I2C errors should be caught and not crash the update loop."""
        imu = self._make_imu()
        call_count = 0

        def failing_read() -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError("I2C bus error")
            imu.running = False

        imu._read_sensor = failing_read
        imu.update()
        # Should have survived the OSError and kept running
        assert call_count >= 2

    def test_shutdown(self) -> None:
        imu = self._make_imu()
        imu.running = True
        imu.shutdown()
        assert imu.running is False
