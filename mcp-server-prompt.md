This repository is a python framework for autonomous RC cars.  

I would like to add an MCP server so that an LLM could work with the autopilot to help navigate a scene.  For instance, while an [autopilot](https://docs.donkeycar.com/guide/train_autopilot/#) is engaged, the AI agent may ask the car for it's current configuration and it's current state (throttle, steering and camera image) so that it can help the car make decisons.

So I believe we want an MCP server that exposes the autopilot configuration and the runtime state.  These should be high level; so we use throttle values of 1 (full forward) to zero (stopped) to -1 (full reverse) and steering values of 1 (full right) to zero (straight ahead) to -1 (full left) rather than low level PWM values.  

The first problem we want to tackle is using the CV Autopilot to navigate a track with known features.  The [Computer Vision Autopilot](https://docs.donkeycar.com/guide/computer_vision/computer_vision/) only requires a colored tape line to follow.

## The Track

- The track will be a tape line.  I suggest that we give it a specific features/structure to aid the LLM in interpreting the track. I propose this;
	- The track is made with 1 inch yellow tape arranged in segments. Each segment is 3 feet long exactly. 
	- Segments are connected at their ends and a 1 foot piece of tape of another color (Red or Blue) is crossed perpendicular to the end  of the segment.  So essentially a segment is a 'T' with a 3 feet stem and a 1 foot cross.  
	- Segments can be arranged in any way, but we should avoid crossings and tight turns.  We may start with a simple straight line that dead ends, then proceed to a looped track.
	- The segments represent the centerline of the track.
	- I think we should use just the centerline and not worry about the left and right edges in order to make it easy to create a track.

- The track will have traffic features; 
	- Stop Signs; The vehicle should stop for 5 seconds before continuing
	- Addresses; When the vehicle is 'told' to go to an address, it stops at the address until it is 'told' to go again.  Addresses will be just 3 digits for simplicity.
	- Initially I would start by only putting a traffic feature at the 'T' end of segment to make it easier for the autopilot to know where to stop.
	- features are just printed on paper and possible mounded on cardboard.  Like a 
	
- The track may have randomly places obstacles.
	- In some cases, the vehicle should stop until the obstacle is removed (a person or animal).
	- In other cases the vehicle should go around the obstacle (a stopped vehicle).  See below on how the agent can 'steer'.


## The activities

The users will create an AI agent that connects to an MCP server and performs various kinds of activities:

- Drive once around the track and top
- Drive once around the track and stop at stop signs for 5 seconds before proceeding.
- Drive once around the track and stop at obstacles until the obstacle is removed.
- Drive once around the track and drive around any obstacles.
- Drive once around the track and stop at a numbered location (and address) until commanded to continue.

These activities represent a learning progression; so we can expect any activity to also include elements of the previous ones.

Since we are using the CV autopilot that follows at tape line, the vehicle will steer itself.  However, we can allow the LLM to change the offset from the center line (target lane offset) in order to allow it to change lanes or go around an obstacle.

## The MCP Server

To facilitate this, we will create an MCP server that runs on the vehicle and provides an API for the LLM/Agent that it can discover and use to ask about the current donkeycar configuration and the running state.  It will also allow the Agent to change the running state.

### MCP Server for CV Autopilot requirements:

- an endpoint that provides the track configuration
	- the lane offset for left and right lanes, 
	- the segment configuration (3 feet log, 1 foot cross-tick)
	- the total number of segments in the track
	- whether the course is continuous (a loop) or dead-ended.
- an endpoint that provides the most recent camera frame and the current throttle and current target lane offset.
- an endpoint that allows the Agent to set the throttle and the lane offset.
- an endpoint that starts donkeycar framework
- an endpoint that stops donkeycar framework

For now the MCP server can assume the [CV Autopilot](https://docs.donkeycar.com/guide/computer_vision/computer_vision/) implemented in [cv_control.py](https://github.com/autorope/donkeycar/blob/main/donkeycar/templates/cv_control.py) with configuration in [cfg_cv_control.py](https://github.com/autorope/donkeycar/blob/main/donkeycar/templates/cfg_cv_control.py).  



