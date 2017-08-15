# About Donkey

Donkey is a high level self driving library written in Python and capable of 
controlling ackerman or differential drive vehicles. It was developed with a 
focus on enabling fast experimentation and easy contribution.

---------

### Build your own Donkey2

Donkey2 is the standard car that most people start with. The parts cost $200
and take 2 hours to assemple. Here are the main steps to build your own car: 

1. [Build a car.](guide/build_hardware.md).
2. [Install the software.](guide/install_software.md)
3. [Calibrate your car.](guide/calibrate.md)
4. [Start driving.](guide/get_driving.md) 
5. [Train an autopilot.](guide/train_autopilot.md) 


---------------


### Hello World. 

Donkeycar is designed to make it easy to customize your car by adding or 
removing parts. Here's a simple example of a car that just captures
images from the camera and saves them.

```python

import donkey as dk

V = dk.Vehicle()

#add a camera
cam = dk.parts.PiCamera()
V.add(cam, outputs=['image'], threaded=True)

#record the images
tub = dk.parts.Tub(path='~/d2/gettings_started', 
                   inputs=['image'], 
                   types=['image_array'])
V.add(tub, inputs=inputs)

#start the drive loop
V.start(max_loop_count=100)
```

----------------

### Installation

The donkeycar package can be installed two ways.

Use pypi to install the stable version:
```bash
pip install donkeycar
```


Clone the master branch to get the lastest version. Use this if you plan 
to contribute code.. 
```bash
git clone https://github.com/wroscoe/donkey donkeycar
pip install -e donkeycar
```
-----------------------

### Why the name Donkey?

The ultimate goal of this project is to build something useful. Donkey's were
one of the first domesticated pack animals, they're notoriously stubborn, and 
they are kid safe. Until the car can nagigate from one side of a city to the 
other, we'll hold off naming it after some celestial being.