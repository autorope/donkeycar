import time
import logging
from donkeycar.parts.object_detector.detector_manager import ActionProtocol

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


ACTION_DEMO_TRIGGER_TIMES = 10

class ActionDemo(ActionProtocol):
  def __init__(self, **kwargs):
      self.__run_trigger = 0
      super().__init__(**kwargs)

  def manage(self, angle, throttle, found: bool, position):    
      reset_action = False  
      self.__run_trigger += 1
      if not found or self.__run_trigger >= ACTION_DEMO_TRIGGER_TIMES:
          self.__run_trigger = 0
          reset_action = True
      return angle, throttle, reset_action
