import logging
import math
import time
from typing import Tuple

from donkeycar.utils import compare_to, sign, is_number_type, clamp

logger = logging.getLogger(__name__)


def limit_angle(angle:float):
    """
    limit angle to pi to -pi radians (one full circle)
    """
    return math.atan2(math.sin(angle), math.cos(angle))
    # twopi = math.pi * 2
    # while(angle > math.pi):
    #     angle -= twopi
    # while(angle < -math.pi):
    #     angle += twopi
    # return angle


class Pose2D:
    def __init__(self, x:float=0.0, y:float=0.0, angle:float=0.0) -> None:
        self.x = x
        self.y = y
        self.angle = angle


class Bicycle:
    """
    Bicycle forward kinematics for a car-like vehicle (Ackerman steering),
    using the point midway between the front wheels as a reference point,
    takes the steering angle in radians and output of the odometer 
    and turns those into:
    - forward distance and velocity of the reference point between the front wheels,
    - pose; angle aligned (x,y) position and orientation in radians
    - pose velocity; change in angle aligned position and orientation per second
    @param wheel_base: distance between the front and back wheels

    NOTE: this version uses the point midway between the front wheels
          as the point of reference.
    see https://thef1clan.com/2020/09/21/vehicle-dynamics-the-kinematic-bicycle-model/
    """
    def __init__(self, wheel_base:float, debug=False):
        self.wheel_base:float = wheel_base
        self.debug = debug
        self.timestamp:float = 0
        self.forward_distance:float = 0
        self.forward_velocity:float = 0
        self.steering_angle = None
        self.pose = Pose2D()
        self.pose_velocity = Pose2D()
        self.running:bool = True

    def run(self, forward_distance:float, steering_angle:float, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        """
        params
            forward_distance: distance the reference point between the
                              front wheels has travelled
            steering_angle: angle in radians of the front 'wheel' from forward.
                            In this case left is positive, right is negative,
                            and directly forward is zero.
            timestamp: time of distance readings or None to use current time
        returns
            distance
            velocity
            x is horizontal position of reference point midway between front wheels
            y is vertical position of reference point midway between front wheels
            angle is orientation in radians of the vehicle along it's wheel base
                  (along the line between the reference points midway between
                   the front wheels and and midway between the back wheels)
            x' is the horizontal velocity (rate of change of reference point along horizontal axis)
            y' is the vertical velocity (rate of change of reference point along vertical axis)
            angle' is the angular velocity (rate of change of orientation)
            timestamp

        """
        if timestamp is None:
            timestamp = time.time()

        steering_angle = limit_angle(steering_angle)

        if self.running:
            if 0 == self.timestamp:
                self.forward_distance = 0
                self.forward_velocity=0
                self.steering_angle = steering_angle
                self.pose = Pose2D()
                self.pose_velocity = Pose2D()
                self.timestamp = timestamp
            elif timestamp > self.timestamp:
                #
                # changes from last run
                #
                delta_time = timestamp - self.timestamp
                delta_distance = forward_distance - self.forward_distance
                delta_steering_angle = steering_angle - self.steering_angle

                #
                # new position and orientation
                # assumes delta_time is small and so assumes movement is linear
                #
                # x, y, angle = update_bicycle_front_wheel_pose(
                #     self.pose,
                #     self.wheel_base,
                #     self.steering_angle + delta_steering_angle / 2,
                #     delta_distance)
                #
                # #
                # # update velocities
                # #
                # forward_velocity = delta_distance / delta_time
                # self.pose_velocity.angle = (angle - self.pose.angle) / delta_time
                # self.pose_velocity.x = (x - self.pose.x) / delta_time
                # self.pose_velocity.y = (y - self.pose.y) / delta_time
                # #
                # # update pose
                # #
                # self.pose.x = x
                # self.pose.y = y
                # self.pose.angle = angle

                #
                # new velocities
                #
                forward_velocity = delta_distance / delta_time
                self.pose_velocity.angle = bicycle_angular_velocity(self.wheel_base, forward_velocity, steering_angle)
                delta_angle = self.pose_velocity.angle * delta_time
                estimated_angle = limit_angle(self.pose.angle + delta_angle / 2)
                self.pose_velocity.x = forward_velocity * math.cos(estimated_angle)
                self.pose_velocity.y = forward_velocity * math.sin(estimated_angle)

                #
                # new pose
                #
                self.pose.x = self.pose.x + self.pose_velocity.x * delta_time
                self.pose.y = self.pose.y + self.pose_velocity.y * delta_time
                self.pose.angle = limit_angle(self.pose.angle + delta_angle)

                self.steering_angle = steering_angle

                #
                # update odometry
                #
                self.forward_distance = forward_distance
                self.forward_velocity = forward_velocity

                self.timestamp = timestamp

            result = (
                self.forward_distance,
                self.forward_velocity,
                self.pose.x, self.pose.y, self.pose.angle,
                self.pose_velocity.x, self.pose_velocity.y, self.pose_velocity.angle,
                self.timestamp
            )
            if self.debug:
                logger.info(result)
            return result

        return 0, 0, 0, 0, 0, 0, 0, 0, self.timestamp

    def shutdown(self):
        self.running = False


class InverseBicycle:
    """
    Bicycle inverse kinematics for a car-like vehicle (Ackerman steering)
    takes the forward velocity and the angular velocity in radians/second
    and converts these to:
    - forward velocity (pass through),
    - steering angle in radians
    @param wheel_base: distance between the front and back wheels

    NOTE: this version uses the point midway between the rear wheels
          as the point of reference.
    see https://thef1clan.com/2020/09/21/vehicle-dynamics-the-kinematic-bicycle-model/
    """
    def __init__(self, wheel_base:float, debug=False):
        self.wheel_base:float = wheel_base
        self.debug = debug
        self.timestamp:float = 0

    def run(self, forward_velocity:float, angular_velocity:float, timestamp:float=None) -> Tuple[float, float, float]:
        """
        @param forward_velocity:float in meters per second
        @param angular_velocity:float in radians per second
        @return tuple
                - forward_velocity:float in meters per second (basically a pass through)
                - steering_angle:float in radians
                - timestamp:float
        """
        if timestamp is None:
            timestamp = time.time()

        """
        derivation from bicycle model:
        angular_velocity = forward_velocity * math.tan(steering_angle) / self.wheel_base
        math.tan(steering_angle) = angular_velocity * self.wheel_base / forward_velocity
        steering_angle = math.atan(angular_velocity * self.wheel_base / forward_velocity)
        """
        steering_angle = bicycle_steering_angle(self.wheel_base, forward_velocity, angular_velocity)        
        self.timestamp = timestamp

        return forward_velocity, steering_angle, timestamp


def update_bicycle_front_wheel_pose(front_wheel, wheel_base, steering_angle, distance):
    """
    Calculates the ending position of the front wheel of a bicycle kinematics model.
    This is expected to be called at a high rate such that we can model the
    the travel as a line rather than an arc.

    Arguments:
    front_wheel -- starting pose at front wheel as tuple of (x, y, angle) where
                x -- initial x-coordinate of the front wheel (float)
                y -- initial y-coordinate of the front wheel (float)
                angle -- initial orientation of the vehicle along it's wheel base (in radians) (float)
    wheel_base -- length of the wheel base (float)
    steering_angle -- steering angle (in radians) (float)
    distance -- distance travelled by the vehicle (float)

    Returns:
    A tuple (x_f, y_f, theta_f) representing the ending position and orientation of the front wheel.
    x_f -- ending x-coordinate of the front wheel (float)
    y_f -- ending y-coordinate of the front wheel (float)
    theta_f -- ending orientation of the vehicle (in radians) (float)
    """
    if distance == 0:
        return front_wheel

    if steering_angle == 0:
        x = front_wheel.x + distance * math.cos(front_wheel.angle)
        y = front_wheel.y + distance * math.sin(front_wheel.angle)
        theta = front_wheel.angle
    else:
        theta = limit_angle(front_wheel.angle + math.tan(steering_angle) * distance / wheel_base)
        x = front_wheel.x + distance * math.cos(theta)
        y = front_wheel.y + distance * math.sin(theta)
    return x, y, theta


def bicycle_steering_angle(wheel_base:float, forward_velocity:float, angular_velocity:float) -> float:
    """
    Calculate bicycle steering for the vehicle from the angular velocity.
    For car-like vehicles, calculate the angular velocity using 
    the bicycle model and the measured max forward velocity and max steering angle.
    """
    #
    # derivation from bicycle model:
    # angular_velocity = forward_velocity * math.tan(steering_angle) / self.wheel_base
    # math.tan(steering_angle) = angular_velocity * self.wheel_base / forward_velocity
    # steering_angle = math.atan(angular_velocity * self.wheel_base / forward_velocity)
    #
    # return math.atan(angular_velocity * wheel_base / forward_velocity)
    return limit_angle(math.asin(angular_velocity * wheel_base / forward_velocity))


def bicycle_angular_velocity(wheel_base:float, forward_velocity:float, steering_angle:float) -> float:
    """
    Calculate angular velocity for the vehicle from the bicycle steering angle.
    For car-like vehicles, calculate the angular velocity using 
    the bicycle model and the measured max forward velocity and max steering angle.
    """
    #
    # for car-like (bicycle model) vehicle, for the back axle:
    # angular_velocity = forward_velocity * math.tan(steering_angle) /  wheel_base if velocity is from rear wheels
    # angular_velocity = forward_velocity * math.tan(steering_angle) /  wheel_base if velocity is from front wheels
    #
    # return forward_velocity * math.tan(steering_angle) / wheel_base # velocity for rear wheel
    return forward_velocity * math.sin(steering_angle) / wheel_base  # velocity of front wheel


class BicycleNormalizeAngularVelocity:
    """
    For a car-like vehicle, convert an angular velocity in radians per second
    to a value between -1 and 1 inclusive.
    """
    def __init__(self, wheel_base:float, max_forward_velocity:float, max_steering_angle:float) -> None:
        self.max_angular_velocity = bicycle_angular_velocity(wheel_base, max_forward_velocity, max_steering_angle)

    def run(self, angular_velocity:float) -> float:
        return angular_velocity / self.max_angular_velocity


class BicycleUnnormalizeAngularVelocity:
    """
    For a car-like vehicle, convert a normalized angular velocity in range -1 to 1
    into a real angular velocity in radians per second.
    """
    def __init__(self, wheel_base:float, max_forward_velocity:float, max_steering_angle:float) -> None:
        self.max_angular_velocity = bicycle_angular_velocity(wheel_base, max_forward_velocity, max_steering_angle)

    def run(self, normalized_angular_velocity:float) -> float:
        if abs(normalized_angular_velocity) > 1:
            logger.error("Warning: normalized_angular_velocity must be between -1 and 1")
        return normalized_angular_velocity * self.max_angular_velocity


class Unicycle:
    """
    Unicycle forward kinematics takes the output of the 
    left and right odometers and 
    turns those into:
    - forward distance and velocity,
    - pose; angle aligned (x,y) position and orientation in radians
    - pose velocity; change in angle aligned position and orientation per second
    axle_length: distance between the two drive wheels
    wheel_radius: radius of wheel; must be in same units as axle_length
                  It is assumed that both wheels have the same radius
    see http://faculty.salina.k-state.edu/tim/robotics_sg/Control/kinematics/unicycle.html
    """
    def __init__(self, axle_length:float, debug=False):
        self.axle_length:float = axle_length
        self.debug = debug
        self.timestamp:float = 0
        self.left_distance:float = 0
        self.right_distance:float = 0
        self.velocity:float = 0
        self.pose = Pose2D()
        self.pose_velocity = Pose2D()
        self.running:bool = True

    def run(self, left_distance:float, right_distance:float, timestamp:float=None) -> Tuple[float, float, float, float, float, float, float, float, float]:
        """
        params
            left_distance: distance left wheel has travelled
            right_distance: distance right wheel has travelled
            timestamp: time of distance readings or None to use current time
        returns
            distance
            velocity
            x is horizontal position of point midway between wheels
            y is vertical position of point midway between wheels
            angle is orientation in radians around point midway between wheels
            x' is the horizontal velocity
            y' is the vertical velocity
            angle' is the angular velocity
            timestamp

        """
        if timestamp is None:
            timestamp = time.time()

        if self.running:
            if 0 == self.timestamp:
                self.timestamp = timestamp
                self.left_distance = left_distance
                self.right_distance = right_distance
                self.velocity=0
                self.pose = Pose2D()
                self.pose_velocity = Pose2D()
                self.timestamp = timestamp
            elif timestamp > self.timestamp:
                #
                # changes from last run
                #
                delta_left_distance = left_distance - self.left_distance
                delta_right_distance = right_distance - self.right_distance
                delta_distance = (delta_left_distance + delta_right_distance) / 2
                delta_angle = (delta_right_distance - delta_left_distance) / self.axle_length
                delta_time = timestamp - self.timestamp

                forward_velocity = delta_distance / delta_time
                angle_velocity = delta_angle / delta_time

                #
                # new position and orientation
                #
                estimated_angle = limit_angle(self.pose.angle + delta_angle / 2)
                x = self.pose.x + delta_distance * math.cos(estimated_angle)
                y = self.pose.y + delta_distance * math.sin(estimated_angle)
                angle = limit_angle(self.pose.angle + delta_angle)

                #
                # new velocities
                #
                self.pose_velocity.x = (x - self.pose.x) / delta_time
                self.pose_velocity.y = (y - self.pose.y) / delta_time
                self.pose_velocity.angle = angle_velocity

                #
                # update pose
                #
                self.pose.x = x
                self.pose.y = y
                self.pose.angle = angle

                #
                # update odometry
                #
                self.left_distance = left_distance
                self.right_distance = right_distance
                self.velocity = forward_velocity

                self.timestamp = timestamp

            return (
                (self.left_distance + self.right_distance) / 2,
                self.velocity,
                self.pose.x, self.pose.y, self.pose.angle,
                self.pose_velocity.x, self.pose_velocity.y, self.pose_velocity.angle,
                self.timestamp
            )

        return 0, 0, 0, 0, 0, 0, 0, 0, self.timestamp

    def shutdown(self):
        self.running = False


class InverseUnicycle:
    """
    Unicycle inverse kinematics that converts forward velocity and 
    angular orientation velocity into invidual linear wheel velocities 
    in a differential drive robot.
    """
    def __init__(self, axle_length:float, wheel_radius:float, min_speed:float, max_speed:float, steering_zero:float=0.01, debug=False):
        self.axle_length:float = axle_length
        self.wheel_radius:float = wheel_radius
        self.min_speed:float = min_speed
        self.max_speed:float = max_speed
        self.steering_zero:float = steering_zero
        self.timestamp = 0
        self.debug = debug

        self.wheel_diameter = 2 * wheel_radius
        self.wheel_circumference = math.pi * self.wheel_diameter

    def run(self, forward_velocity:float, angular_velocity:float, timestamp:float=None) -> Tuple[float, float, float]:
        """
        Convert turning velocity in radians and forward velocity (like meters per second)
        into left and right linear wheel speeds that result in that forward speed
        at that turning angle
        see http://faculty.salina.k-state.edu/tim/robotics_sg/Control/kinematics/unicycle.html#calculating-wheel-velocities

        @parma forward_velocity:float in meters per second
        @param angular_velocity:float in radians per second
        @param timestamp:float epoch seconds or None to use current time
        @return tuple
                - left_wheel_velocity: in meters per second
                - right_wheel_velocity in meters per second
                - timestamp
        """
        if timestamp is None:
            timestamp = time.time()

        left_linear_speed = forward_velocity - angular_velocity * self.axle_length / 2
        right_linear_speed = forward_velocity + angular_velocity * self.axle_length / 2

        self.timestamp = timestamp

        # left/right linear speeds and timestamp
        return left_linear_speed, right_linear_speed, timestamp

    def shutdown(self):
        pass


def unicycle_angular_velocity(wheel_radius:float, axle_length:float, left_velocity:float, right_velocity:float) -> float:
    """
    Calculate angular velocity for the unicycle vehicle.
    For differential drive, calculate angular velocity 
    using the unicycle model and linear wheel velocities. 
    """
    #
    # since angular_velocity = wheel_radius / axle_length * (right_rotational_velocity - left_rotational_velocity)
    # where wheel rotational velocity is in radians per second.
    #
    right_rotational_velocity = wheel_rotational_velocity(wheel_radius, right_velocity)
    left_rotational_velocity = wheel_rotational_velocity(wheel_radius, left_velocity)
    return wheel_radius / axle_length * (right_rotational_velocity - left_rotational_velocity)


def unicycle_max_angular_velocity(wheel_radius:float, axle_length:float, max_forward_velocity:float) -> float:
    """
    Calculate maximum angular velocity for the vehicle, so we can convert between
    normalized and unnormalized forms of the angular velocity.
    For differential drive, calculate maximum angular velocity 
    using the unicycle model and assuming one 
    one wheel is stopped and one wheel is at max velocity.
    """
    #
    # since angular_velocity = wheel_radius / axle_length * (right_rotational_velocity - left_rotational_velocity)
    # where wheel rotational velocity is in radians per second.
    # then if we drive the right wheel at maximum velocity and keep the left wheel stopped
    # we get max_angular_velocity = wheel_radius / axle_length * max_forward_velocity
    #
    return unicycle_angular_velocity(wheel_radius, axle_length, 0, max_forward_velocity)


class UnicycleNormalizeAngularVelocity:
    """
    For a differential drive vehicle, convert an angular velocity in radians per second
    to a value between -1 and 1 inclusive.
    """
    def __init__(self, wheel_radius:float, axle_length:float, max_forward_velocity:float) -> None:
        self.max_angular_velocity = unicycle_max_angular_velocity(wheel_radius, axle_length, max_forward_velocity)

    def run(self, angular_velocity:float) -> float:
        return angular_velocity / self.max_angular_velocity


class UnicycleUnnormalizeAngularVelocity:
    """
    For a differential drive vehicle, convert a normalized angular velocity in range -1 to 1
    into a real angular velocity in radians per second.
    """
    def __init__(self, wheel_radius:float, axle_length:float, max_forward_velocity:float) -> None:
        self.max_angular_velocity = unicycle_max_angular_velocity(wheel_radius, axle_length, max_forward_velocity)

    def run(self, normalized_angular_velocity:float) -> float:
        if abs(normalized_angular_velocity) > 1:
            logger.error("Warning: normalized_angular_velocity must be between -1 and 1")
        return normalized_angular_velocity * self.max_angular_velocity


class NormalizeSteeringAngle:
    """
    Part to convert real steering angle in radians
    to a to a normalize steering value in range -1 to 1
    """
    def __init__(self, max_steering_angle:float, steering_zero:float=0.0) -> None:
        """
        @param max_steering_angle:float measured maximum steering angle in radians
        @param steering_zero:float value at or below which normalized steering values
                                   are considered to be zero.
        """
        self.max_steering_angle = max_steering_angle
        self.steering_zero = steering_zero
    
    def run(self, steering_angle) -> float:
        """
        @param steering angle in radians where
               positive radians is a left turn,
               negative radians is a right turn
        @return a normalized steering value in range -1 to 1, where
               -1 is full left, corresponding to positive max_steering_angle
                1 is full right, corresponding to negative max_steering_angle
        """
        if not is_number_type(steering_angle):
            logger.error("steering angle must be a number.")
            return 0

        steering = steering_angle / self.max_steering_angle
        if abs(steering) <= self.steering_zero:
            return 0
        return -steering # positive steering angle is negative normalized

    def shutdown(self):
        pass


class UnnormalizeSteeringAngle:
    """
    Part to convert normalized steering in range -1 to 1
    to a to real steering angle in radians
    """
    def __init__(self, max_steering_angle:float, steering_zero:float=0.0) -> None:
        """
        @param max_steering_angle:float measured maximum steering angle in radians
        @param steering_zero:float value at or below which normalized steering values
                                   are considered to be zero.
        """
        self.max_steering_angle = max_steering_angle
        self.steering_zero = steering_zero
    
    def run(self, steering) -> float:
        """
        @param a normalized steering value in range -1 to 1, where
               -1 is full left, corresponding to positive max_steering_angle
                1 is full right, corresponding to negative max_steering_angle
        @return steering angle in radians where
                positive radians is a left turn,
                negative radians is a right turn
        """
        if not is_number_type(steering):
            logger.error("steering must be a number")
            return 0

        if steering > 1 or steering < -1:
            logger.warn(f"steering = {steering}, but must be between 1(right) and -1(left)")

        steering = clamp(steering, -1, 1)
        
        s = sign(steering)
        steering = abs(steering)
        if steering <= self.steering_zero:
            return 0.0

        return self.max_steering_angle * steering * -s

    def shutdown(self):
        pass


def wheel_rotational_velocity(wheel_radius:float, speed:float) -> float:
    """
    Convert a forward speed to wheel rotational speed in radians per second.
    Units like wheel_radius in meters and speed in meters per second
    results in radians per second rotational wheel speed.

    @wheel_radius:float radius of wheel in same distance units as speed
    @speed:float speed in distance units compatible with radius
    @return:float wheel's rotational speed in radians per second
    """
    return speed / wheel_radius


def differential_steering(throttle: float, steering: float, steering_zero: float = 0) -> Tuple[float, float]:
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
