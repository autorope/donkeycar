# This document lists possible models by challenge

## Detect obstacle lane and avoid obstacle by driving in the other lane
### Description
- KerasDetector model outputs obstacle's lane presence based solely on the camera image
  - output can be 'left', 'right' or 'NA'
- AvoidanceBehaviorPart will interpret KerasDetector ouput and build the behavior vector to input in KerasBehavior Model
  - output can be 
    - [1.,0.] to drive on left lane
    - [0.,1.] to drive on right lane
    - [0.,0.] to allow to use the whole track
- KerasBehavior will use the camera image and the behavior vector as inputs
  - output will be standard steering and throttle

### Configuration
- To activate these parts the following configuration is required
  - ONNX Format
  ```
  CREATE_ONNX_MODEL = True      #This configuration is required to be able to run 2 models in every loop
  ```
  - OBSTACLE_DETECTOR 
  ``` 
  OBSTACLE_DETECTOR_ENABLED = True                                         # To activate/deactivate obsttacle detector
  OBSTACLE_DETECTOR_NUM_LOCATIONS = 4                                      # Number of possible obstacle states
  OBSTACLE_DETECTOR_MODEL_PATH = "~/mycar/models/pilot_23-02-15_29.onnx"   # Path of the obstacle detector model, extension must match model type 
  OBSTACLE_DETECTOR_MODEL_TYPE = "onnx_obstacle_detector"                  # Model type
  OBSTACLE_DETECTOR_BEHAVIOR_LIST = ['NA', 'left', 'middle', 'right']      # Array of possible obstacle states
  BEHAVIOR_LIST = ['left', 'right']                                        # used in avoidance_behavior
  ```

### Run
```
cd ~/mycar
python manage.py drive --type=onnx_behavior --model=models/pilot_23-02-15_30.onnx 
```

## Follow the track

### Donkey standard parts

- KerasLinear (used)
- KerasMemory

### Lane detection + control theory

Idea: Detect the lanes to evaluate a trajectory as a set of waypoints and create an asserv to follow the trajectory. Because trajectory detection may be slow, use an estimation of the position to update waypoints.

Use 3 components:

- C1: detect the central path of the road (as a simple trajectory estimation) and express it as a set of waypoints
- C2: estimate the pose (x, y, orientation) of the car
- C3: do an asserv that use current pose and waypoints to calculate throttle and steering

Pose estimation is needed because:

- waypoints from C1 are calculated from data collected at T0
- they will be available at T1, P = T1 - T0 = C1 processing time
- and will be updated every T (C1 period), which means we need to use those waypoints between T1 and T1 + T before receiving updated waypoints
- waypoints where valid for car pose at T0, current pose and pose at T0 are used to update waypoints => pose estimation only need to be accurate for P + T duration

Possible algorithms:

- C1:
  - image segmentation to get lanes, see [road-segmentation-adas-0001 from DepthAPI Demo](https://github.com/luxonis/depthai)
  - and opencv to extract waypoints
- C2:
  - velocity from odometry + steering command to create a feedforward model
  - enhanced, eventually, with IMU via sensor fusion (EKF)

Current results:

- Image segmentation takes 470 ms at 4 fps => pose estimation must be reliable during at least 720 ms
- Waypoints are extracted for approx 1 m ahead => velocity is limited to 1.38 m/s (5 km/h)
- IMU need (tedious) calibration and being STATIC, position drifts approx by 5 mm/s and orientation by 0.06 °/s => pose estimation seems possible, but difficult, for needed duration

Improvements:

- Make it work (end to end integration)
- Faster lane detection
  - Reduce NN image size: road-segmentation-adas-0001 works on 896 x 512 image size => finding another network
  - Alternatively, use a different method (opencv ?)

## Collision avoidance

### Luxonis models/algorithms

- [depthai experiments collision avoidance](https://github.com/luxonis/depthai-experiments/tree/master/collision-avoidance)

## Track side signals

### Read track side signals

- [depthai experiments OCR](https://github.com/luxonis/depthai-experiments/tree/master/gen2-ocr)

## Grip loss detection
- Find a model to use IMU and detect sudden lateral acceleration to identify maximum speed with grip

## decision confidence management
- How to improve the models when images cannot be inferred with sufficient confidence
- What is the offline learning cycle

## use segmentation to tag images 
- Modify acquired driving date with the correct steering angle based on track orientation vs car orientation
- 
