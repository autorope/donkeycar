# Lidar

A Lidar sensor can be used with Donkeycar to provide obstacle avoidance or to help navigate on tracks with walls. It records data along with the camera during training and this can be used for training

![Donkey lidar](../assets/lidar.jpg) 
## Supported Lidars

We currently only support the RPLidar series of sensors, but will be adding support for the similar YDLidar series soon. 

We recommend the [$99 A1M8](https://amzn.to/3vCabyN) (12m range) 


## Hardware Setup

Mount the Lidar underneath the camera canopy as shown above (the RPLidar A2M8 is used there, but the A1M8 mounting is the same). You can velcro the USB adapter under the Donkey plate and use a short USB cable to connect to one of your RPi or Nano USB ports. It can be powered by the USB port so there's no need for an additional power supply.

## Software Setup

Right now Lidar is only supported with the basic template. Install it as follows

donkey createcar path = ./lidarcar  template = basic


## Troubleshooting

