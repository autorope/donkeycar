# Donkey Simulator

Experiment with training a donkey car to drive in simulation. This simulator is built on the the Unity game platform, uses their internal physics and graphics, and connects to a donkey python process to use our trained model to control the simulated Donkey.

### Download the Simulator

You will need a specific build per platform:

* Ubuntu 16.04 [download](https://drive.google.com/open?id=0BxSsaxmEV-5Yc3VVdVQ4UUZOc0k)
* Mac 10.10.5+ [download](https://drive.google.com/open?id=0BxSsaxmEV-5YRnFEZmpRaks5NXM)
* Windows 7+ [download](https://drive.google.com/open?id=0BxSsaxmEV-5YRC1ZWHZ4Y1dZTkE)

Extract this compressed file. It will create a folder with executable. Double click that executable to launch the simulator.

### Recorded Data

This simulator can create log data in the donkey tub format. This is stored in the `log` dir at the root of the folder next to the executable. On the mac you will need to browse the package contents to see this folder. If this folder is missing, no data will be recorded.


You can choose two different scenes.

## Generated Road Scene

The purpose of this is to create a randomly generated road so that you can have miles of curves on different road surfaces. You can train on one road and test on something similar, or a totally different surface.

## Warehouse Scene

The purpose of this is to create a specific track that is somewhat similar to an actual course in use as the primary track for the Oakland DIYRobocars Meetup.

### Menu Options:

##### Joystick/Keyboard No Rec

Drive the donkey with a joystick or keyboard. I used a PS2 Joystick and a PS3 Joystick. Keyboard controls use arrow keys to steer. In this mode, no data is recorded.

##### Joystick/Keyboard w Rec

Drive the donkey with a joystick or keyboard. In this mode, data is stored in the tub donkey format.

##### Auto Drive No Rec

This uses path information to guide the donkey down the track. It uses a PID controller to steer, so there is some oscillation. In this mode, no data is stored.

##### Auto Drive w Rec

This uses path information to guide the donkey down the track. It uses a PID controller to steer, so there is some oscillation. In this mode, data is stored in the tub donkey format.

##### Next Track

In the generated road scene, this will switch out the road surface and track width.

##### Regen Track

Use the current surface type, but generate a new random path and road.



## Typical Use
* Start simulator
* Double check that `log` dir exists and is empty
* Start scene of your choice
* Hit `Auto Drive w Rec` button
* Wait 10-15 minutes until you have recorded 10K+ frames of data.
* Hit the `Stop` button
* Hit the `Exit` button
* Move the `log` dir to the `~/d2/data/` dir where you normally put tub data. This will create a `~/d2/data/log` path.
* Train as usual. 

``` bash
python manage.py train --tub=data/log --model=models/mypilot
```

* Start the simulator server. 

``` bash
python manage.py sim --model=models/mypilot
```

Wait to see `wsgi starting up on http://0.0.0.0:9090`

* Enter the scene of your choice in the simulator
* Hit the button `NN Steering w Websockets`
* Your donkey should begin to move. You should see in the upper left two values for incoming steering and throttle.

