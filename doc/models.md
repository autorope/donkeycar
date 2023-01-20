# This document lists possible models by challenge

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
