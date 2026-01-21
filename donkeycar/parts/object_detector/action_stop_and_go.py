import time
import logging
from donkeycar.parts.object_detector.detector_manager import ActionProtocol

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StopManager():
    # Stop states
    IDLE = 0
    INITIATE = 1
    POS_ONE = 3
    NEG_ONE = 2
    NEG_TWO = 4
    THROTTLE_INC = 0.2

    def __init__(self):
        self.stop_state = self.IDLE
        self.last_throttle = 0.0

    def stop(self):
        if self.stop_state == self.IDLE:
            self.stop_state = self.INITIATE

    def is_idle(self):
        return self.stop_state == self.IDLE

    def throttle(self):
        #         if self.stop_state == self.IDLE:
        #             pass
        throttle = 0.0
        if self.stop_state == self.INITIATE:
            self.stop_state = self.NEG_ONE
            throttle = -1.0
        elif self.stop_state == self.NEG_ONE:
            self.stop_state = self.POS_ONE
            throttle = 0.0
        elif self.stop_state == self.POS_ONE:
            self.stop_state = self.NEG_TWO
            throttle = -1.0
        elif self.stop_state == self.NEG_TWO:
            throttle = self.last_throttle + self.THROTTLE_INC
            if throttle >= 0.0:
                throttle = 0.0
                self.stop_state = self.IDLE
        self.last_throttle = throttle
        return throttle


class ActionStopAndGo(ActionProtocol):
    # Stop and Go protocol States
    RUNNING = 0
    STOPPING = 1
    PAUSING = 2
    PASSING = 3

    def __init__(self, pause_time=2.0, **kwargs):
        super().__init__(**kwargs)
        self.pause = pause_time
        self.state = self.RUNNING
        self.timeout = 0.0
        self.stopper = StopManager()

    def manage(self, angle, throttle, found: bool, position):
        reset_action = False
        logger.debug(f'self.state: {self.state}')
        if self.state == self.RUNNING:
            if found:
                self.state = self.STOPPING
                self.stopper.stop()
            else:
                reset_action = True
        if self.state == self.STOPPING:
            throttle = self.stopper.throttle()
            if self.stopper.is_idle():
                self.state = self.PAUSING
                self.timeout = time.time() + self.pause
        elif self.state == self.PAUSING:
            if time.time() < self.timeout:
                throttle = 0.0
            else:
                self.state = self.PASSING
        elif self.state == self.PASSING:
            if not found:
                self.state = self.RUNNING
                reset_action = True

        return angle, throttle, reset_action
