import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SteeringThrottleScaler:
    def __init__(self, steering_factor, throttle_factor, steering_on_throttle_factor):
       
        self.steering_factor = steering_factor
        self.throttle_factor = throttle_factor
        self.steering_on_throttle_factor = steering_on_throttle_factor
        
        self.running = True    

    def run(self, steering_angle, throttle):
        scaled_throttle = throttle * self.throttle_factor
        scaled_steering = steering_angle * self.steering_factor * self.steering_on_throttle_factor * self.throttle_factor
        return scaled_steering, scaled_throttle
        
    def shutdown(self):
        self.running = False
        logger.info('Stopping Steering Throttle Scaler')
