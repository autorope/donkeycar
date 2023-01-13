import unittest
import numpy as np
from donkeycar.parts.depth_avoidance import DepthAvoidance

class TestUser(unittest.TestCase):

    def test_emergency_brake_init(self):
        '''
        Test that the emergency_brake attribute 
        is initialized to False
        '''
        depth_avoidance = DepthAvoidance()
        self.assertFalse(depth_avoidance.emergency_brake)

    def test_emergency_brake_set(self):
        '''
        Test that the detect_obstacle method 
        sets the emergency_brake attribute to True 
        when obstacles are detected in both PCLC and PCRC
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_frame[250:300,220:320] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_frame[250:300,320:420] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_avoidance.detect_obstacle_full_frame(0, 0, depth_frame)
        self.assertTrue(depth_avoidance.emergency_brake)

    def test_steering_angle_set(self):
        '''
        Test that the detect_obstacle method 
        sets the steering_angle attribute to the correct value 
        when obstacles are detected in PCLL
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_frame[250:300,120:220] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_avoidance.detect_obstacle_full_frame(0, 0, depth_frame)
        self.assertEqual(depth_avoidance.steering_angle, depth_avoidance.THREE_QUARTER_RIGHT_STEERING)

    def test_steering_angle_unchanged(self):
        '''
        Test that the detect_obstacle method 
        does not change the steering_angle attribute 
        when no obstacles are detected
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_avoidance.detect_obstacle_full_frame(0,0, depth_frame)
        self.assertEqual(depth_avoidance.steering_angle, 0)

    def test_clamp(self):
        '''
        Test that the clamp method correctly 
        clamps a value within the given range
        '''
        depth_avoidance = DepthAvoidance()
        self.assertEqual(depth_avoidance.clamp(10, 0, 5), 5)
        self.assertEqual(depth_avoidance.clamp(-10, -5, 5), -5)
        self.assertEqual(depth_avoidance.clamp(3, 0, 5), 3)

class TestAvoidanceOnCroppedFrame(unittest.TestCase):

    def test_emergency_brake_init(self):
        '''
        Test that the emergency_brake attribute 
        is initialized to False
        '''
        depth_avoidance = DepthAvoidance()
        self.assertFalse(depth_avoidance.emergency_brake)

    def test_emergency_brake_set(self):
        '''
        Test that the detect_obstacle method 
        sets the emergency_brake attribute to True 
        when obstacles are detected in both PCLC and PCRC
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((100, 400)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_frame[50:100,100:200] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_frame[50:100,200:300] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_avoidance.detect_obstacle_cropped_frame(0, 0, depth_frame)
        self.assertTrue(depth_avoidance.emergency_brake)

    def test_steering_angle_set_when_object_in_PCLL(self):
        '''
        Test that the detect_obstacle method 
        sets the steering_angle attribute to the correct value 
        when obstacles are detected in PCLL
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((100, 400)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_frame[50:100,0:100] = depth_avoidance.CLOSE_DISTANCE_MM - 1
        depth_avoidance.detect_obstacle_cropped_frame(0, 0, depth_frame)
        self.assertEqual(depth_avoidance.steering_angle, depth_avoidance.THREE_QUARTER_RIGHT_STEERING)

    def test_steering_angle_set_when_object_in_PFRR(self):
        '''
        Test that the detect_obstacle method 
        sets the steering_angle attribute to the correct value 
        when obstacles are detected in PFRR
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((100, 400)) * depth_avoidance.FAR_DISTANCE_MM
        depth_frame[0:50,300:400] = depth_avoidance.FAR_DISTANCE_MM - 1
        depth_avoidance.detect_obstacle_cropped_frame(0, 0, depth_frame)
        self.assertEqual(depth_avoidance.steering_angle, depth_avoidance.QUARTER_LEFT_STEERING)
        
    def test_steering_angle_unchanged(self):
        '''
        Test that the detect_obstacle method 
        does not change the steering_angle attribute 
        when no obstacles are detected
        '''
        depth_avoidance = DepthAvoidance()
        depth_frame = np.ones((100, 400)) * depth_avoidance.CLOSE_DISTANCE_MM
        depth_avoidance.detect_obstacle_cropped_frame(0,0, depth_frame)
        self.assertEqual(depth_avoidance.steering_angle, 0)

    def test_clamp(self):
        '''
        Test that the clamp method correctly 
        clamps a value within the given range
        '''
        depth_avoidance = DepthAvoidance()
        self.assertEqual(depth_avoidance.clamp(10, 0, 5), 5)
        self.assertEqual(depth_avoidance.clamp(-10, -5, 5), -5)
        self.assertEqual(depth_avoidance.clamp(3, 0, 5), 3)


if __name__ == '__main__':
    unittest.main()