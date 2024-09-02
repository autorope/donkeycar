"""
detector_manager.py
Donkeycar Parts to manage a sequence of events based upon object detection 

    DetectorManager is a Donkeycar part that manages the object detection and the actions.

    ActionProtocol is a base class for the actions that can be managed by the DetectorManager.
      * action_demo.py: An example that shows how to create an action.
      * action_pass_object.py: Pass the target object if it is detected.

    Mediapipe_Object_Detector: detects objects in the image using the mediapipe object detection model.

How to use: 
  1. Download the object detection model to the Car directory
     https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite

  2. configure myconfig.py
    2.1 Set OBJECT_DETECTOR = True to enable object detection.
    2.2 OD_ACTION_DEMO = True, which allows recognition of OD_ACTION_DEMO_LABEL, default value is person.
    2.3 OD_ACTION_STOP_AND_GO = True to enable the stop sign feature.
"""

import time
import logging
from donkeycar.parts.object_detector.mediapipe_object_detetor import MediapipeObjectDetector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
        
MARK_TEXT_MARGIN = 10  # pixels
MARK_TEXT_ROW_SIZE = 30
MARK_TEXT_SIZE = 1
MARK_TEXT_THICKNESS = 1
MARK_TEXT_COLOR = (0, 255, 0)

class ActionProtocol:
    def __init__(self, od_label: str):
      self.od_label = od_label

    def manage(self, angle, throttle, found: bool, position):
      reset_action = True
      return angle, throttle, reset_action

class DetectorManager:

    def __init__(self,
                 od_model_path,
                 score=0.5,
                 image_width=160,
                 run_hz=1,  # 1 per second
                 vehicle_hz=20,
                 show_bounding_box = True):

        self.on = True
        self.width = image_width
        self.img_center = self.width / 2

        self.running_action = None

        self.run_counter = 0
        self.run_trigger = int(vehicle_hz / run_hz)
        self.run_inprogress = False
        
        self.show_bounding_box  = show_bounding_box

        self.image = None
        self.bbox = None
        self.score = 0
        self.label = None
        self.position = 0.0

        self.__actions = {}
        self._od_labels =[]

        self.detector = MediapipeObjectDetector(
            od_model_path=od_model_path,
            max_results=3,
            score_threshold=score)

    def run(self, angle, throttle, image):
        self.run_counter += 1
        start = time.time()
        if self.run_counter >= self.run_trigger:
            logger.debug(f'self.run_counter: {self.run_counter}')
            self.image = image
            self._detect()
            if self.show_bounding_box and self.bbox is not None:
                self._mark(self.image, self.bbox, self.label)

            angle, throttle = self._dispatch_action(self.label,angle, throttle)
            logger.debug(f'run_time_cost:{(time.time() - start):5.3f}')
        return angle, throttle, image

    def shutdown(self):
        logger.info(
            f'Detector - average detection time {self.detector.average_perf():5.3f}')
        self.on = False

    def addAction(self,action: ActionProtocol):
         logger.info(f'addAction label:{action.od_label}')
         self._od_labels.append(action.od_label)
         self.__actions[action.od_label] = action

    def _mark(self, image, bbox, label):
        import cv2
        # top left corner of rectangle
        start_point = (bbox.origin_x, bbox.origin_y)
        # bottom right corner of rectangle
        end_point = (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height)
        color = (255, 0, 0)  # Red color
        thickness = 1
        image = cv2.rectangle(image, start_point, end_point, color, thickness)

        text_location = (MARK_TEXT_MARGIN + bbox.origin_x,
                        MARK_TEXT_MARGIN + MARK_TEXT_ROW_SIZE + bbox.origin_y)
        cv2.putText(image, label, text_location, cv2.FONT_HERSHEY_DUPLEX,
                    MARK_TEXT_SIZE, MARK_TEXT_COLOR, MARK_TEXT_THICKNESS, cv2.LINE_AA)

    def _detect(self):
        self.bbox = None
        self.score = 0
        self.label = None
        self.position = 0.0
        if self.image is not None:
            results = self.detector.detect(self.image)
            for label, bbox, score in results:
                if label in self._od_labels:
                    self.bbox = bbox
                    self.score = score
                    self.label = label
                    self.position = ((self.bbox.origin_x + (self.bbox.width / 2)) - self.img_center) / self.img_center
                    logger.debug(f'object label:{self.label }, bbox:{self.bbox}, score:{self.score}, position:{self.position }')
                    break

    def _dispatch_action(self, label, angle, throttle):
        action_label = self.running_action
        
        if action_label == None: # if no action is running then check if there is an action for the label
          if label in self.__actions:
              self.running_action = label
              action_label = label

        if action_label != None: # if there is an action running then manage it
             # if the label is the same as the action label then found is True
            found = True if label == action_label else False
            
            angle, throttle, reset_action = self.__actions[action_label].manage(angle, throttle, found, self.position)
            if reset_action:
                self.run_counter = 0
                self.running_action = None
            logger.info(f'dispatch action_label:{action_label}, reset_action:{reset_action}, angle:{angle}, throttle:{throttle}')
        else:
            self.run_counter = 0  # reset the run counter if no action is running
        
        return angle, throttle
