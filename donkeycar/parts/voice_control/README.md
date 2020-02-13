# Alexa Support
## Overview
This part works together with a public Alexa skill that we have released. When you say a command, the Alexa skill will forward this command to a server hosted by us to temporarily store it. Your donkey car, installed with this part and with proper configuration, poll our server for any new command from Alexa.

![alt text](alexa_overview.png "Overview")


## Demo
Click the image below to open the video on youtube

[![Demo](https://img.youtube.com/vi/Q3kYmy0yjmc/0.jpg)](https://www.youtube.com/watch?v=Q3kYmy0yjmc)

## Command Supported
- Report device code
- autopilot
- slowdown
- speedup
- stop/manual

## Get Started
1. Use your alexa app, navigate to Skills and Games
2. Search for "Donkey Car Control"
3. Enable the Skill
4. Say "Open car control and report device code". Use a pencil to write down the device code.
5. Follow the instructions below to install the part in donkey car software running on Pi


## Installation
To install this part, add the following lines to `manage.py`, right after the `controller` setup
In manage.py
```python

if cfg.USE_ALEXA_CONTROL:
  from donkeycar.parts.voice_control.alexa import AlexaController
  V.add(AlexaController(ctr, cfg), threaded=True)
```

In myconfig.py, add the following parameters
```python
USE_ALEXA_CONTROL = True
ALEXA_DEVICE_CODE="123456"
```

## Commands
### Autopilot
`Phrases: autopilot, start autopilot`

If you use this command, it is expected that the donkey car is started with a model. This command will set the variable `mode` of the controller to `local`

### Slowdown / Speedup
`Phrases: slow down, speed up, go faster, go slower`

This command alter the `cfg.AI_THROTTLE_MULT` variable passed from the constructor. Each time this command is received, the `AI_THROTTLE_MULT` is increased/decreased by 0.05.

Note: Since this command alter `AI_THROTTLE_MULT`, it won't speed up when you are running in `user` or `local_angle` mode.

### Stop/Manual
`Phrases: human control, user mode, stop autopilot, manual`

This command will set the variable `mode` of the controller to `user`

### Report device code
`Phrases: report device code, what is your device code, device code`

Device code is a 6-digit numeric string derived by a hash function from your Alexa device ID. In order to distinguish commands from multiple Alexa devices, commands sent to our server would need an identifier, which is the device code. When donkey car poll for new command, the part will use this device code to poll for new commands.

## Backend
Check here for our web service source code, it is open source too.

https://github.com/robocarstore/donkeycar-alexa-backend

## Copyright
Copyright (c) 2020 Robocar Ltd
