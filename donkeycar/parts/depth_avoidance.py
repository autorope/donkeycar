import logging
import cv2
from typing import Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DepthAvoidance:
    '''
    Depth Map Avoidance

    RIGHT is Positive steering
    LEFT is Negative steering
    '''

    FULL_RIGHT_STEERING = -0.9
    THREE_QUARTER_RIGHT_STEERING = -0.75
    HALF_RIGHT_STEERING = -0.5
    QUARTER_RIGHT_STEERING = -0.25

    FULL_LEFT_STEERING = 0.9
    THREE_QUARTER_LEFT_STEERING = 0.75
    HALF_LEFT_STEERING = 0.5
    QUARTER_LEFT_STEERING = 0.25

    CLOSE_DISTANCE_MM = 1000
    FAR_DISTANCE_MM = 2000

    NB_PIXELS_IN_RANGE = 1500 # 3000
    
    def __init__(self):
        
        self.emergency_brake = False
        self.throttle = 0
        self.steering_angle = 0

        self.obstacle_distances = None

        self.clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

        self.running = True

    def detect_obstacle_full_frame(self, steering_angle, throttle, depth_frame):
        '''
                                                     H400 x W640
        |-----------------------------------------------------------------------------------------------------|
        |             |                                                                       |               |
        |             |                          (UNUSED) 0:200,0:640                         |               |
        |             |                                                                       |               |
        |             |-----------------------------------------------------------------------|               |
        |    UNUSED   | 200:250,120:220 | 200:250,220:320 | 200:250,320:420 | 200:250,420:520 |   UNUSED      |
        | 0:400,0:120 | 250:300,120:220 | 250:300,220:320 | 250:300,320:420 | 250:300,420:520 | 0:400,520,640 |
        |             |-----------------------------------------------------------------------|               |
        |             |                          (UNUSED) 300:400,0:640                       |               |
        |-----------------------------------------------------------------------------------------------------|

                      |      PFLL       |      PFLC       |      PFRC       |      PFRR       |
                      |      PCLL       |      PCLC       |      PCRC       |      PCRR       |
        '''
        self.emergency_brake = False
        self.throttle = throttle
        obstacle_detected_in_PCLC = ((depth_frame[250:300,220:320] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        obstacle_detected_in_PCRC = ((depth_frame[250:300,320:420] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        
        if obstacle_detected_in_PCLC or obstacle_detected_in_PCRC:
            self.emergency_brake = obstacle_detected_in_PCLC & obstacle_detected_in_PCRC
            self.steering_angle += self.clamp(obstacle_detected_in_PCLC * self.FULL_RIGHT_STEERING,-1,1)
            self.steering_angle += self.clamp(obstacle_detected_in_PCRC * self.FULL_LEFT_STEERING,-1,1)
        else:    
            obstacle_detected_in_PCLL = ((depth_frame[250:300,120:220] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PCLL * self.THREE_QUARTER_RIGHT_STEERING,-1,1)
            
            obstacle_detected_in_PCRR = ((depth_frame[250:300,420:520] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PCRR * self.THREE_QUARTER_LEFT_STEERING,-1,1)
            
            obstacle_detected_in_PFLC = ((depth_frame[200:250,220:320] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PFLC * self.HALF_RIGHT_STEERING,-1,1)
            
            obstacle_detected_in_PFRC = ((depth_frame[200:250,320:420] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PFRC * self.HALF_LEFT_STEERING,-1,1)
            
            obstacle_detected_in_PFLL = ((depth_frame[200:250,120:220] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PFLL * self.QUARTER_RIGHT_STEERING,-1,1)
            
            obstacle_detected_in_PFRR = ((depth_frame[200:250,420:520] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += self.clamp(obstacle_detected_in_PFRR * self.QUARTER_LEFT_STEERING,-1,1)

        if self.steering_angle == 0:
            self.steering_angle = steering_angle
        
        if self.emergency_brake:
            self.throttle = -1
        
        logger.debug("steering_angle = {} ; emergency_brake = {}".format(self.steering_angle, self.throttle))

    def detect_obstacle_cropped_frame(self, steering_angle, throttle, depth_frame):
        '''
                                                     H400 x W640
        |-----------------------------------------------------------------------------------------------------|
        |             |                                                                       |               |
        |             |                          (UNUSED) 0:200,0:640                         |               |
        |             |                                                                       |               |
        |             |-----------------------------------------------------------------------|               |
        |    UNUSED   | 200:250,120:220 | 200:250,220:320 | 200:250,320:420 | 200:250,420:520 |   UNUSED      |
        | 0:400,0:120 | 250:300,120:220 | 250:300,220:320 | 250:300,320:420 | 250:300,420:520 | 0:400,520,640 |
        |             |-----------------------------------------------------------------------|               |
        |             |                          (UNUSED) 300:400,0:640                       |               |
        |-----------------------------------------------------------------------------------------------------|

                      
        '''
        '''
                               CROPPED H100 x W400
        |-----------------------------------------------------------------------|
        |    0:50,0:100   |    0:50,100:200 |    0:50,200:300 |    0:50,300:400 |
        |  50:100,0:100   |  50:100,100:200 |  50:100,200:300 |  50:100,300:400 |
        |-----------------------------------------------------------------------|
        |      PFLL       |      PFLC       |      PFRC       |      PFRR       |
        |      PCLL       |      PCLC       |      PCRC       |      PCRR       |

        '''


        self.emergency_brake = False
        self.throttle = throttle
        self.steering_angle = 0

        # obstacle_detected_in_PCLC = ((depth_frame[50:100,100:200] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        # obstacle_detected_in_PCRC = ((depth_frame[50:100,200:300] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        obstacle_detected_in_PCLC = ((depth_frame[75:100,100:200] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        obstacle_detected_in_PCRC = ((depth_frame[75:100,200:300] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        
        if obstacle_detected_in_PCLC or obstacle_detected_in_PCRC:
            self.emergency_brake = obstacle_detected_in_PCLC & obstacle_detected_in_PCRC
            self.steering_angle += obstacle_detected_in_PCLC * self.FULL_RIGHT_STEERING
            self.steering_angle += obstacle_detected_in_PCRC * self.FULL_LEFT_STEERING
        else:    
            # obstacle_detected_in_PCLL = ((depth_frame[50:100,0:100] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            obstacle_detected_in_PCLL = ((depth_frame[75:100,0:100] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += obstacle_detected_in_PCLL * self.THREE_QUARTER_RIGHT_STEERING
            
            # obstacle_detected_in_PCRR = ((depth_frame[50:100,300:400] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            obstacle_detected_in_PCRR = ((depth_frame[75:100,300:400] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            self.steering_angle += obstacle_detected_in_PCRR * self.THREE_QUARTER_LEFT_STEERING
            
            # obstacle_detected_in_PFLC = ((depth_frame[0:50,100:200] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFLC * self.HALF_RIGHT_STEERING
            
            # obstacle_detected_in_PFRC = ((depth_frame[0:50,200:300] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFRC * self.HALF_LEFT_STEERING
            
            # obstacle_detected_in_PFLL = ((depth_frame[0:50,0:100] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFLL * self.QUARTER_RIGHT_STEERING
            
            # obstacle_detected_in_PFRR = ((depth_frame[0:50,300:400] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFRR * self.QUARTER_LEFT_STEERING

        self.steering_angle = self.clamp(self.steering_angle, -1, 1)
        if self.steering_angle == 0:
            self.steering_angle = steering_angle
        
        if self.emergency_brake:
            self.throttle = 0 # -1
        
        logger.debug("steering_angle = {} ; emergency_brake = {}".format(self.steering_angle, self.throttle))
   
    def detect_obstacle_from_distance(self, steering_angle, throttle, obstacle_distances):
        '''
                                                     H400 x W640
        |-----------------------------------------------------------------------------------------------------|
        |             |                                                                       |               |
        |             |                          (UNUSED) 0:200,0:640                         |               |
        |             |                                                                       |               |
        |             |-----------------------------------------------------------------------|               |
        |    UNUSED   | 200:250,120:220 | 200:250,220:320 | 200:250,320:420 | 200:250,420:520 |   UNUSED      |
        | 0:400,0:120 | 250:300,120:220 | 250:300,220:320 | 250:300,320:420 | 250:300,420:520 | 0:400,520,640 |
        |             |-----------------------------------------------------------------------|               |
        |             |                          (UNUSED) 300:400,0:640                       |               |
        |-----------------------------------------------------------------------------------------------------|

                      
        '''
        '''
                               CROPPED H100 x W400
        |-----------------------------------------------------------------------|
        |    0:50,0:100   |    0:50,100:200 |    0:50,200:300 |    0:50,300:400 |
        |  50:100,0:100   |  50:100,100:200 |  50:100,200:300 |  50:100,300:400 |
        |-----------------------------------------------------------------------|
        |      PFLL       |      PFLC       |      PFRC       |      PFRR       |
        |      PCLL       |      PCLC       |      PCRC       |      PCRR       |

        '''
        self.obstacle_distances = obstacle_distances
        
        PCLL_dist = self.obstacle_distances[0,6]
        PCLC_dist = self.obstacle_distances[1,6]
        PCRC_dist = self.obstacle_distances[2,6]
        PCRR_dist = self.obstacle_distances[3,6]
        


        self.emergency_brake = False
        self.throttle = throttle
        self.steering_angle = 0

        # obstacle_detected_in_PCLC = ((depth_frame[50:100,100:200] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        # obstacle_detected_in_PCRC = ((depth_frame[50:100,200:300] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
        obstacle_detected_in_PCLC = (PCLC_dist < self.CLOSE_DISTANCE_MM)
        obstacle_detected_in_PCRC = (PCRC_dist < self.CLOSE_DISTANCE_MM)
        
        if obstacle_detected_in_PCLC or obstacle_detected_in_PCRC:
            self.emergency_brake = obstacle_detected_in_PCLC & obstacle_detected_in_PCRC
            self.steering_angle += obstacle_detected_in_PCLC * self.FULL_RIGHT_STEERING
            self.steering_angle += obstacle_detected_in_PCRC * self.FULL_LEFT_STEERING
        else:    
            # obstacle_detected_in_PCLL = ((depth_frame[50:100,0:100] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            obstacle_detected_in_PCLL = (PCLL_dist < self.CLOSE_DISTANCE_MM)
            self.steering_angle += obstacle_detected_in_PCLL * self.THREE_QUARTER_RIGHT_STEERING
            
            # obstacle_detected_in_PCRR = ((depth_frame[50:100,300:400] < self.CLOSE_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            obstacle_detected_in_PCRR = (PCRR_dist < self.CLOSE_DISTANCE_MM)
            self.steering_angle += obstacle_detected_in_PCRR * self.THREE_QUARTER_LEFT_STEERING
            
            # obstacle_detected_in_PFLC = ((depth_frame[0:50,100:200] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFLC * self.HALF_RIGHT_STEERING
            
            # obstacle_detected_in_PFRC = ((depth_frame[0:50,200:300] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFRC * self.HALF_LEFT_STEERING
            
            # obstacle_detected_in_PFLL = ((depth_frame[0:50,0:100] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFLL * self.QUARTER_RIGHT_STEERING
            
            # obstacle_detected_in_PFRR = ((depth_frame[0:50,300:400] < self.FAR_DISTANCE_MM).sum() > self.NB_PIXELS_IN_RANGE)
            # self.steering_angle += obstacle_detected_in_PFRR * self.QUARTER_LEFT_STEERING

        self.steering_angle = self.clamp(self.steering_angle, -0.9, 0.9)
        if self.steering_angle == 0:
            self.steering_angle = steering_angle
        
        if self.emergency_brake:
            self.throttle = 0 # -1
        
        logger.debug("steering_angle = {} ; emergency_brake = {}".format(self.steering_angle, self.throttle))
   
    def run(self, steering_angle, throttle, obstacle_distances):
        # H100 W400 np.uint16
        # , depth_image_arr: Tuple[int, ...] = (100, 400)
        #self.detect_obstacle_cropped_frame(steering_angle, throttle, depth_frame)
        self.detect_obstacle_from_distance(steering_angle, throttle, obstacle_distances)
        return self.steering_angle, self.throttle
    
    def shutdown(self):
        self.running = False
        logger.info('Stopping Depth Map Avoidance')