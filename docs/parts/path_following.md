
# Path Following with the Intel Realsense T265 sensor

Rather than using a standard camera and training a network to drive, Donkeycar supports using the [Intel Realsense T265 "tracking camera"](https://www.intelrealsense.com/tracking-camera-t265/) to follow a path instead. In this application, you simply drive a path once manually, and Donkeycar will "remember" that path and repeat it autonomously.

The Intel T265 uses a combination of stereo cameras and an internal Inertial Measurement Unit (IMU) plus its own Myriad X processor to do Visual Inertial Odometry, which is a fancy way of saying that it knows where it is by looking at the scene around it as it moves and correlating that with the IMU's sensing to localize itself, outputting an X,Y,Z position to Donkey, much as a GPS sensor would (but ideally much more accurately, to a precision of centemeters)

---------------
* **Note** Although the Realsense T265 can be used with a Nvidia Jetson Nano, it's a bit easier to set up with a Raspberry Pi (we recommend the RPi 4, with at least 4GB memory). Also, the Intel Realsense D4XX series can also be used with Donkeycar as a regular camera (with the use of its depth sensing data coming soon), and we'll add instructions for that when it's ready.

Original T265 path follower code by [Tawn Kramer](https://github.com/tawnkramer/donkey)
----


## Step 1: Setup Librealsense on Ubuntu Machine

Using the latest version of Raspian (tested with Raspian Buster) on the RPi, follow [these instructions](https://github.com/acrobotic/Ai_Demos_RPi/wiki/Raspberry-Pi-4-and-Intel-RealSense-D435) to set up Intel's Realsense libraries (Librealsense) and dependencies. Although those instructions discuss another Realsense sensor, they work equally well for the T265. There are also [video instructions](https://www.youtube.com/watch?v=LBIBUntnxp8)

## Step 2: Setup Donkeycar

Follow the standard instructions [here](https://docs.donkeycar.com/guide/install_software/). With the Path Follower, there is no need to install Tensorflow for this particular Donkeycar configuration however do install numpy/upgrade before running "pip install -e .[pi]"

## Step 3: Create the Donkeycar path follower app

```donkey createcar --path ~/follow --template path_follow

## Step 4: Check/change your config settings

```cd ~follow```
```sudo nano myconfig.py```

Make sure you agree with the default values or adjust them to your liking (ie. "throttle", "steering", PIDs, etc.). Uncomment (remove the #) for any line you've changed. In Nano press cntrl-o to save the file and cntrl-x to exit.

## Step 5: Run the Donkeycar path follower app

Running
``ssh pi@<your pi’s IP address or "raspberrypi.local">``
``` cd ~/follow``` 
```python3 manage.py drive```

Keep the terminal open to see the printed output of the app while it is running.

If you get an error saying that it can't find the T265, unplug the sensor, plug it back in and try again. Ensure that your gamepad is on and connected, too (blue light is on the controller)

Once it’s running, open a browser on your laptop and enter this in the URL bar: http://<your pi’s IP address or "raspberrypi.local">:8887

When you drive, the Web interface will draw a red line for the path, a green circle for the robot location. If you're seeing the green dot but not the red line, that means that a path file has already been written. Delete “donkey_path.pkl” (rm donkey_path.pkl), restart and the red line should show up


PS4 Gamepad controls are as follows:
+------------------+--------------------------+
|     control      |          action          |
+------------------+--------------------------+
|      share       | toggle auto/manual mode  |
|      circle      |        save_path         |
|     triangle     |        erase_path        |
|      cross       |      emergency_stop      |
|        L1        |  increase_max_throttle   |
|        R1        |  decrease_max_throttle   |
|     options      | toggle_constant_throttle |
|      square      |       reset_origin       |
|        L2        |        dec_pid_d         |
|        R2        |        inc_pid_d         |
| left_stick_horz  |       set_steering       |
| right_stick_vert |       set_throttle       |
+------------------+--------------------------+

## Step 6: Driving instructions

1) Mark a nice starting spot for your robot. Be sure to put it right back there each time you start.
2) Drive the car in some kind of loop. You see the red line show the path.
3) Hit circle on the PS3/4 controller to save the path.
4) Put the bot back at the start spot.
5) Then hit the “select” button (on a PS3 controller) or “share” (on a PS4 controller) twice to go to pilot mode. This will start driving on the path. If you want it go faster or slower, change this line in the myconfig.py file: ```THROTTLE_FORWARD_PWM = 400```

Check the bottom of myconfig.py for some settings to tweak. PID values, map offsets and scale. things like that. You might want to start by downloading and using the myconfig.py file from my repo, which has some known-good settings and is otherwise a good place to start.

Some tips:

When you start, the green dot will be in the top left corner of the box. You may prefer to have it in the center. If so, change PATH_OFFSET = (0, 0) in the myconfig.py file to PATH_OFFSET = (250, 250)

For a small course, you may find that the path is too small to see well. In that case, change PATH_SCALE = 5.0 to PATH_SCALE = 10.0 (or more, if necessary)

When you're running in auto mode, the green dot will change to blue

It defaults to recording a path point every 0.3 meters. If you want it to be smoother, you can change to a smaller number in myconfig.py with this line: PATH_MIN_DIST = 0.3
