# Donkey Simulator

Experiment with training a donkey car to drive in simulation. This simulator is built on the the Unity game platform, uses their internal physics and graphics, and connects to a donkey Python process to use our trained model to control the simulated Donkey.

### Download the Simulator

You will need a specific build per platform:

* Ubuntu 16.04 [download](https://drive.google.com/open?id=0BxSsaxmEV-5Yc3VVdVQ4UUZOc0k)
* Mac 10.10.5+ [download](https://drive.google.com/open?id=0BxSsaxmEV-5YRnFEZmpRaks5NXM)
* Windows 7+ [download](https://drive.google.com/open?id=0BxSsaxmEV-5YRC1ZWHZ4Y1dZTkE)

Extract this compressed file. It will create a folder containing an executable. Double click that executable to launch the simulator.


#### Extra Mac Steps

If logs are not being generated you are probably running a version of OS X that sandboxes untrusted applications. This prevents the simulator writing to disk. To resolve this, move the executable within the Applications folder.

### Recorded Data

This simulator can create log data in the donkey tub format. This is stored in the `log` dir at the root of the folder next to the executable. On the mac you will need to browse the package contents to see this folder. If this folder is missing, no data will be recorded.


You can choose two different scenes.

## Generated Road Scene

The purpose of this is to create a randomly generated road so that you can have miles of curves on different road surfaces. You can train on one road and test on something similar, or a totally different surface.

## Warehouse Scene

The purpose of this is to create a specific track that is somewhat similar to an actual course in use as the primary track for the Oakland DIYRobocars Meetup.

____

### Menu Options:

##### Joystick/Keyboard No Rec

Drive the donkey with a joystick or keyboard. I used a PS2 Joystick and a PS3 Joystick. Keyboard controls use arrow keys to steer. In this mode, no data is recorded.

> Note: Keyboard data produces steering information that is stepped (ie. -1, 0, +1) and may be difficult to train with. See below for joystick setup.

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

____

## PID Controls

##### Max Speed

This setting determines the target speed during the PID auto drive. It will also affect the speed when driving by keyboard controls (not recommended).

##### Prop

This is short for proportional. This is the P part of PID that attempts to adjust steering back to the path in proportion to the deviation.

##### Diff

This is the D part of PID that attempts to limit steering back to the path as derivative to the trend of deviation, designed to limit overshoot.

##### Max Steering

>Note - Max Steering is an important adjustment. This affects categorical training quite strongly. As the steering data is normalized when written, and multiplies after coming from Python, this angle should remain constant over training and simulation. Take care when changing this value. And separate data and models by max steering setting.

Max steering can only be adjusted when using `Auto Drive No Rec`. It will also affect joystick and keyboard steering range, and should be saved and reloaded for you.

The default categorical model has 16 bins, or classes. And so, with a max steering of +-16, each bin will represent 2 degrees. It is helpful to graph the model training vs the example data to get and intuition about how it fits the data.

____

## Typical Use
* Start simulator
* Double check that `log` dir exists and is empty
* Start scene of your choice
* Hit `Auto Drive w Rec` button
* Vary the Max Speed, Prop, and Diff sliders to obtain a variety of driving styles
* Wait 10-15 minutes until you have recorded 10K+ frames of data.
* Hit the `Stop` button
* Hit the `Exit` button
* Move the `log` dir to the `~/mycar/data/` dir where you normally put tub data. This will create a `~/mycar/data/log` path.
* Train as usual.

> Note: I had problems w default categorical model. Linear model worked better for me.

``` bash
python manage.py train --tub=data/log --model=models/mypilot
```

* Start the simulator server.

``` bash
donkey sim --model=models/mypilot
```

Wait to see `wsgi starting up on http://0.0.0.0:9090`

* Enter the scene of your choice in the simulator
* Hit the button `NN Steering w Websockets`
* Your donkey should begin to move. You should see in the upper left two values for incoming steering and throttle.

______

## Joystick Setup

Keyboard input provides a poor learning signal. I recommend using the joystick to provide manual driving data.

##### Linux Joystick Setup

Unity on Linux uses the SDL library to see your joystick. And in particular the GamePad API. This is not setup by default. I needed to do these steps:

```bash
git clone https://github.com/Grumbel/sdl-jstest

sudo apt-get install cmake
sudo apt-get install libsdl1.2-dev
sudo apt-get install libsdl2-dev
sudo apt-get install libncurses5-dev
cd sdl-jstest
mkdir build
cd build
cmake ..
make install


./sdl2-jstest -l
```

Look for:
Joystick GUID: 030000004f04000008b1000000010000

The GUID will be different depending on your device.

Then open:
https://github.com/gabomdq/SDL_GameControllerDB/blob/master/gamecontrollerdb.txt

and look for your GUID in Linux section. One line is for one device type. Now modify your environment to specify information for your device:

```bash
sudo -H gedit /etc/environment
```

add the line SDL_GAMECONTROLLERCONFIG=, make sure to add the quotes at begin and end. ie.


SDL_GAMECONTROLLERCONFIG="030000004f04000008b1000000010000, ... and the rest of the long line copied from gamecontrollerdb"

* reboot
* start sim
* choose drive w joystick
* move sticks
* do happy dance


