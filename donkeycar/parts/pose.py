import logging
import time
from typing import Tuple

from donkeycar.utils import is_number_type
from donkeycar.parts.kinematics import NormalizeSteeringAngle, UnnormalizeSteeringAngle, TwoWheelSteeringThrottle
from donkeycar.parts.kinematics import Unicycle, InverseUnicycle, UnicycleUnnormalizeAngularVelocity
from donkeycar.parts.kinematics import Bicycle, InverseBicycle, BicycleUnnormalizeAngularVelocity
from donkeycar.parts.kinematics import differential_steering
from donkeycar.parts.tachometer import Tachometer, MockEncoder

logger = logging.getLogger(__name__)

class UnicycleDistance:
    def run(self, left, right):
        if is_number_type(left) and is_number_type(right):
            return (left + right) / 2.0
        else:
            logger.error("left and right must be floats")
        return 0.0


class BicyclePose:
    """
    Part that integrates encoder+tachometer+odometer+kinematics
    for the purposes of estimating the pose of a car-like vehicle over time.
    """
    def __init__(self, cfg, poll_delay_secs:float=0):
        from donkeycar.parts.serial_port import SerialPort
        from donkeycar.parts.tachometer import (Tachometer, SerialEncoder,
                                                GpioEncoder, EncoderChannel,
                                                MockEncoder)
        from donkeycar.parts.odometer import Odometer

        distance_per_revolution = cfg.WHEEL_RADIUS * 2 * 3.141592653589793

        self.poll_delay_secs = poll_delay_secs
        self.encoder = None
        self.tachometer = None
        self.odometer = None
        self.steerer = None
        self.bicycle = None
        self.Running = False

        self.inputs = (0, 0)  # (throttle, steering)
        self.reading = (0, 0, 0, 0, 0, 0, 0, 0, None)

        if cfg.ENCODER_TYPE == "GPIO":
            from donkeycar.parts import pins
            self.encoder = GpioEncoder(gpio_pin=pins.input_pin_by_id(cfg.ODOM_PIN),
                        debounce_ns=cfg.ENCODER_DEBOUNCE_NS,
                        debug=cfg.ODOM_DEBUG)
        elif cfg.ENCODER_TYPE == "arduino":
            self.encoder = SerialEncoder(serial_port=SerialPort(cfg.ODOM_SERIAL, cfg.ODOM_SERIAL_BAUDRATE), debug=cfg.ODOM_DEBUG)
        elif cfg.ENCODER_TYPE.upper() == "MOCK":
            self.encoder = MockEncoder(cfg.MOCK_TICKS_PER_SECOND)
        else:
            print("No supported encoder found")

        if self.encoder:
            self.tachometer = Tachometer(
                self.encoder,
                ticks_per_revolution=cfg.ENCODER_PPR,
                direction_mode=cfg.TACHOMETER_MODE,
                poll_delay_secs=1.0 / (cfg.DRIVE_LOOP_HZ * 3),
                debug=cfg.ODOM_DEBUG)

        if self.tachometer:
            self.odometer = Odometer(
                distance_per_revolution=distance_per_revolution,
                smoothing_count=cfg.ODOM_SMOOTHING,
                debug=cfg.ODOM_DEBUG)

            self.steerer = UnnormalizeSteeringAngle(cfg.MAX_STEERING_ANGLE)
            self.bicycle = Bicycle(cfg.WHEEL_BASE, cfg.ODOM_DEBUG)
            self.running = True
        else:
            logger.error("Unable to initialize BicyclePose part")

    def poll(self, timestamp=None):
        if self.running:
            if self.tachometer:
                throttle, steering = self.inputs
                if isinstance(self.encoder, MockEncoder):
                    self.encoder.run(throttle, timestamp)
                revolutions, timestamp = self.tachometer.run(throttle, timestamp)
                distance, velocity, timestamp = self.odometer.run(revolutions, timestamp)
                steering_angle = self.steerer.run(steering)
                self.reading = self.bicycle.run(distance, steering_angle, timestamp)

    def update(self):
        """
        This will get called on it's own thread.
        throttle: sign of throttle is use used to determine direction.
        timestamp: timestamp for update or None to use current time.
                   This is useful for creating deterministic tests.
        """
        while self.running:
            self.poll()
            time.sleep(self.poll_delay_secs)  # give other threads time

    def run_threaded(self, throttle:float=0.0, steering:float=0.0, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        if self.running and self.tachometer:
            if throttle is None:
                throttle = 0
            if steering is None:
                steering = 0

            self.inputs = (throttle, steering)

            return self.reading

        return 0, 0, 0, 0, 0, 0, 0, 0, timestamp

    def run(self, throttle:float=0.0, steering:float=0.0, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        if self.running and self.tachometer:
            if throttle is None:
                throttle = 0
            if steering is None:
                steering = 0

            self.inputs = (throttle, steering)
            self.poll(timestamp)

            return self.reading

        return 0, 0, 0, 0, 0, 0, 0, 0, timestamp


class UnicyclePose:
    """
    Part that integrates encoders+tachometers+odometers+kinematics
    for the purposes of estimating the pose of a
    differential drive vehicle over time.
    """
    def __init__(self, cfg, poll_delay_secs:float=0):
        from donkeycar.parts.serial_port import SerialPort
        from donkeycar.parts.tachometer import (SerialEncoder,
                                                GpioEncoder, EncoderChannel)
        from donkeycar.parts.odometer import Odometer

        # distance_per_revolution = cfg.ENCODER_PPR * cfg.MM_PER_TICK / 1000
        distance_per_revolution = cfg.WHEEL_RADIUS * 2 * 3.141592653589793

        self.poll_delay_secs = poll_delay_secs
        self.left_throttle = 0
        self.right_throttle = 0
        self.encoder = None
        self.tachometer = None
        self.odometer = None
        self.unicycle = None

        self.inputs = (0, 0)  # (left_throttle, right_throttle)
        self.reading = (0, 0, 0, 0, 0, 0, 0, 0, None)

        if cfg.ENCODER_TYPE == "GPIO":
            from donkeycar.parts import pins
            self.encoder = [
                GpioEncoder(gpio_pin=pins.input_pin_by_id(cfg.ODOM_PIN),
                        debounce_ns=cfg.ENCODER_DEBOUNCE_NS,
                        debug=cfg.ODOM_DEBUG),
                GpioEncoder(gpio_pin=pins.input_pin_by_id(cfg.ODOM_PIN_2),
                            debounce_ns=cfg.ENCODER_DEBOUNCE_NS,
                            debug=cfg.ODOM_DEBUG)
            ]
        elif cfg.ENCODER_TYPE == "arduino":
            serial_encoder = SerialEncoder(serial_port=SerialPort(cfg.ODOM_SERIAL, cfg.ODOM_SERIAL_BAUDRATE), debug=cfg.ODOM_DEBUG)
            self.encoder = [
                serial_encoder,
                EncoderChannel(encoder=serial_encoder, channel=1)
            ]
        elif cfg.ENCODER_TYPE.upper() == "MOCK":
            self.encoder = [
                MockEncoder(cfg.MOCK_TICKS_PER_SECOND),
                MockEncoder(cfg.MOCK_TICKS_PER_SECOND),
            ]
        else:
            print("No supported encoder found")

        if self.encoder:
            self.tachometer = [
                Tachometer(
                    self.encoder[0],
                    ticks_per_revolution=cfg.ENCODER_PPR,
                    direction_mode=cfg.TACHOMETER_MODE,
                    poll_delay_secs=0,
                    debug=cfg.ODOM_DEBUG),
                Tachometer(
                    self.encoder[1],
                    ticks_per_revolution=cfg.ENCODER_PPR,
                    direction_mode=cfg.TACHOMETER_MODE,
                    poll_delay_secs=0,
                    debug=cfg.ODOM_DEBUG)
            ]

        if self.tachometer:
            self.odometer = [
                Odometer(
                    distance_per_revolution=distance_per_revolution,
                    smoothing_count=cfg.ODOM_SMOOTHING,
                    debug=cfg.ODOM_DEBUG),
                Odometer(
                    distance_per_revolution=distance_per_revolution,
                    smoothing_count=cfg.ODOM_SMOOTHING,
                    debug=cfg.ODOM_DEBUG)
            ]
            self.unicycle = Unicycle(cfg.AXLE_LENGTH, cfg.ODOM_DEBUG)
        self.running = True

    def poll(self, timestamp=None):
        if self.running:
            if self.tachometer:
                left_timestamp = timestamp
                right_timestamp = timestamp
                left_throttle, right_throttle = self.inputs
                if isinstance(self.encoder[0], MockEncoder):
                    self.encoder[0].run(left_throttle, left_timestamp)
                    self.encoder[1].run(right_throttle, right_timestamp)

                left_revolutions, left_timestamp = self.tachometer[0].run(left_throttle, left_timestamp)
                right_revolutions, right_timestamp = self.tachometer[1].run(right_throttle, right_timestamp)

                left_distance, left_velocity, left_timestamp = self.odometer[0].run(left_revolutions, left_timestamp)
                right_distance, right_velocity, right_timestamp = self.odometer[1].run(right_revolutions, right_timestamp)

                self.reading = self.unicycle.run(left_distance, right_distance, right_timestamp)

    def update(self):
        """
        This will get called on it's own thread.
        throttle: sign of throttle is use used to determine direction.
        timestamp: timestamp for update or None to use current time.
                   This is useful for creating deterministic tests.
        """
        while self.running:
            self.poll()
            time.sleep(self.poll_delay_secs)  # give other threads time

    def run_threaded(self, throttle:float=0.0, steering:float=0.0, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        if self.running and self.tachometer:
            if throttle is None:
                throttle = 0
            if steering is None:
                steering = 0

            self.inputs = differential_steering(throttle, steering)
            return self.reading

        return 0, 0, 0, 0, 0, 0, 0, 0, timestamp

    def run(self, throttle:float=0.0, steering:float=0.0, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        if self.running and self.tachometer:
            if throttle is None:
                throttle = 0
            if steering is None:
                steering = 0

            self.inputs = differential_steering(throttle, steering)
            self.poll(timestamp)
            return self.reading

        return 0, 0, 0, 0, 0, 0, 0, 0, timestamp
