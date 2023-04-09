import math
from donkeycar.utils import map_frange, sign

class VelocityNormalize:
    """
    Normalize a velocity into to range 0..1.0
    given the measured minimum and maximum speeds.
    @param min_speed: speed below which car stalls
    @param max_speed: car's top speed (may be a target, not a limit)
    @param min_normal_speed: the normalized throttle corresponding to min_speed
    """
    def __init__(self, min_speed:float, max_speed:float, min_normal_speed:float=0.1) -> None:
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.min_normal_speed = min_normal_speed

    def run(self, speed:float) -> float:
        s = sign(speed)
        speed = abs(speed)
        if speed < self.min_speed:
            return 0.0
        if speed >= self.max_speed:
            return s * 1.0
        return s * map_frange(
            speed, 
            self.min_speed, self.max_speed, 
            self.min_normal_speed, 1.0)

    def shutdown(self):
        pass


class VelocityUnnormalize:
    """
    Map normalized speed (0 to 1) to actual speed
    """
    def __init__(self, min_speed:float, max_speed:float, min_normal_speed:float=0.1) -> None:
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.min_normal_speed = min_normal_speed

    def run(self, speed:float) -> float:
        s = sign(speed)
        speed = abs(speed)
        if speed < self.min_normal_speed:
            return 0.0
        if speed >= 1.0:
            return s * 1.0
        return s * map_frange(
            speed, 
            self.min_normal_speed, 1.0,
            self.min_speed, self.max_speed)

    def shutdown(self):
        pass


class StepSpeedController:
    """
    Simplistic constant step controller.
    Just increases speed if we are too slow 
    or decreases speed if we are too fast.
    Includes feed-forward when reversing direction
    or starting from stopped.
    """
    def __init__(self, min_speed:float, max_speed:float, throttle_step:float=1/255, min_throttle:float=0) -> None:
        """
        @param min_speed is speed below which vehicle stalls (so slowest stable working speed)
        @param max_speed is speed at maximum throttle
        @param throttle_steps is number of steps in working range of throttle (min_throttle to 1.0)
        @param min_throttle is throttle that corresponds to min_speed; the throttle below which the vehicle stalls.
        """
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.min_throttle = min_throttle
        self.step_size = throttle_step
    
    def run(self, throttle:float, speed:float, target_speed:float) -> float:
        """
        Given current throttle and speed and a target speed, 
        calculate a new throttle to attain target speed
        @param throttle is current throttle (-1 to 1)
        @param speed is current speed where reverse speeds are negative
        @param throttle_steps number of steps between min_throttle and max_throttle=1.0
        @param min_throttle is throttle that corresponds to min_speed
        max_throttle is assumed to be 1.0
        """
        if speed is None or target_speed is None:
            # no speed to control, just return throttle
            return throttle

        target_direction = sign(target_speed)
        direction = sign(speed)

        target_speed = abs(target_speed)
        speed = abs(speed)

        # 
        # treat speed below minimum as zero
        #
        if target_speed < self.min_speed:
            return 0

        #
        # when changing direction or starting from stopped,
        # calculate a feed-forward throttle estimate 
        # so we jump into a working range quickly
        #
        if direction != target_direction:
            # if we are going too fast to just reverse, then slow down first
            if speed > self.min_speed:
                return 0
            
            # calculate first estimate of throttle to achieve target speed
            return target_direction * map_frange(target_speed, self.min_speed, self.max_speed, self.min_throttle, 1.0)

        # 
        # modify throttle
        #
        if speed > target_speed:
            # too fast, slow down
            throttle -= self.step_size
        elif speed > target_speed:
            # too slow, speed up
            throttle += self.step_size

        return target_direction * throttle
