
# Path Following with the Intel Realsense T265 sensor

Rather than using a standard camera and training a network to drive, Donkeycar supports using the [Intel Realsense T265 "tracking camera"](https://www.intelrealsense.com/tracking-camera-t265/) to follow a path instead. In this application, you simply drive a path once manually, and Donkeycar will "remember" that path and repeat it autonomously.

The Intel T265 uses a combination of stereo cameras and an internal Inertial Measurement Unit (IMU) plus its own Myriad X processor to do Visual Inertial Odometry, which is a fancy way of saying that it knows where it is by looking at the scene around it as it moves and correlating that with the IMU's sensing to localize itself, outputting an X,Y,Z position to Donkey, much as a GPS sensor would (but ideally much more accurately, to a precision of centemeters)

---------------
* **Note** Although the Realsense T265 can be used with a Nvidia Jetson Nano, it's a bit easier to set up with a Raspberry Pi (we recommend the RPi 4, with at least 4GB memory). Also, the Intel Realsense D4XX series can also be used with Donkeycar as a regular camera (with the use of its depth sensing data coming soon), and we'll add instructions for that when it's ready.

Original T265 path follower code by [Tawn Kramer](https://github.com/tawnkramer/donkey)
----


## Step 1: Setup Librealsense on Ubuntu Machine

Using the latest version of Raspian (tested with Raspian Buster) on the RPi, follow [these instructions](https://github.com/IntelRealSense/librealsense/blob/master/doc/installation_raspbian.md) to set up Intel's Realsense libraries (Librealsense) and dependencies. 

## Step 1: Setup Donkeycar

Follow the standard instructions [here](https://docs.donkeycar.com/guide/install_software/)

## Step 3: Run the Donkeycar path follower app

After you’ve done that, set up the directory with this:

```donkey createcar --path ~/follow --template path_follower 

Running
``` cd ~/follow 
python3 manage.py drive```

Once it’s running, open a browser on your laptop and enter this in the URL bar: http://<your nano’s IP address>:8890

The rest of the instructions from Tawn’s repo:

When you drive, this will draw a red line for the path, a green circle for the robot location.

1) Mark a nice starting spot for your robot. Be sure to put it right back there each time you start.
2) Drive the car in some kind of loop. You see the red line show the path.
3) Hit X on the PS3/4 controller to save the path.
4) Put the bot back at the start spot.
5) Then hit the “select” button (on a PS3 controller) or “share” (on a PS4 controller) twice to go to pilot mode. This will start driving on the path. If you want it go faster or slower, change this line in the myconfig.py file: THROTTLE_FORWARD_PWM = 530

Check the bottom of myconfig.py for some settings to tweak. PID values, map offsets and scale. things like that. You might want to start by downloading and using the myconfig.py file from my repo, which has some known-good settings and is otherwise a good place to start.
Some tips:

When you start, the green dot will be in the top left corner of the box. You may prefer to have it in the center. If so, change PATH_OFFSET = (0, 0) in the myconfig.py file to PATH_OFFSET = (250, 250)

For a small course, you may find that the path is too small to see well. In that case, change PATH_SCALE = 5.0 to PATH_SCALE = 10.0 (or more, if necessary)

If you’re not seeing the red line, that means that a path file has already been written. Delete “donkey_path.pkl” (rm donkey_path.pkl) and the red line should show up

When you're running in auto mode, the green dot will change to blue

It defaults to recording a path point every 0.3 meters. If you want it to be smoother, you can change to a smaller number in myconfig.py with this line: PATH_MIN_DIST = 0.3
