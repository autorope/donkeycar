"""
od_protocol.py
Donkeycar Parts to manage a sequence of events based upon object detection 
    author: cfox570 March 2023
    The class Detection_Protocol is a base class that provides functions to manages calling the 
    Object Detector class. Run in pilot mode only.
    Four protocols are defined:
        1. Stop_and_Go - First stops the car, then pauses for delay, then passes the Stop Sign. Mimics 
        the behavior of a human driver on a road. Then the pilot takes over
        2. Pass_Object - Swerves around a Traffic Cone and then resumes driving around the track
    
    Threaded mode is likely only usable when running with the coGPUprocessor Google Coral Edge TPU.  Without the
    coprocessor, two Tensorflow Lite processes interfere with each other and the main Keras detection slows down.
    
    In non threaded mode, the run_hz parameter throttles the objection detection. It is only necessary to set to 
    run 1 or 2 times a vehicle loop. The object detection algorithm takes about 80m secs to run.  So if nothing is detected,
    very little delay is added to the vehicle loop over one second.   When an object is detected, the detection method
    is run for each cycle until the protocol ends. Examples: Stop: The Stop Sign is not seen.
    Stop and Go: The Stop Sign is passed; Pass Object: The cone is not detected. The method self.reset_run_counter() is
    called to restart the run counter to only run the algorithm run_hz times a second.
    
"""
import time
import logging
from donkeycar.parts.object_detector.detector import Object_Detector

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

class Detection_Protocol:

    def __init__ (self, 
            category = 0,
            use_edgetpu = False,
            score = 0.5,
            image_width = 160,
            run_hz = 1, # seconds; run 1 per second
            vehicle_hz = 20):
        
        self.on = True

        self.width = image_width
        self.img_center = self.width / 2
               
        self.run_trigger = int(vehicle_hz / run_hz)
        self.run_counter = 0
        self.run_inprogress = False
               
        self.newimageready = False
        self.detector_ready = True

        self.found = False
        self.not_found = True
                
        self.image = None
        self.detector_image = None
        self.bbox = None
        self.score = 0
        self.name = None
        self.position = 0.0

        self.detector = Object_Detector(category=category, enable_edgetpu = use_edgetpu, score_threshold=score)

    def mark(self, image, bbox):
        import cv2
        # top left corner of rectangle
        start_point = (bbox.origin_x, bbox.origin_y)
        # bottom right corner of rectangle
        end_point = (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height)     
        color = (255, 0, 0) # Red color
        thickness = 1
        image = cv2.rectangle(image, start_point, end_point, color, thickness)

    def ready(self):
        self.found = False
        self.not_found = False
        self.detector_image = self.image
        if self.detector_ready:
            if self.bbox is not None:
                self.found = True
                self.mark(self.detector_image, self.bbox)
            else:
                self.not_found = True

    def next_image(self, image):
        if self.detector_ready:
            self.image = image  
            self.newimageready = True   
    
    def reset_run_counter(self):
        self.run_counter = 0
 
    def detect(self):  
        self.newimageready = False
        self.detector_ready = False
        self.bbox = None
        self.score = 0
        self.name = None
        self.position = 0.0
        if self.image is not None:
            self.bbox, self.score, self.name = self.detector.detect(self.image)
        if self.bbox != None:
            self.position = ((self.bbox.origin_x + (self.bbox.width / 2)) - self.img_center) / self.img_center  
        self.detector_ready = True
    
    def update(self):
        while self.on:
           if self.newimageready:
               self.detect()
 
    def manage(self, angle, throttle):
        # template routine
        return angle, throttle

    def run_threaded(self, angle, throttle, image):
        self.ready()
        angle, throttle = self.manage(angle, throttle)
        self.next_image(image)
        if self.detector_image is None:
            self.detector_image = image
        return angle, throttle, self.detector_image   
    
    def run(self, angle, throttle, image):
        self.run_counter += 1
        if self.run_counter >= self.run_trigger:
            self.image = image
            self.detect()
            self.ready()
            angle, throttle = self.manage(angle, throttle)
            return angle, throttle, self.detector_image
        else:
            return angle, throttle, image           

    def shutdown(self):
        logger.info(f'Detector - average detection time {self.detector.average_perf():5.3f}')
        self.on = False
        
class Stop_Manager():
    # Stop states
    stop_states = ('idle', 'start', 'back1', 'forward', 'back2')
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

'''
    Stop_And_Go:
        args:
            pause_time:     2.0 # seconds
            image_width:    160
            run_hz:         1 
            vehicle_hz:     20
        inputs:  [pilot/angle, pilot/throttle, cam/image_array]
        outputs: [pilot/angle, pilot/throttle, cam/image_array]
        threaded:   True
        run_condition: run_pilot   

'''
  
class Stop_And_Go(Detection_Protocol):
    # Stop and Go protocol States
    states = ('running', 'stopping', 'pausing', 'passing')
    RUNNING = 0
    STOPPING = 1
    PAUSING = 2
    PASSING = 3

    def __init__(self, pause_time=2.0, **kwargs):
        super().__init__(category = 'stop sign', **kwargs)

        self.pause = pause_time
        self.state = self.RUNNING
        self.timeout = 0.0
        self.stopper = Stop_Manager()
        
    def manage(self, angle, throttle):
        if self.state == self.RUNNING: 
            if self.found:
                self.state = self.STOPPING
                self.stopper.stop()
            else:
                self.reset_run_counter()
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
            if self.not_found:
                self.state = self.RUNNING
                self.reset_run_counter()

        return angle, throttle

'''
    Pass_Cone:
        args:
            image_width:        160
            run_hz:             4
            vehicle_hz:         20    
            speedup_multiplier: 1.0
            tolerance:          0.45
            max_angle:          0.75
        inputs:  [pilot/angle, pilot/throttle, cam/image_array]
        outputs: [pilot/angle, pilot/throttle, cam/image_array]
        run_condition: run_pilot  
'''

class Pass_Object(Detection_Protocol):

    def __init__(self, speedup_multiplier=1.0, tolerance=.25, max_angle=.75, **kwargs):
        super().__init__(category = 'cone', **kwargs)

        self.speedup = speedup_multiplier
        self.max_angle = max_angle
        self.tolerance = tolerance

    def avoid(self, angle):
        cone_tol = self.position + self.tolerance
        cone_tol_neg = self.position - self.tolerance
        
        if angle >= self.position:
            if cone_tol <= self.max_angle:
                new_angle = max(angle, cone_tol)
            else:
                new_angle = angle if cone_tol <= angle else cone_tol_neg
        else: # ai angle < cone position
            if cone_tol_neg >= -self.max_angle:
                new_angle = min(angle, cone_tol_neg)
            else:
                new_angle = angle if cone_tol_neg >= angle else cone_tol

        return new_angle

    def manage(self, angle, throttle):
        new_angle = angle
        if self.detector_ready:
            if not self.found: 
                self.reset_run_counter()
            else: # found
                throttle *= self.speedup 
                new_angle = self.avoid(angle)
        return new_angle, throttle 

