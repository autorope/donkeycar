import logging
from typing import Tuple

from donkeycar.utils import is_number_type, clamp

logger = logging.getLogger(__name__)


def differential_steering(throttle: float, steering: float, steering_zero: float = 0.01) -> Tuple[float, float]:
        """
        Turn steering angle and speed/throttle into 
        left and right wheel speeds/throttle.
        This basically slows down one wheel by the steering value
        while leaving the other wheel at the desired throttle.
        So, except for the case where the steering is zero (going straight forward),
        the effective throttle is low than the requested throttle.  
        This is different than car-like vehicles, where the effective
        forward throttle is not affected by the steering angle.
        This is is NOT inverse kinematics; it is appropriate for managing throttle
        when a user is driving the car (so the user is the controller)
        This is the algorithm used by TwoWheelSteeringThrottle.

        @Param throttle:float throttle or real speed; reverse < 0, 0 is stopped, forward > 0
        @Param steering:float -1 to 1, -1 full left, 0 straight, 1 is full right
        @Param steering_zero:float values abs(steering) <= steering_zero are considered zero.
        """
        if not is_number_type(throttle):
            logger.error("throttle must be a number")
            return 0, 0
        if throttle > 1 or throttle < -1:
            logger.warn(f"throttle = {throttle}, but must be between 1(right) and -1(left)")
        throttle = clamp(throttle, -1, 1)

        if not is_number_type(steering):
            logger.error("steering must be a number")
            return 0, 0
        if steering > 1 or steering < -1:
            logger.warn(f"steering = {steering}, but must be between 1(right) and -1(left)")
        steering = clamp(steering, -1, 1)

        left_throttle = throttle
        right_throttle = throttle
 
        if steering < -steering_zero:
            left_throttle *= (1.0 + steering)
        elif steering > steering_zero:
            right_throttle *= (1.0 - steering)

        return left_throttle, right_throttle        


class TwoWheelSteeringThrottle:
    """
    convert throttle and steering into individual
    wheel throttles in a differential drive robot
    @Param steering_zero:float values abs(steering) <= steering_zero are considered zero.
    """
    def __init__(self, steering_zero: float = 0.01) -> None:
        if not is_number_type(steering_zero):
            raise ValueError("steering_zero must be a number")
        if steering_zero > 1 or steering_zero < 0:
            raise ValueError(f"steering_zero  {steering_zero}, but must be be between 1 and zero.")
        self.steering_zero = steering_zero

    def run(self, throttle, steering):
        """
        @Param throttle:float throttle or real speed; reverse < 0, 0 is stopped, forward > 0
        @Param steering:float -1 to 1, -1 full left, 0 straight, 1 is full right
        """
        return differential_steering(throttle, steering, self.steering_zero)
 
    def shutdown(self):
        pass
