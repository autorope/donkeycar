'''

Methods to create, use, save and load pilots. Pilots 
contain the highlevel logic used to determine the angle
and throttle of a vehicle. Pilots can include one or more 
models to help direct the vehicles motion. 

'''
import os
import math
import random
from operator import itemgetter
from datetime import datetime

import numpy as np
import cv2
import keras

from donkey import utils

class BasePilot():
    '''
    Base class to define common functions.
    When creating a class, only override the funtions you'd like to replace.
    '''
    def __init__(self, name=None, last_modified=None):
        self.name = name
        self.last_modified = last_modified

    def decide(self, img_arr):
        angle = 0
        speed = 0

        #Do prediction magic

        return angle, speed


    def load(self):
        return self



class SwervePilot(BasePilot):
    '''
    Example predictor that should not be used.
    '''
    def __init__(self, **kwargs):
        self.angle= random.randrange(-45, 46)
        self.throttle = 20
        super().__init__(**kwargs)


    def decide(self, img_arr):

        new_angle = self.angle + random.randrange(-4, 5)
        self.angle = min(max(-45, new_angle), 45)

        return angle, self.throttle




class KerasAngle(BasePilot):
    def __init__(self, model_path, throttle=.8, **kwargs):
        self.model_path = model_path
        self.model = None #load() loads the model
        self.throttle = throttle
        self.last_angle = 0.0
        super().__init__(**kwargs)


    def decide(self, img_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle = self.model.predict(img_arr)
        angle = angle[0][0]
        print(angle)

        #add some smoothing

        a = .8
        #angle = a * angle * 1.5  + (1.0-a) * self.last_angle
        angle = angle * 1.2
        self.last_angle = angle

        return angle, self.throttle

    def load(self):

        self.model = keras.models.load_model(self.model_path)
        return self





class OpenCVLineDetector(BasePilot): 

    def __init__(self, M=None, blur_pixels=5, canny_threshold1=100, canny_threshold2=130,
                 rho=2, theta=.02, min_line_length=80, max_gap=20, hough_threshold=9, 
                 throttle=30, **kwargs):


        self.blur_pixels = blur_pixels
        self.canny_threshold1 = canny_threshold1
        self.canny_threshold2 = canny_threshold2
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_gap = max_gap
        self.rho = rho
        self.theta = theta
        if M is not None: 
            self.M = M
        else: 
            self.M = self.get_M() 

        self.throttle = throttle

        super().__init__(**kwargs)


    def decide(self, img_arr):
        lines = self.get_lines(img_arr, 
                                self.M,
                                self.blur_pixels,
                                self.canny_threshold1,
                                self.canny_threshold2,
                                self.hough_threshold, 
                                self.min_line_length, 
                                self.max_gap, 
                                self.rho, 
                                self.theta,
                                )    
        if lines is not None:
            line_data = self.compute_lines(lines)
            clustered = self.cluster_angles(line_data)
            angle = self.decide_angle(clustered)
        else:
            angle = 0
        return angle, self.throttle



    def get_M(self):
        M = np.array([[  2.43902439e+00,   6.30081301e+00,  -6.15853659e+01],
               [ -4.30211422e-15,   1.61246610e+01,  -6.61644977e+01],
               [ -1.45283091e-17,   4.06504065e-02,   1.00000000e+00]])
        return M

    @staticmethod
    def get_lines(img, M, blur_pixels, canny_threshold1, canny_threshold2, 
                 hough_threshold, min_line_length, max_gap, rho, theta ):
        
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_blur = cv2.blur(img_gray,(blur_pixels,blur_pixels))
        img_canny = cv2.Canny(img_blur, canny_threshold1, canny_threshold2)
        lines = cv2.HoughLinesP(img_canny, rho, theta, hough_threshold, min_line_length, max_gap)
        
        if lines is not None:
            lines = lines.reshape((lines.shape[0],2,2))
            lines = lines.astype(float)
            lines = cv2.perspectiveTransform(lines, M)
        return lines


    @classmethod
    def line_length(cls, arr):
        l = math.sqrt( (arr[0,0] - arr[1,0])**2 + (arr[0,1] - arr[1,1])**2 )
        return l


    @classmethod
    def line_angle(cls, arr):
        dx = arr[1,0] - arr[0,0]
        dy = arr[1,1] - arr[0,1]
        rads = math.atan2(-dy,dx)
        rads %= 2*math.pi
        degs = -math.degrees(rads)
        if degs <= -180: 
            degs = degs + 180
            
        degs = degs + 90
        return degs


    @classmethod
    def compute_lines(cls, lines):
        
        line_data = []
        for line in lines:
            line_data.append([cls.line_angle(line), cls.line_length(line)])

        sorted(line_data, key=itemgetter(0))
        return line_data

    @staticmethod
    def cluster_angles(line_data):
        clusters = []
        last_angle = -180
        for a, l in line_data:
            if abs(last_angle - a) > 20:
                clusters.append([(a,l)])
            else:
                clusters[-1].append((a,l))
        return clusters


    @classmethod
    def decide_angle(cls, clustered_angles):
        max_length = 0
        max_cluster_id = -1
        for i, c in enumerate(clustered_angles):
            #sum lenght of lines found in clusters, filter out angles > 80 (likely in horizon)
            cluster_length = sum([l for a, l in c if abs(a) < 80])
            if cluster_length > max_length:
                max_length = cluster_length
                max_cluster_id = i

        if max_cluster_id>-1:
            angles = [a for a, l in clustered_angles[max_cluster_id]]
            #return average angle of cluster
            return sum(angles)/len(angles)
        else:
            return 0 


class PilotHandler():
    """ Convinience class to load default pilots """
    def __init__(self, models_path):

        self.models_path = os.path.expanduser(models_path)
        
        
    def pilots_from_models(self):
        """ Load pilots from keras models saved in the models directory. """
        models_list = [f for f in os.scandir(self.models_path)]
        pilot_list = []
        for d in models_list:
            last_modified = datetime.fromtimestamp(d.stat().st_mtime)
            pilot = KerasAngle(d.path, throttle=25, name=d.name, 
                                last_modified=last_modified)
            pilot_list.append(pilot)
        return pilot_list

    def default_pilots(self):
        """ Load pilots from models and add CV pilots """
        pilot_list = self.pilots_from_models()
        pilot_list.append(OpenCVLineDetector(name='OpenCV'))
        return pilot_list