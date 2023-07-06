#!/usr/bin/env python3
# Object Detection from Tensorflow Lite
# Find an object
#    https://github.com/tensorflow/examples/tree/master/lite/examples/object_detection/raspberry_pi
# installation:
#    pip install tflite-support
#
# Models
# https://www.tensorflow.org/lite/api_docs/python/tflite_model_maker
# 
# Stop Sign Tflite model (complete set of COCO images) from tensorflow
#   efficientdet_lite0.tflite - https://github.com/tensorflow/examples/tree/master/tensorflow_examples/lite/model_maker
# Traffic cone images source from Roboflow
#   custom model created by Craig Fox using images from Roboflow with 
#   conemodel.tflite - https://universe.roboflow.com/robotica-xftin/traffic-cones-4laxg
#
# This is a general purpose detection class that uses a model to recognize an object.


import os
import time

from tflite_support.task import core
from tflite_support.task import processor
from tflite_support.task import vision

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Object_Detector:
    # Trained TFLITE object detection models
    coco_object  = 'efficientdet_lite0.tflite'
    coco_object_edgetpu  = 'efficientdet_lite0_edgetpu.tflite'
    cone_object = 'conemodel.tflite'
    cone_object_edgetpu = 'conemodel_edgetpu.tflite'

    def __init__ (self, 
        category = None, # 'person', 'stop sign', 'cone' if None, use category_id to specify object to detect
        category_id = 0, # person
        enable_edgetpu = False, # Coral Edge TPU (USB Accelerator, Dev Board)
        max_results = 3,
        score_threshold = 0.3,
        num_threads = 4,
        ):

        # Initialize the object detection model and category_id
        model = self.coco_object_edgetpu if enable_edgetpu else self.coco_object
        self.category_id = category_id
        
        if category == None or category == 'person':
            pass        
        elif category == 'cone':
            model = self.cone_object_edgetpu if enable_edgetpu else self.cone_object
        elif category == 'stop sign':
            self.category_id = 12
        else:
            raise(Exception(f'Category value is invalid: {category}'))
        logger.debug(f'Detecting category: {category}')
        
        model = os.path.join(os.path.dirname(__file__), model)
        base_options = core.BaseOptions(file_name=model, use_coral=enable_edgetpu, num_threads=num_threads)
        detection_options = processor.DetectionOptions(max_results=max_results, score_threshold=score_threshold)
        options = vision.ObjectDetectorOptions(base_options=base_options, detection_options=detection_options)

        self.detector = vision.ObjectDetector.create_from_options(options)
        
        # Performance timer
        self.loops = 0
        self.total_time = 0
    
    def average_perf(self):
        p = 0 if self.loops == 0 else self.total_time / self.loops
        return p 
    
    def detect(self, image):
        # Create a TensorImage object from the RGB image.
        input_tensor = vision.TensorImage.create_from_array(image)
        
        # Detect objects
        start = time.time()   
        detection_result = self.detector.detect(input_tensor)       
        self.loops += 1
        self.total_time += (time.time() - start)
                
        score = 0
        name = None
        bbox = None
        for detection in detection_result.detections:
            category = detection.categories[0]
            if category.index == self.category_id:
                if category.score > score:
#                     logger.info(f'{category.category_name} : {category.score}')
                    score = category.score
                    name = category.category_name
                    bbox = detection.bounding_box
            
        return bbox, score, name
        