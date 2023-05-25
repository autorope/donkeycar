Throttle and Steering Scaler

# Introduction

Part robocars_hat_ctrl implements a new class named RobocarsHatDriveCtrl which implements static and dynamic scalers on throttle and steering.

Idea is to train manually a model at limited throttle to ensure good quality of driving data, and then increase overall throttle in pilot mode by applying scalar factors.
Throttle used to make the training is then used to configure key ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE

There are several kinds of factors :
- static factor, applied anytime
- extra factor applued only when straight line is detected
- dynamic factor spplied on steering to compensate late decision done by model when factor is applied on throttle

# Factors 

## Static throttle factor
This is controled by config key ROBOCARS_THROTTLE_SCALER which is set to 1.0 by default.

## Extra throttle factor when in straight line
This is controled by config key ROBOCARS_THROTTLE_SCALER_ON_SL which is set to 1.0 by default.

## Steering dynamic factor
This is controled by config key ROBOCARS_CTRL_ADAPTATIVE_STEERING_SCALER which is set to 1.0 by default.

# Setup instructions

Setup requires a trained model as decribed above, since instructions below are performed in pilot mode.

To help to adjust this setting, you can use several specific working mode:
- Control static throttle scalar from remote control
- Control dynamic steering scalar from remote control (from Auxiliary Channel)

## Feature to Control static throttle scalar from remote control
The config key ROBOCARSHAT_EXPLORE_THROTTLE_SCALscalarER_USING_THROTTLE_CONTROL feature allows you to control a throttle factor by increment, using the throttle trigger from the remote controler, between 1.0 and value configured in config key AUX_FEATURE_THROTTLE_SCALAR_EXP_MAX_VALUE (2.0 by default). Pushing throttle trigger will increment factor by 0.1, while pulling throttle trigger will decrement factor by 0.1. Each time value changes, it is printed out in the console. If you pull trigger full backward (reverse), brake cycle is performed and pilot mode is suspended until you release the command (then pilot mode is reengaged as long as pilot control remains engaged) 

## Feature Control dynamic steering scalar from remote control
This feature is controled thand an auxiliary channel, thanks to feature name 'adaptative_steering_scalar_exp'. When configured, the auxiliary channel is used to control the dynamic stewering scalar between 1.0 and config key  AUX_FEATURE_ADAPTATIVE_STEERING_SCALAR_EXP_MAX_VALUE (3.0 by default). Each time value changes, it is printed out in the console.

## Step by step
### Find Static throttle factor
Using the ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL feature, the first step is to find a static throttle factor value that works when applied continuously for a given track.
Once a factor value for which pilot mode works on all parts of the track is identified, report this value to config key ROBOCARS_THROTTLE_SCALER as a baseline. This factor is then the maximal constant throttle factor applicable for that track.

### Find the Dynamic steering factor that allow to increase static throttle factor.
Now, we can increase even more the static throttle factor by using dynamic steering factor to compensate for late decision done by the model in turn when throttle in increased thantks to scaler. 
Use both ROBOCARSHAT_EXPLORE_THROTTLE_SCALER_USING_THROTTLE_CONTROL feature, and 'adaptative_steering_scalar_exp' to find at which extend you can inscrease again static trottle scalar factor by increaseing dapatative steering scalar factor, keeping the car on the track. When new values are identified for both factor, report throttle factor in key ROBOCARS_THROTTLE_SCALER and steering factor in key ROBOCARS_CTRL_ADAPTATIVE_STEERING_SCALER


