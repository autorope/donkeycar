import logging
import donkeycar as dk

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SteeringThrottleScaler:
    def __init__(self, cfg):
        self.steering_factor = cfg.STEERING_FACTOR
        self.throttle_factor = cfg.THROTTLE_FACTOR
        self.steering_on_throttle_factor = cfg.STEERING_ON_THROTTLE_FACTOR
        self.min_throttle = cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE_MIN
        self.max_throttle = cfg.ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE_MAX
        self.adaptative_steering_scaler = cfg.ADAPTATIVE_STEERING_SCALER_ON_THROTTLE
        self.running = True    

    def run(self, steering_angle, throttle):
        scaled_steering = steering_angle
        scaled_throttle = throttle
        if steering_angle and throttle:
            scaled_throttle = throttle * self.throttle_factor
            if self.adaptative_steering_scaler:
                dyn_steering_factor = dk.utils.map_range_float(throttle, self.min_throttle, self.max_throttle, 1.0, self.steering_on_throttle_factor)
                scaled_steering = max(min(steering_angle * dyn_steering_factor,1.0),-1.0)
            else:
                scaled_steering = max(min(steering_angle * self.steering_factor * self.steering_on_throttle_factor * self.throttle_factor,1.0),-1.0)
        return scaled_steering, scaled_throttle
        
    def shutdown(self):
        self.running = False
        logger.info('Stopping Steering Throttle Scaler')
