import unittest
import numpy as np
from donkeycar.parts.oak_d_camera import OakDCamera

class TestOakDCamera(unittest.TestCase):

    def test_RGB_camera_only_shape(self):
        '''
        Test if the returned RGB image shape is right
        '''
        oak_D_Camera = OakDCamera(width=240, height=135, depth=3, isp_scale=(1,8), framerate=35, enable_depth= False)
        oak_D_Camera.run()
        self.assertEqual((3, 135, 240),oak_D_Camera.frame_xout.shape)
        
    def test_RGB_camera_and_depth_camera_shape(self):
        '''
        Test if the returned RGB image shape
        and depth image shape are right
        '''
        oak_D_Camera = OakDCamera(width=240, height=135, depth=3, isp_scale=(1,8), framerate=35, enable_depth= True)
        oak_D_Camera.run()
        self.assertEqual((135, 240, 3),oak_D_Camera.frame_xout.shape)
        self.assertEqual((100, 400),oak_D_Camera.frame_xout_depth.shape)
        
    

    # def test_emergency_brake_set(self):
    #     '''
    #     Test that the detect_obstacle method 
    #     sets the emergency_brake attribute to True 
    #     when obstacles are detected in both PCLC and PCRC
    #     '''
    #     depth_avoidance = DepthAvoidance()
    #     depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
    #     depth_frame[250:300,220:320] = depth_avoidance.CLOSE_DISTANCE_MM - 1
    #     depth_frame[250:300,320:420] = depth_avoidance.CLOSE_DISTANCE_MM - 1
    #     depth_avoidance.detect_obstacle_full_frame(0, 0, depth_frame)
    #     self.assertTrue(depth_avoidance.emergency_brake)

    # def test_steering_angle_set(self):
    #     '''
    #     Test that the detect_obstacle method 
    #     sets the steering_angle attribute to the correct value 
    #     when obstacles are detected in PCLL
    #     '''
    #     depth_avoidance = DepthAvoidance()
    #     depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
    #     depth_frame[250:300,120:220] = depth_avoidance.CLOSE_DISTANCE_MM - 1
    #     depth_avoidance.detect_obstacle_full_frame(0, 0, depth_frame)
    #     self.assertEqual(depth_avoidance.steering_angle, depth_avoidance.THREE_QUARTER_RIGHT_STEERING)

    # def test_steering_angle_unchanged(self):
    #     '''
    #     Test that the detect_obstacle method 
    #     does not change the steering_angle attribute 
    #     when no obstacles are detected
    #     '''
    #     depth_avoidance = DepthAvoidance()
    #     depth_frame = np.ones((400, 640)) * depth_avoidance.CLOSE_DISTANCE_MM
    #     depth_avoidance.detect_obstacle_full_frame(0,0, depth_frame)
    #     self.assertEqual(depth_avoidance.steering_angle, 0)

    # def test_clamp(self):
    #     '''
    #     Test that the clamp method correctly 
    #     clamps a value within the given range
    #     '''
    #     depth_avoidance = DepthAvoidance()
    #     self.assertEqual(depth_avoidance.clamp(10, 0, 5), 5)
    #     self.assertEqual(depth_avoidance.clamp(-10, -5, 5), -5)
    #     self.assertEqual(depth_avoidance.clamp(3, 0, 5), 3)



if __name__ == '__main__':
    unittest.main()