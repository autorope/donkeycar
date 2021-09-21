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
        #
        # turn_distance = math.pi
        # unicycle.run(0, turn_distance, 2)
        # self.assertEqual(0, unicycle.left_distance)
        # self.assertEqual(turn_distance, unicycle.right_distance)
        # self.assertEqual(2, unicycle.timestamp)
        # self.assertAlmostEqual(0, unicycle.pose.x, 4)
        # self.assertEqual(-1, unicycle.pose.y)
        # self.assertEqual(math.pi, unicycle.pose.angle)
        # self.assertAlmostEqual(0, unicycle.pose_velocity.x, 4)
        # self.assertEqual(-1, unicycle.pose_velocity.y)
        # self.assertEqual(math.pi, unicycle.pose_velocity.angle)
