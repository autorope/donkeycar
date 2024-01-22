# Configs for races

## Obstacle detector always active
- Deactivate if performance problem
- Use steering scaler to improve object avoidance

## AI sprint & AI slalom
Fixed speed:
- auto steering : local_angle
- auto fixed_speed : 0.16
```
ROBOCARSHAT_PILOT_MODE = 'local_angle' # Which autonomous mode is triggered by Hat : local_angle or local
ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE = 0.16 # For pilot_angle autonomous mode (aka constant throttle), this is the default throttle to apply
```
AI speed:
- auto steering : local
- auto fixed_speed : 0.16

```
ROBOCARSHAT_PILOT_MODE = 'local_angle' # Which autonomous mode is triggered by Hat : local_angle or local
ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE = 0.16 # For pilot_angle autonomous mode (aka constant throttle), this is the default throttle to apply
```

## AI lane racing
- default left or right  (2 lane mode)

```
OBSTACLE_DETECTOR_AVOIDANCE_ENABLED = True # To free drive using behavior model, Si True, active l'autopilote du steering avec avoidance
OBSTACLE_DETECTOR_MANUAL_LANE = False # si True, active le mode copilot pour le steering depuis la radio 
```

## COPILOT sprint & AI slalom
- auto steering : local_angle
- auto fixed_speed : None 

```
ROBOCARSHAT_PILOT_MODE = 'local_angle' # Which autonomous mode is triggered by Hat : local_angle or local
ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE = None # For pilot_angle autonomous mode (aka constant throttle), this is the default throttle to apply
```

## COPILOT lane racing
- default left or right (2 lane mode)

```
OBSTACLE_DETECTOR_AVOIDANCE_ENABLED = False # To free drive using behavior model, Si True, active l'autopilote du steering avec avoidance
OBSTACLE_DETECTOR_MANUAL_LANE = True # si True, active le mode copilot pour le steering depuis la radio 
```

