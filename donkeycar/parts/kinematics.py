import math
import time
from typing import Tuple

def limit_angle(angle:float):
    """
    limit angle between 0..2pi
    """
    return math.atan2(math.sin(angle), math.cos(angle));

class Pose2D:
    def __init__(self, x:float=0.0, y:float=0.0, angle:float=0.0) -> None:
        self.x = x
        self.y = y
        self.angle = angle


class Unicycle:
    """
    Unicycle kinematics takes the output of the 
    left and right odometers 
    turns those forward distance and velocity,
    pose and pose velocity.
    axle_length: distance between the two drive wheels
    wheel_radius: radius of wheel; must be in same units as axle_length
                  It is assumed that both wheels have the same radius
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


        return (0, 0, 0, 0, 0, 0, 0, 0, self.timestamp)

    def shutdown(self):
        self.running = False

