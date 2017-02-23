import time
import sys
import math
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
        self.steering_actuator.update_angle(angle)

    def update_throttle(self, throttle):
        self.throttle_actuator.update_throttle(throttle)


class DifferentialSteeringMixer(BaseMixer):

    def __init__(self, 
                 left_actuator=None, 
                 right_actuator=None,
                 angle_throttle_multiplier = 1.0/math.pi):
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


class MecanumMixer(DifferentialSteeringMixer):

    def __init__(self, 
                 lf_actuator=None, 
                 rf_actuator=None,
                 lr_actuator=None, 
                 rr_actuator=None,
                 angle_throttle_multiplier = 1.0/math.pi):
        self.lf_actuator = lf_actuator
        self.rf_actuator = rf_actuator
        self.lr_actuator = lr_actuator
        self.rr_actuator = rr_actuator
        self.angle = 0
        self.throttle = 0
        self.angle_throttle_multiplier = angle_throttle_multiplier

    def update_actuators(self):
        self.lf_actuator.update(self.throttle - self.angle * angle_throttle_multiplier)
        self.rf_actuator.update(self.throttle + self.angle * angle_throttle_multiplier)
        self.lr_actuator.update(self.throttle - self.angle * angle_throttle_multiplier)
        self.rr_actuator.update(self.throttle + self.angle * angle_throttle_multiplier)
        