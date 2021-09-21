import math
import unittest
from donkeycar.parts.kinematics import Unicycle

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
        # turn left 180 degrees, pivoting on left wheel.
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
        # self.assertAlmostEqual(0.5, pose_velocity_x, 2)
        # self.assertAlmostEqual(0.5, pose_velocity_y, 2)
        # self.assertAlmostEqual(math.pi / 2, pose_velocity_angle, 2)

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
        # self.assertAlmostEqual(0.5, pose_velocity_x, 2)
        # self.assertAlmostEqual(0.5, pose_velocity_y, 2)
        # self.assertAlmostEqual(math.pi / 2, pose_velocity_angle, 2)
