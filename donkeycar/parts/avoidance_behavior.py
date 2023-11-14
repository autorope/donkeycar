import numpy as np

class AvoidanceBehaviorPart(object):
    '''
    Keep a list of states, and an active state. Keep track of switching.
    And return active state information.
    '''
    def __init__(self, obstacle_states, lane_options, avoidance_enabled, manual_lane):
        '''
        expects a list of strings to enumerate state
        '''
        # print("bvh states:", states)
        self.obstacle_states = obstacle_states
        self.lane_options_size = len(lane_options)
        self.lane_options = lane_options
        self.lane_behavior_left_index = self.lane_options.index('left')
        self.lane_behavior_right_index = self.lane_options.index('right')
        self.lane_behavior_middle_index = self.lane_options.index('middle')
        self.avoidance_enabled = avoidance_enabled
        self.manual_lane = manual_lane

        if (self.manual_lane):
            from donkeycar.parts.robocars_hat_ctrl import RobocarsHatInCtrl
            self.hatInCtrl = RobocarsHatInCtrl(self.cfg)

    def run(self, detector_obstacle_lane):
        one_hot_bhv_arr = np.zeros(self.lane_options_size)

        if self.avoidance_enabled:
            # get text value from obstacle position
            obstacle_position_text = self.obstacle_states[detector_obstacle_lane]

            # get desired behavior regarding obstacle position
            # search index of desired behavior
            # create one_hot_bhv_arr with desired behavior

            if (self.manual_lane):
                #For test purpose, will follow a lane given from remote controller
                lane=self.hatInCtrl.getSelectedLane()
                if lane==0:
                    one_hot_bhv_arr[self.lane_behavior_left_index] = 1.0
                elif lane==2:
                    one_hot_bhv_arr[self.lane_behavior_right_index] = 1.0
                else:
                    one_hot_bhv_arr[self.lane_behavior_middle_index] = 1.0
            else:
                if obstacle_position_text == "left":
                    one_hot_bhv_arr[self.lane_behavior_right_index] = 1.0
                elif obstacle_position_text == "right":
                    one_hot_bhv_arr[self.lane_behavior_left_index] = 1.0
                elif obstacle_position_text == "middle":
                    one_hot_bhv_arr[self.lane_behavior_middle_index] = 1.0
            # elif obstacle_position_text == "NA":
                # SET TO 0.0 WHEN MODEL CAN HANDLE [0.0,0.0], NO lane seletion = regular driving
                # at the moment default driving is left lane driving
                # one_hot_bhv_arr[self.lane_behavior_left_index] = 1.0

        return one_hot_bhv_arr

    def shutdown(self):
        pass
    
   