import math
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
        R = abs(wheel_base / math.tan(steering_angle))  # Radius of turn
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

        angular_velocity = normalize.run(max_angular_velocity / 2)
        self.assertAlmostEqual(angular_velocity, 0.5, 3)
        angular_velocity = unnormalize.run(angular_velocity)
        self.assertAlmostEqual(angular_velocity, max_angular_velocity / 2, 3)


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

        steering_angle = normalize.run(max_steering_angle / 2)
        self.assertAlmostEqual(steering_angle, 0.5, 3)
        steering_angle = unnormalize.run(steering_angle)
        self.assertAlmostEqual(steering_angle, max_steering_angle / 2, 3)


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
