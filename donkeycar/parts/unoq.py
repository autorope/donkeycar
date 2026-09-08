"""
unoq.py - donkeycar drive train for the Arduino UNO Q.

The UNO Q's Arduino header belongs to its STM32U585, so the servo, the ESC
and the RC receiver are all the MCU's business.  The MCU runs the sketch in
arduino/unoq_rc_hat/, which emits the servo pulses and captures RC input, and
these parts talk to it over the router bridge (see unoq_bridge.py).

This is the same split as the Robo HAT MM1 (parts/robohat.py) and the DIY
Robocars RC hat, and deliberately mirrors their shape:

    UnoQRcHatDriver      steering/throttle in -1..1  ->  pulse widths
    UnoQRcHatController   RC receiver  ->  user steering/throttle and mode

The pulse maths is the MM1's, because it is the same problem and that code is
field-tested; the transport is what differs.  One set_pulse call sets both
channels and costs ~7.4ms, so the driver deliberately makes one call per
frame rather than one per channel.

Config (see the unoq section of myconfig.py):
    UNOQ_BRIDGE_ADDRESS   router socket, default unix:///var/run/arduino-router.sock
    UNOQ_STEERING_MID     pulse width for straight ahead
    UNOQ_MAX_FORWARD      pulse width for full throttle
    UNOQ_STOPPED_PWM      pulse width for neutral throttle
    UNOQ_MAX_REVERSE      pulse width for full reverse
"""
from typing import Optional
import logging
import time

import donkeycar as dk
from donkeycar.parts.unoq_bridge import UnoQBridge, UnoQBridgeError

logger = logging.getLogger(__name__)

# The sketch clamps to this range too; mirrored here so we never even ask for
# a pulse a servo cannot accept.
PULSE_MIN = 500
PULSE_MAX = 2500


def _shared_bridge(cfg, bridge: Optional[UnoQBridge] = None) -> UnoQBridge:
    """
    Both parts want the same connection, and a car uses both, so allow one to
    be passed in rather than opening two.
    """
    if bridge is not None:
        return bridge
    address = getattr(cfg, "UNOQ_BRIDGE_ADDRESS",
                      "unix:///var/run/arduino-router.sock")
    return UnoQBridge(address)


class UnoQRcHatDriver:
    """
    Drives the steering servo and the ESC through the MCU.
    Takes steering and throttle in -1..1, as donkeycar's other drive trains do.
    """

    def __init__(self, cfg, bridge: Optional[UnoQBridge] = None,
                 debug: bool = False) -> None:
        self.cfg = cfg
        self.debug = debug
        self.bridge = _shared_bridge(cfg, bridge)
        self.STEERING_MID = cfg.UNOQ_STEERING_MID
        self.MAX_FORWARD = cfg.UNOQ_MAX_FORWARD
        self.STOPPED_PWM = cfg.UNOQ_STOPPED_PWM
        self.MAX_REVERSE = cfg.UNOQ_MAX_REVERSE
        self.on = True
        # Leave the car neutral until something actually commands it.
        self.set_pulse(0.0, 0.0)

    def trim_out_of_bound_value(self, value: float) -> float:
        if value > 1:
            logger.warning(f"Value {value} is greater than 1, clamping")
            return 1.0
        if value < -1:
            logger.warning(f"Value {value} is less than -1, clamping")
            return -1.0
        return value

    def is_valid_pwm_value(self, value: float) -> bool:
        return PULSE_MIN <= value <= PULSE_MAX

    def set_pulse(self, steering: float, throttle: float) -> None:
        """
        :param steering: -1 (full left) .. 1 (full right)
        :param throttle: -1 (full reverse) .. 1 (full forward)
        """
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = dk.utils.map_range_float(
                    throttle, 0, 1.0, self.STOPPED_PWM, self.MAX_FORWARD)
            else:
                output_throttle = dk.utils.map_range_float(
                    throttle, -1.0, 0, self.MAX_REVERSE, self.STOPPED_PWM)

            output_steering = self.STEERING_MID * (1 + steering * 0.5)

            if not (self.is_valid_pwm_value(output_steering)
                    and self.is_valid_pwm_value(output_throttle)):
                logger.warning(
                    f"Invalid pulse: steering={output_steering} "
                    f"throttle={output_throttle}; not sending")
                return

            if self.debug:
                logger.info(f"steering={output_steering:.0f}us "
                            f"throttle={output_throttle:.0f}us")
            # One call for both channels: the round trip is ~7.4ms, so two
            # calls per frame would cost 15ms of a 50ms budget at 20Hz.
            self.bridge.call("set_pulse", int(output_steering), int(output_throttle))
        except UnoQBridgeError as e:
            logger.error(f"Failed to send pulse to the MCU: {e}")
        except OSError as e:
            logger.error(f"Bridge I/O error: {e}")

    def run(self, steering: float, throttle: float) -> None:
        self.set_pulse(steering, throttle)

    def shutdown(self) -> None:
        self.on = False
        try:
            # Stop the car rather than leaving the last throttle applied.
            self.bridge.call("set_pulse", int(self.STEERING_MID),
                             int(self.STOPPED_PWM))
        except Exception as e:
            logger.warning(f"Could not neutralise the drive train: {e}")


class UnoQRcHatController:
    """
    Reads the RC receiver through the MCU and reports user steering, throttle
    and mode, so the car can be driven from a transmitter.

    The sketch pushes RC values as `rc_input` notifications at ~40Hz, so this
    does not poll: values arrive on the bridge's reader thread and run() just
    reports the latest.  If the sketch's push is unavailable, set
    UNOQ_RC_POLL = True to fall back to calling its get_rc() instead.
    """

    def __init__(self, cfg, bridge: Optional[UnoQBridge] = None,
                 debug: bool = False) -> None:
        self.cfg = cfg
        self.debug = debug
        self.bridge = _shared_bridge(cfg, bridge)

        self.STEERING_MID = cfg.UNOQ_STEERING_MID
        self.MAX_FORWARD = cfg.UNOQ_MAX_FORWARD
        self.STOPPED_PWM = cfg.UNOQ_STOPPED_PWM
        self.MAX_REVERSE = cfg.UNOQ_MAX_REVERSE
        self.SHOW_STEERING_VALUE = getattr(cfg, "UNOQ_SHOW_STEERING_VALUE", False)
        self.poll = getattr(cfg, "UNOQ_RC_POLL", False)
        self.DEAD_ZONE = getattr(cfg, "JOYSTICK_DEADZONE", 0.01)

        self.angle = 0.0
        self.throttle = 0.0
        self.mode = "user"
        self.recording = False
        self.recording_latch: Optional[bool] = None
        self.last_rc_time = 0.0
        self.on = True

        if not self.poll:
            self.bridge.provide("rc_input", self._on_rc_input)
            logger.info("Listening for pushed rc_input from the MCU")

    def _on_rc_input(self, steering_us: int, throttle_us: int,
                     mode_us: int = 0) -> None:
        """
        Called on the bridge reader thread for every pushed RC frame.
        A channel with no signal reads 0, which must not be mapped as if it
        were a real pulse -- that would look like full reverse.
        """
        try:
            if steering_us:
                self.angle = dk.utils.map_range_float(
                    float(steering_us), 1000, 2000, -1.0, 1.0)
            if throttle_us:
                if throttle_us >= self.STOPPED_PWM:
                    pwm = dk.utils.map_range_float(
                        float(throttle_us), 1500, 2000,
                        self.STOPPED_PWM, self.MAX_FORWARD)
                    self.throttle = dk.utils.map_range_float(
                        pwm, self.STOPPED_PWM, self.MAX_FORWARD, 0, 1.0)
                else:
                    pwm = dk.utils.map_range_float(
                        float(throttle_us), 1000, 1500,
                        self.MAX_REVERSE, self.STOPPED_PWM)
                    self.throttle = dk.utils.map_range_float(
                        pwm, self.MAX_REVERSE, self.STOPPED_PWM, -1.0, 0)
                if abs(self.throttle) < self.DEAD_ZONE:
                    self.throttle = 0.0
            self.last_rc_time = time.time()
            if self.SHOW_STEERING_VALUE:
                logger.info(f"UNOQ: steering={steering_us}")
            if self.debug:
                logger.info(f"angle={self.angle:.2f} throttle={self.throttle:.2f}")
        except Exception as e:
            logger.error(f"Bad rc_input frame ({steering_us}, {throttle_us}): {e}")

    def read_rc(self) -> None:
        """Polling fallback for when pushed notifications are not in use."""
        try:
            reply = self.bridge.call("get_rc")
        except UnoQBridgeError as e:
            logger.error(f"Could not read RC from the MCU: {e}")
            return
        parts = [p.strip() for p in str(reply).split(",")]
        if len(parts) < 3 or not all(p.lstrip('-').isnumeric() for p in parts[:3]):
            return
        self._on_rc_input(int(parts[0]), int(parts[1]), int(parts[2]))

    def update(self) -> None:
        while self.on:
            if self.poll:
                self.read_rc()
                time.sleep(0.025)
            else:
                # Values arrive on the bridge reader thread; nothing to do.
                time.sleep(0.05)

    def run(self, img_arr=None, mode=None, recording=None):
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        self.img_arr = img_arr
        if mode is not None:
            self.mode = mode
        if recording is not None and recording != self.recording:
            self.recording = recording
        return self.angle, self.throttle, self.mode, self.recording

    def shutdown(self) -> None:
        self.on = False
        if not self.poll:
            try:
                self.bridge.unprovide("rc_input")
            except Exception as e:
                logger.warning(f"Could not unregister rc_input: {e}")
