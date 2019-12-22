# Create your car application

If you are not already, please [ssh into your vehicle](/guide/robot_sbc/setup_raspberry_pi/#step-5-connecting-to-the-pi).

## Create Donkeycar from Template

Create a set of files to control your Donkey with this command:

```bash
donkey createcar --path ~/mycar
```

See also more information on [createcar.](/utility/donkey/#create-car)

## Configure Options

Look at __myconfig.py__ in your newly created directory, ~/mycar
```bash
cd ~/mycar
nano myconfig.py
```

Each line has a comment mark. The commented text shows the default value. When you want to make an edit to over-write the default, uncomment the line by removing the # and any spaces before the first character of the option.

example:

```python
# STEERING_LEFT_PWM = 460
```

becomes:

```python
STEERING_LEFT_PWM = 500
```

when edited. You will adjust these later in the [calibrate](/guide/calibrate/) section.

### Configure I2C PCA9685

If you are using a PCA9685 card, make sure you can see it on I2C.

**Jetson Nano**:

```bash
sudo usermod -aG i2c $USER
sudo reboot
```

After a reboot, then try:

```bash
sudo i2cdetect -r -y 1
```

**Raspberry Pi**:

```bash
sudo apt-get install -y i2c-tools
sudo i2cdetect -y 1
```

This should show you a grid of addresses like:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: 70 -- -- -- -- -- -- --
```

In this case, the 40 shows up as the address of our PCA9685 board. If this does not show up, then check your wiring to the board. On a pi, ensure I2C is enabled in menu of ```sudo raspi-config``` (notice, it suggest reboot).

If you have assigned a non-standard address to your board, then adjust the address in the `myconfig.py` under variable `PCA9685_I2C_ADDR`. If your board is on another bus, then you can specify that with the `PCA9685_I2C_BUSNUM`.

**Jetson Nano**: set ```PCA9685_I2C_BUSNUM = 1``` in your __myconfig.py__ . For the pi, this will be auto detected by the Adafruit library. But not on the Jetson Nano.

## Sombrero Setup

Set ```HAVE_SOMBRERO = True``` in your __myconfig.py__ if you have a sombrero board.

## Robo HAT MM1 Setup

Set ```HAVE_ROBOHAT = True``` in your __myconfig.py__ if you have a Robo HAT MM1 board.

The Robo HAT MM1 uses a RC Controller and CircuitPython script to drive the car during training. You must put the CircuitPython script onto the Robo HAT MM1 with your computer before you can continue.

1.  Download the CircuitPython Donkey Car Driver for Robo HAT MM1 to your computer from [here](https://github.com/robotics-masters/mm1-hat-cpy-native/blob/master/examples/rc-cpy-final.py)
2.  Connect the MicroUSB connector on the Robo HAT MM1 to your computer's USB port.
3.  A __CIRCUITPY__ device should appear on the computer as a USB Storage Device
4.  Copy the file downloaded in Step 1 to the __CIRCUITPY__ USB Storage Device.  Rename the file __code.py__.
5.  Unplug USB Cable from the Robo HAT MM1 and place on top of the Raspberry Pi, as you would any HAT.


You may need to enable the hardware serial port on your Raspberry Pi.  On your Raspberry Pi...

1.  Run the command ```sudo raspi-config```
2.  Navigate to the __5 - Interfaceing options__ section.
3.  Navigate to the __P6 - Serial__ section.
4.  When asked: __Would you like a login shell to be accessible over serial?__  NO
5.  When asked: __Would you like the serial port hardware to be enabled?__ YES
6.  Close raspi-config
7.  Restart


Please skip to [here](/guide/get_driving) to continue setting up your car.

## Joystick setup

If you plan to use a joystick, take a side track over to [here](/parts/controllers/#joystick-controller).

## Camera Setup

**Raspberry Pi**:

If you are on a raspberry pi and using the recommended pi camera, then no changes are needed to your __myconfg.py__. 

**Jetson Nano**:

When using a Sony IMX219 based camera, and you are using the default car template, then you will want edit your __myconfg.py__ to have:
`CAMERA_TYPE = "CSIC"`.
For flipping the image vertically set `CSIC_CAM_GSTREAMER_FLIP_PARM = 3` - this is helpful if you have to mount the camera in a rotated position.
Set `IMAGE_W = 224` and also `IMAGE_H = 224`.

CVCAM is a camera type that has worked for USB cameras when OpenCV is setup. This requires additional setup for [OpenCV for Nano](/guide/robot_sbc/setup_jetson_nano/#step-4-install-opencv) or [OpenCV for Raspberry Pi](https://www.learnopencv.com/install-opencv-4-on-raspberry-pi/).

WEBCAM is a camera type that uses the pygame library, also typically for USB cameras. That requires additional setup for [pygame](https://www.pygame.org/wiki/GettingStarted).

## Troubleshooting

If you are having troubles with your camera, check out our [Discourse FAQ for hardware troubleshooting](https://donkey.discourse.group/t/faq-troubleshooting/33). Check this forum for more help.

## Keeping Things Up To Date

Make all config changes to __myconfig.py__ and they will be preserved through an update. If you are a long time user, you might be used to editing config.py. You should switch to editing myconfig.py instead. Later on, when changes occur that you would like to get, you can pull latest code, then issue a:

```bash
cd projects/donkeycar
git pull
donkey createcar --path ~/mycar --overwrite
```

Your ~/mycar/manage.py, ~/mycar/config.py and other files will change with this operation, but __myconfig.py__ will not be touched. Your __data__ and __models__ dirs will not be touched.

> Note: If you are updating from Donkey<3.0 to 3.0+ it is very likely you will need to start over with a new virtual environment. We've had a few users hit this snag.

-------

### Next [calibrate your car](/guide/calibrate/).
