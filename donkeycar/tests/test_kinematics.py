import math
import time
import unittest

from donkeycar.parts.kinematics import Bicycle, InverseBicycle, InverseUnicycle, bicycle_angular_velocity, limit_angle
from donkeycar.parts.kinematics import BicycleNormalizeAngularVelocity, BicycleUnnormalizeAngularVelocity
from donkeycar.parts.kinematics import Unicycle, unicycle_angular_velocity, unicycle_max_angular_velocity
from donkeycar.parts.kinematics import UnicycleNormalizeAngularVelocity, UnicycleUnnormalizeAngularVelocity
from donkeycar.parts.kinematics import NormalizeSteeringAngle, UnnormalizeSteeringAngle
from donkeycar.parts.kinematics import differential_steering
from donkeycar.utils import sign

#
# python -m unittest donkeycar/tests/test_kinematics.py
#
class TestBicycle(unittest.TestCase):

    def test_forward(self):
        bicycle = Bicycle(1)

        bicycle.run(0, 0, 1)
        self.assertEqual(0, bicycle.forward_distance)
        self.assertEqual(0, bicycle.forward_velocity)
        self.assertEqual(1, bicycle.timestamp)
        self.assertEqual(0, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(0, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(1, 0, 2)
        self.assertEqual(1, bicycle.forward_distance)
        self.assertEqual(1, bicycle.forward_velocity)
        self.assertEqual(2, bicycle.timestamp)
        self.assertEqual(1, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(1, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(10, 0, 3)
        self.assertEqual(10, bicycle.forward_distance)
        self.assertEqual(9, bicycle.forward_velocity)
        self.assertEqual(3, bicycle.timestamp)
        self.assertEqual(10, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(9, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

    def test_reverse(self):
        bicycle = Bicycle(1)

        bicycle.run(0, 0, 1)
        self.assertEqual(0, bicycle.forward_distance)
        self.assertEqual(0, bicycle.forward_velocity)
        self.assertEqual(1, bicycle.timestamp)
        self.assertEqual(0, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(0, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(-1, 0, 2)
        self.assertEqual(-1, bicycle.forward_distance)
        self.assertEqual(-1, bicycle.forward_velocity)
        self.assertEqual(2, bicycle.timestamp)
        self.assertEqual(-1, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(-1, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(-10, 0, 3)
        self.assertEqual(-10, bicycle.forward_distance)
        self.assertEqual(-9, bicycle.forward_velocity)
        self.assertEqual(3, bicycle.timestamp)
        self.assertEqual(-10, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(-9, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

    def test_forward_reverse(self):
        bicycle = Bicycle(1)

        bicycle.run(0, 0, 1)
        self.assertEqual(0, bicycle.forward_distance)
        self.assertEqual(0, bicycle.forward_velocity)
        self.assertEqual(1, bicycle.timestamp)
        self.assertEqual(0, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(0, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(1, 0, 2)
        self.assertEqual(1, bicycle.forward_distance)
        self.assertEqual(1, bicycle.forward_velocity)
        self.assertEqual(2, bicycle.timestamp)
        self.assertEqual(1, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(1, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

        bicycle.run(-1, 0, 3)
        self.assertEqual(-1, bicycle.forward_distance)
        self.assertEqual(-2, bicycle.forward_velocity)
        self.assertEqual(3, bicycle.timestamp)
        self.assertEqual(-1, bicycle.pose.x)
        self.assertEqual(0, bicycle.pose.y)
        self.assertEqual(0, bicycle.pose.angle)
        self.assertEqual(-2, bicycle.pose_velocity.x)
        self.assertEqual(0, bicycle.pose_velocity.y)
        self.assertEqual(0, bicycle.pose_velocity.angle)

    def do_90degree_turn(self, steering_angle):
        turn_direction = sign(steering_angle)
        steering_angle = limit_angle(steering_angle)

        wheel_base = 0.5  
        bicycle = Bicycle(wheel_base)  # wheel base is 1/2 meter


        #
        # turn an 1/4 of circle while wheel is turned 22.5 degrees.
        # do this at 20 hertz, like the vehicle loop
        #
        # calculate length of circle's perimeter
        # see [Rear-axle reference point](https://thef1clan.com/2020/09/21/vehicle-dynamics-the-kinematic-bicycle-model/)
        #
        R = abs(wheel_base / math.sin(steering_angle))  # Radius of turn (radius to Instantaneous Center of Rotation)
        C = 2 * math.pi * R                             # Circumference of turn

        turn_distance = C / 4  # drive the 90 degrees of perimeter
        turn_steps = math.floor(turn_distance * 200)  # 200 odometry readings per meter
        steps_per_second = 20
        time_per_step = 1 / steps_per_second  # 20 odometry readings per second
        print()
        print("X,Y,A")
        for i in range(turn_steps):
            distance, velocity, pose_x, pose_y, pose_angle, pose_velocity_x, pose_velocity_y, pose_velocity_angle, timestamp = bicycle.run(turn_distance * (i+1) / turn_steps, steering_angle, 1 + time_per_step * (i + 1))
            print(pose_x, pose_y, pose_angle, sep=",")
        self.assertAlmostEqual(turn_distance, bicycle.forward_distance, 3)
        self.assertAlmostEqual(1 + turn_steps * time_per_step, bicycle.timestamp, 3)
        self.assertLessEqual((R - pose_x) / R, 0.005)  # final error less than 0.5%
        self.assertLessEqual((turn_direction * R - pose_y) / R, 0.005)  # final error less than 0.5%
        self.assertLessEqual(((turn_direction * math.pi / 2) - pose_angle) / (math.pi / 2), 0.005)


    def test_turn_left(self):
        # 22.5 degrees steering angle
        self.do_90degree_turn(steering_angle = math.pi / 8)

    def test_turn_right(self):
        # 22.5 degrees steering angle
        self.do_90degree_turn(steering_angle = -math.pi / 8)


class TestUnicycle(unittest.TestCase):

    def test_forward(self):
        unicycle = Unicycle(1)

        unicycle.run(0, 0, 1)
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(1, unicycle.timestamp)
        self.assertEqual(0, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(0, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(1, 1, 2)
        self.assertEqual(1, unicycle.left_distance)
        self.assertEqual(1, unicycle.right_distance)
        self.assertEqual(2, unicycle.timestamp)
        self.assertEqual(1, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(1, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(10, 10, 3)
        self.assertEqual(10, unicycle.left_distance)
        self.assertEqual(10, unicycle.right_distance)
        self.assertEqual(3, unicycle.timestamp)
        self.assertEqual(10, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(9, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

    def test_reverse(self):
        unicycle = Unicycle(1)

        unicycle.run(0, 0, 1)
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(1, unicycle.timestamp)
        self.assertEqual(0, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(0, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(-1, -1, 2)
        self.assertEqual(-1, unicycle.left_distance)
        self.assertEqual(-1, unicycle.right_distance)
        self.assertEqual(2, unicycle.timestamp)
        self.assertEqual(-1, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(-1, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(-10, -10, 3)
        self.assertEqual(-10, unicycle.left_distance)
        self.assertEqual(-10, unicycle.right_distance)
        self.assertEqual(3, unicycle.timestamp)
        self.assertEqual(-10, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(-9, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)


    def test_forward_reverse(self):
        unicycle = Unicycle(1)

        unicycle.run(0, 0, 1)
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(1, unicycle.timestamp)
        self.assertEqual(0, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(0, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(1, 1, 2)
        self.assertEqual(1, unicycle.left_distance)
        self.assertEqual(1, unicycle.right_distance)
        self.assertEqual(2, unicycle.timestamp)
        self.assertEqual(1, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(1, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        unicycle.run(-1, -1, 3)
        self.assertEqual(-1, unicycle.left_distance)
        self.assertEqual(-1, unicycle.right_distance)
        self.assertEqual(3, unicycle.timestamp)
        self.assertEqual(-1, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(-2, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

    def test_turn_left(self):
        unicycle = Unicycle(1)

        unicycle.run(0, 0, 1)
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(1, unicycle.timestamp)
        self.assertEqual(0, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(0, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        #
        # turn left 90 degrees, pivoting on left wheel.
        # pivot on a non-moving wheel creates a circle
        # with a radius equal to the axle-length.
        # do this at 20 hertz, like the vehicle loop
        #
        turn_distance = math.pi / 2
        turn_steps = 20
        steps_per_second = 20
        time_per_step = 1 / steps_per_second  # 20 hertz
        for i in range(turn_steps):
            distance, velocity, pose_x, pose_y, pose_angle, pose_velocity_x, pose_velocity_y, pose_velocity_angle, timestamp = unicycle.run(0, turn_distance * (i+1) / turn_steps, 1 + time_per_step * (i + 1))
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(turn_distance, unicycle.right_distance)
        self.assertEqual(1 + turn_steps * time_per_step, unicycle.timestamp)
        self.assertAlmostEqual(0.5, pose_x, 3)
        self.assertAlmostEqual(0.5, pose_y, 3)
        self.assertAlmostEqual(math.pi / 2, pose_angle, 3)

    def test_turn_right(self):
        unicycle = Unicycle(1)

        unicycle.run(0, 0, 1)
        self.assertEqual(0, unicycle.left_distance)
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(1, unicycle.timestamp)
        self.assertEqual(0, unicycle.pose.x)
        self.assertEqual(0, unicycle.pose.y)
        self.assertEqual(0, unicycle.pose.angle)
        self.assertEqual(0, unicycle.pose_velocity.x)
        self.assertEqual(0, unicycle.pose_velocity.y)
        self.assertEqual(0, unicycle.pose_velocity.angle)

        #
        # turn right 180 degrees, pivoting on right wheel.
        # pivot on a non-moving wheel creates a circle
        # with a radius equal to the axle-length.
        # do this at 20 hertz, like the vehicle loop
        #
        turn_distance = math.pi / 2
        turn_steps = 20
        steps_per_second = 20
        time_per_step = 1 / steps_per_second  # 20 hertz
        for i in range(turn_steps):
            distance, velocity, pose_x, pose_y, pose_angle, pose_velocity_x, pose_velocity_y, pose_velocity_angle, timestamp = unicycle.run(turn_distance * (i+1) / turn_steps, 0, 1 + time_per_step * (i + 1))
        self.assertEqual(0, unicycle.right_distance)
        self.assertEqual(turn_distance, unicycle.left_distance)
        self.assertEqual(1 + turn_steps * time_per_step, unicycle.timestamp)
        self.assertAlmostEqual(0.5, pose_x, 3)
        self.assertAlmostEqual(-0.5, pose_y, 3)
        self.assertAlmostEqual(-math.pi / 2, pose_angle, 3)


class TestInverseBicycle(unittest.TestCase):
    def test_inverse_bicycle(self):
        wheel_base = 0.5
        steering_angle = math.pi / 8
        angular_velocity = bicycle_angular_velocity(wheel_base, 1, steering_angle)
        inverse = InverseBicycle(wheel_base)
        forward_velocity, inverse_steering_angle, _ = inverse.run(1, angular_velocity)
        self.assertAlmostEqual(forward_velocity, 1, 3)
        self.assertAlmostEqual(inverse_steering_angle, steering_angle, 3)


class TestInverseUnicycle(unittest.TestCase):
    def test_inverse_unicycle(self):
        axle_length = 0.3
        wheel_radius = 0.01
        angular_velocity = unicycle_angular_velocity(wheel_radius, axle_length, 0.5, 1.5)
        inverse = InverseUnicycle(axle_length, wheel_radius, 0.01, 10, 0)
        left_velocity, right_velocity, _ = inverse.run(1, angular_velocity)
        self.assertAlmostEqual(left_velocity, 0.5, 3)
        self.assertAlmostEqual(right_velocity, 1.5, 3)


class TestBicycleNormalizeAngularVelocity(unittest.TestCase):
    def test_normalize(self):
        wheel_base = 0.5
        max_forward_velocity = 10
        max_steering_angle = math.pi / 6
        max_angular_velocity = bicycle_angular_velocity(wheel_base, max_forward_velocity, max_steering_angle)
        normalize = BicycleNormalizeAngularVelocity(wheel_base, max_forward_velocity, max_steering_angle)        
        unnormalize = BicycleUnnormalizeAngularVelocity(wheel_base, max_forward_velocity, max_steering_angle)

        angular_velocity = normalize.run(max_angular_velocity)
        self.assertAlmostEqual(angular_velocity, 1.0, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, max_angular_velocity, 3)

        angular_velocity = normalize.run(max_angular_velocity / 2)
        self.assertAlmostEqual(angular_velocity, 0.5, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, max_angular_velocity / 2, 3)

        angular_velocity = normalize.run(0)
        self.assertAlmostEqual(angular_velocity, 0, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, 0, 3)

        angular_velocity = normalize.run(-max_angular_velocity / 2)
        self.assertAlmostEqual(angular_velocity, -0.5, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, -max_angular_velocity / 2, 3)

        angular_velocity = normalize.run(-max_angular_velocity)
        self.assertAlmostEqual(angular_velocity, -1.0, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, -max_angular_velocity, 3)


class TestUnicycleNormalizeAngularVelocity(unittest.TestCase):
    def test_normalize(self):
        wheel_radius = 0.01
        axle_length = 0.1
        max_forward_velocity = 10
        max_angular_velocity = unicycle_max_angular_velocity(wheel_radius, axle_length, max_forward_velocity)
        normalize = UnicycleNormalizeAngularVelocity(wheel_radius, axle_length, max_forward_velocity)        
        unnormalize = UnicycleUnnormalizeAngularVelocity(wheel_radius, axle_length, max_forward_velocity)

        angular_velocity = normalize.run(max_angular_velocity / 2)
        self.assertAlmostEqual(angular_velocity, 0.5, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, max_angular_velocity / 2, 3)


class TestNormalizeSteeringAngle(unittest.TestCase):
    def test_normalize(self):
        max_steering_angle = math.pi / 6
        normalize = NormalizeSteeringAngle(max_steering_angle)        
        unnormalize = UnnormalizeSteeringAngle(max_steering_angle)

        #
        # steering(-1) == steering_angle(max_steering_angle)
        #
        steering = normalize.run(max_steering_angle)
        self.assertAlmostEqual(steering, -1.0, 3)
        steering_angle = unnormalize.run(steering)
        self.assertAlmostEqual(steering_angle, max_steering_angle, 3)

        #
        # steering(-0.5) == steering_angle(max_steering_angle/2)
        #
        steering = normalize.run(max_steering_angle / 2)
        self.assertAlmostEqual(steering, -0.5, 3)
        steering_angle = unnormalize.run(steering)
        self.assertAlmostEqual(steering_angle, max_steering_angle / 2, 3)

        #
        # steering(0) == steering_angle(0)
        #
        steering = normalize.run(0)
        self.assertAlmostEqual(steering, 0, 3)
        steering_angle = unnormalize.run(steering)
        self.assertAlmostEqual(steering_angle, 0, 3)

        #
        # steering(0.5) == steering_angle(-max_steering_angle/2)
        #
        steering = normalize.run(-max_steering_angle / 2)
        self.assertAlmostEqual(steering, 0.5, 3)
        steering_angle = unnormalize.run(steering)
        self.assertAlmostEqual(steering_angle, -max_steering_angle / 2, 3)

        #
        # steering(1) == steering_angle(-max_steering_angle)
        #
        steering = normalize.run(-max_steering_angle)
        self.assertAlmostEqual(steering, 1.0, 3)
        steering_angle = unnormalize.run(steering)
        self.assertAlmostEqual(steering_angle, -max_steering_angle, 3)


class TestTwoWheelSteeringThrottle(unittest.TestCase):
    def test_differential_steering(self):
        # Straight within steering_zero tolerance
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.0, 0.0))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.05, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, 0.10, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, -0.05, 0.10))
        self.assertEqual((1.0, 1.0), differential_steering(1.0, -0.10, 0.10))

        # left
        self.assertEqual((0.9, 1.0), differential_steering(1.0, -0.10, 0.0))
        self.assertEqual((0.8, 1.0), differential_steering(1.0, -0.20, 0.0))
        self.assertEqual((0.45, 0.5), differential_steering(0.5, -0.10, 0.0))
        self.assertEqual((0.40, 0.5), differential_steering(0.5, -0.20, 0.0))

        # right
        self.assertEqual((1.0, 0.9), differential_steering(1.0, 0.10, 0.0))
        self.assertEqual((1.0, 0.8), differential_steering(1.0, 0.20, 0.0))
        self.assertEqual((0.5, 0.45), differential_steering(0.5, 0.10, 0.0))
        self.assertEqual((0.5, 0.40), differential_steering(0.5, 0.20, 0.0))

from donkeycar.templates.complete import add_odometry
from donkeycar.vehicle import Vehicle
from donkeycar.parts.kinematics import NormalizeSteeringAngle, limit_angle
import math


def calc_center_of_rotation(wheelbase, front_wheel, orientation, steering_angle):
    """
    Calculate the center of rotation for a bicycle turn.

    Args:
        wheelbase (float): The length of the bicycle wheelbase.
        front_wheel (tuple): The x and y coordinates of the front wheel (x, y).
        orientation (float): The orientation of the bicycle in radians.
        steering_angle (float): The steering angle of the bicycle in radians.

    Returns:
        tuple: The x and y coordinates of the center of rotation
               and the radius of the rotation (x, y, radius) .
               if the steering_angle is zero, the function returns the position
               of the front wheel as the center of rotation and a radius of zero,
               since there is no turn in this case.
    """
    x, y = front_wheel
    if steering_angle == 0:
        return (x, y, 0)
    else:
        R = wheelbase / math.sin(steering_angle)
        cx = x - R * math.sin(orientation)
        cy = y + R * math.cos(orientation)
        return (cx, cy, abs(R))  # radius is always positive


def calc_arc_end_point(center, radius, point, radians):
    """
    Calculates the ending point on a circle given the center of the circle, the radius of the circle,
    a point on the circle and a distance along the circle in radians from the given point.

    Arguments:
    center -- the center of the circle represented as a tuple (x, y) (tuple)
    radius -- the radius of the circle (float)
    point -- a point on the circle represented as a tuple (x, y) (tuple)
    radians -- the distance along the circle in radians from the given point (float)

    Returns:
    end_point -- the ending point on the circle represented as a tuple (x, y) (tuple)
    """
    center_x, center_y = center
    point_x, point_y = point

    theta = math.atan2(point_y - center_y, point_x - center_x)
    theta_end = theta + radians

    x = center_x + radius * math.cos(theta_end)
    y = center_y + radius * math.sin(theta_end)
    end_point = (x, y)
    return end_point


def calc_bicycle_pose(wheelbase, front_wheel, orientation, steering_angle, distance):
    """
    Calculate the ending pose for a bicycle with the given wheel base,
    starting front wheel position, orientation, and steering angle that has
    driven the given distance.
    :param wheelbase:
    :param front_wheel:
    :param orientation:
    :param steering_angle:
    :return: ending pose as tuple of (x, y, orientation)
    """

    if distance == 0:
        return front_wheel.x, front_wheel.y, orientation

    if steering_angle == 0:
        ending_x = front_wheel[0] + distance * math.cos(orientation)
        ending_y = front_wheel[1] + distance * math.sin(orientation)
        ending_angle = orientation
    else:
        # - calculate the center and radius of the turn,
        center_x, center_y, turn_radius = calc_center_of_rotation(wheelbase,
                                                               front_wheel,
                                                               orientation,
                                                               steering_angle)
        print(f"Center of rotation = ({center_x}, {center_y})")
        print(f"Radius of turn = {turn_radius}")

        # - calculate the circumference of a full turn
        turn_circumference = 2 * math.pi * turn_radius

        # - calculate the angular distance travelled in radians
        turn_radians = (distance / turn_circumference) * 2 * math.pi
        turn_radians *= sign(steering_angle)  # right turn is negative angle

        # - calculate the end position on the arc
        ending_x, ending_y = calc_arc_end_point((center_x, center_y),
                                                turn_radius, front_wheel, turn_radians)

        # - calculate the end orientation
        ending_angle = limit_angle(orientation + math.tan(steering_angle) * distance / wheelbase)

    return ending_x, ending_y, ending_angle


def calc_line_length(p1, p2):
    """
    Calculate the length of a line segment given its endpoints.

    Args:
        p1 (tuple): The x and y coordinates of the first endpoint (x1, y1).
        p2 (tuple): The x and y coordinates of the second endpoint (x2, y2).

    Returns:
        float: The length of the line segment.
    """
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


class TestVehicle(unittest.TestCase):

    def initialize_config(self):
        # initialize configurations
        class Config:
            pass

        cfg = Config()
        # cfg.DONKEY_GYM = True
        # cfg.__setattr__('DONKEY_GYM', True)
        # cfg.SIM_RECORD_DISTANCE = True

        cfg.DRIVE_LOOP_HZ = 50

        cfg.DRIVE_TRAIN_TYPE = "mock"
        cfg.AXLE_LENGTH = 0.175  # length of axle; distance between left and right wheels in meters
        cfg.WHEEL_BASE = 0.20  # distance between front and back wheels in meters
        cfg.WHEEL_RADIUS = 0.04  # radius of wheel in meters
        cfg.MAX_STEERING_ANGLE = 25.0 / 360.0 * 3.141592653589793 * 2  # for car-like robot; maximum steering angle in radians (corresponding to tire angle at steering == -1)
        cfg.MIN_SPEED = 0.1  # minimum speed in meters per second; speed below which car stalls
        cfg.MAX_SPEED = 3.0  # maximum speed in meters per second; speed at maximum throttle (1.0)
        cfg.MIN_THROTTLE = 0.1  # throttle (0 to 1.0) that corresponds to MIN_SPEED, throttle below which car stalls
        cfg.HAVE_ODOM = True
        cfg.HAVE_ODOM_2 = False
        cfg.ENCODER_PPR = 600
        cfg.MM_PER_TICK = (
                                      cfg.WHEEL_RADIUS * 2 * 3.141592653589793) / cfg.ENCODER_PPR * 1000  # How much travel with a single encoder tick, in mm. Roll you car a meter and divide total ticks measured by 1,000
        cfg.ODOM_SMOOTHING = 1  # number of odometer readings to use when calculating velocity
        cfg.ODOM_DEBUG = False  # Write out values on vel and distance as it runs
        cfg.ENCODER_TYPE = "MOCK"
        cfg.TACHOMETER_MODE = 1  # FORWARD_ONLY

        cfg.ENCODER_TYPE = "MOCK"
        cfg.MOCK_TICKS_PER_SECOND = cfg.ENCODER_PPR * 10

        return cfg

    def initialize_vehicle(self, cfg):
        # Initialize vehicle pipeline
        v = Vehicle()
        add_odometry(v, cfg, threaded=False)
        return v

    def do_drive(self, cfg, forward_velocity, steering_angle):
        steering_angle = limit_angle(steering_angle)
        turn_direction = sign(steering_angle)

        wheel_base = cfg.WHEEL_BASE


        #
        # turn an 1/4 of circle while wheel is turned 12.5 degrees.
        # do this at 20 hertz, like the vehicle loop
        #
        # calculate length of circle's perimeter
        # see [Rear-axle reference point](https://thef1clan.com/2020/09/21/vehicle-dynamics-the-kinematic-bicycle-model/)
        #
        turn_distance = None
        if steering_angle != 0.0:
            R = wheel_base / math.sin(steering_angle)  # Radius of turn (radius to Instantaneous Center of Rotation)
            C = 2 * math.pi * R                        # Circumference of turn
            turn_distance = abs(C / 4)  # drive the 90 degrees of perimeter
        else:
            # going straight
            turn_distance = forward_velocity * 2 # just use 2 seconds of driving

        #
        # calculate a ticks_per_second value for the mock encoder
        #
        turn_seconds = turn_distance / forward_velocity
        steps_per_second = cfg.DRIVE_LOOP_HZ
        turn_steps = steps_per_second * turn_seconds

        meters_per_revolution = cfg.WHEEL_RADIUS * 2 * math.pi
        turn_revolutions = turn_distance / meters_per_revolution
        turn_ticks = turn_revolutions * cfg.ENCODER_PPR
        ticks_per_second = turn_ticks / turn_seconds

        #
        # set turns-per-tick for mock encoder into configuration
        #
        cfg.MOCK_TICKS_PER_SECOND = ticks_per_second

        # set throttle and steering angle
        throttle = 1.0  # full throttle, so we can use the cfg.MOCK_TICKS_PER_SECOND as the encoder rate
        normalize_steering = NormalizeSteeringAngle(max_steering_angle=cfg.MAX_STEERING_ANGLE)
        steering = normalize_steering.run(steering_angle)

        # run the vehicle and then stop it
        vehicle = self.initialize_vehicle(cfg)
        vehicle.mem.put(['throttle', 'steering'], [throttle, steering])

        # run the vehicle loop and get how long it took
        loop_count, loop_seconds = vehicle.start(rate_hz=steps_per_second, max_loop_count=int(turn_steps), verbose=True)

        # read the final values from vehicle memory
        distance, velocity, pose_x, pose_y, pose_angle = vehicle.mem.get(['enc/distance', 'enc/velocity', 'pos/x', 'pos/y', 'pos/angle', ])

        #
        # use the actual loop time to determine the expected distance
        #
        loop_ticks = ticks_per_second * loop_seconds
        loop_distance = loop_ticks / cfg.ENCODER_PPR * meters_per_revolution
        self.assertAlmostEqual(loop_distance, distance, 2)
        self.assertLessEqual(abs(loop_distance - distance) / distance, 0.005)  # final error less than 0.5%

        #
        # calculate the expected ending position using the center of the turn,
        # the radius of the turn, the circumference of the turn
        # and the distance travelled to get the point on the turn where
        # the vehicle ends up
        #
        ending_x, ending_y, ending_angle = calc_bicycle_pose(cfg.WHEEL_BASE, (0, 0), 0, steering_angle, distance)

        print(f"Expected Distance = {loop_distance}")
        print(f"Calculated Pose = ({pose_x}, {pose_y}, {pose_angle})")
        print(f"Expected ending Pose = ({ending_x}, {ending_y}, {ending_angle})")

        if steering_angle != 0.0:
            self.assertLessEqual(abs((ending_x - pose_x) / loop_distance), 0.005)  # final error less than 0.5%
            self.assertLessEqual(abs((ending_y - pose_y) / loop_distance), 0.005)  # final error less than 0.5%
            self.assertLessEqual(abs((ending_angle - pose_angle) / (2 * math.pi)), 0.04)  # final error less than 4%

    def test_drive_straight(self):
        # 12.5 degrees steering angle
        cfg = self.initialize_config()
        self.do_drive(cfg, forward_velocity=cfg.MAX_SPEED / 2, steering_angle = 0.0)

    def test_turn_left(self):
        # 12.5 degrees steering angle
        cfg = self.initialize_config()
        self.do_drive(cfg, forward_velocity=cfg.MAX_SPEED / 2, steering_angle =cfg.MAX_STEERING_ANGLE / 2)

    def test_turn_right(self):
        # -12.5 degrees steering angle
        cfg = self.initialize_config()
        self.do_drive(cfg, forward_velocity=cfg.MAX_SPEED / 2, steering_angle =-cfg.MAX_STEERING_ANGLE / 2)
