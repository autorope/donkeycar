#!/usr/bin/env python3
# Object Detection from Mediapipe
# Mediapipe-studio
#     https://mediapipe-studio.webapps.google.com/home
# Mediapipe-examples-object_detection
#     https://github.com/google-ai-edge/mediapipe-samples/tree/main/examples/object_detection/raspberry_pi
# installation:
#     pip install mediapipe
#
# Model
#     efficientdet_lite0: https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite
#     category list: https://storage.googleapis.com/mediapipe-tasks/object_detector/labelmap.txt
#
# This is a general purpose detection class that uses a model to recognize an object.

import os
import time
import os

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MediapipeObjectDetector:
    def __init__(self,
                 od_model_path,  # object detection model path
                 max_results=3,
                 score_threshold=0.3):

        # Check model file
        if not os.path.exists(od_model_path):
            raise (
                Exception(f'ObjectDetector Model file not found: {od_model_path}'))
        logger.debug(f"MediapipeOD load model {od_model_path}")

        # Initialize the object detection model
        base_options = python.BaseOptions(model_asset_path=od_model_path)
        options = vision.ObjectDetectorOptions(base_options=base_options,
                                               max_results=max_results,
                                               score_threshold=score_threshold)
        self.detector = vision.ObjectDetector.create_from_options(options)

        # Performance timer
        self.loops = 0
        self.total_time = 0

    def average_perf(self):
        p = 0 if self.loops == 0 else self.total_time / self.loops
        return p

    def detect(self, image):
        # Create a MediaPipe Image from the RGB image.
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        # gray_frame = mp.Image(image_format=mp.ImageFormat.GRAY8,
        #                   data=cv2.cvtColor(cv_mat, cv2.COLOR_RGB2GRAY))
        
        # Detect objects
        start = time.time()
        detection_result = self.detector.detect(mp_image)

        self.loops += 1
        cost = time.time() - start
        self.total_time += cost
        logger.debug(f'detect_time_cost:{cost}')

        result = []  # list of (category, bbox, score)
        for detection in detection_result.detections:
            bbox = detection.bounding_box
            for category in detection.categories:
                result.append((category.category_name, bbox, category.score))
        return result
