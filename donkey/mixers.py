import time
import sys
from donkey import actuators

class BaseMixer():

    def update_angle(self, angle):
        print('BaseSteeringActuator.update: angle=%s' %angle)

    def update_throttle(self, throttle):
        print('BaseThrottleActuator.update: throttle=%s' %throttle)

    def update(self, angle=0, throttle=0):
        '''Convenience function to update
        angle and throttle at the same time'''
        self.update_angle(angle)
        self.update_throttle(throttle)


class FrontSteeringMixer(BaseMixer):

    def __init__(self, 
                 steering_actuator=None, 
                 throttle_actuator=None):
        self.steering_actuator = steering_actuator
        self.throttle_actuator = throttle_actuator

    def update_angle(self, angle):
        self.steering_actuator.update(angle)

    def update_throttle(self, throttle):
        self.throttle_actuator.update(throttle)


class DifferentialSteeringMixer(BaseMixer):

    def __init__(self, 
                 left_actuator=None, 
                 right_actuator=None,
                 angle_throttle_multiplier = 1.0):
        self.left_actuator = left_actuator
        self.right_actuator = right_actuator
        self.angle = 0
        self.throttle = 0
        self.angle_throttle_multiplier = angle_throttle_multiplier

    def update_angle(self, angle):
        self.angle = angle
        self.update_actuators()

    def update_throttle(self, throttle):
        self.throttle = throttle
        self.update_actuators()

    def update_actuators(self):
        self.left_actuator.update(self.throttle - self.angle * angle_throttle_multiplier)
        self.right_actuator.update(self.throttle + self.angle * angle_throttle_multiplier)
