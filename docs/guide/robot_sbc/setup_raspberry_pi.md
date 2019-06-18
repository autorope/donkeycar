# Get Your Raspberry Pi Working.

![donkey](/assets/logos/rpi_logo.png)

* [Step 1: Flash Operating System](#step-1-flash-operating-system)
* [Step 2: Setup the WiFi for First Boot](#step-2-setup-the-wifi-for-first-boot)
* [Step 3: Setup Pi's Hostname](#step-3-setup-pis-hostname)
* [Step 4: Enable SSH on Boot](#step-4-enable-ssh-on-boot)
* [Step 5: Connecting to the Pi](#step-5-connecting-to-the-pi)
* [Step 6: Update and Upgrade](#step-6-update-and-upgrade)
* [Step 7: Raspi-config](#step-7-raspi-config)
* [Step 8: Install Dependencies](#step-8-install-dependencies)
* [Step 9: Install Optional OpenCV Dependencies](#step-9-install-optional-opencv-dependencies)
* [Step 10: Setup Virtual Env](#step-10-setup-virtual-env)
* [Step 11: Install Donkeycar Python Code](#step-11-install-donkeycar-python-code)
* [Step 12: Install Optional OpenCV](#step-12-install-optional-opencv)
* Then [Create your Donkeycar Application](/guide/create_application/)

## Step 1: Flash Operating System

You need to flash a micro SD image with an operating system.

1. Download [Raspian Lite](https://downloads.raspberrypi.org/raspbian_lite_latest) (300MB). 
2. Follow OS specific guides [here](https://www.raspberrypi.org/documentation/installation/installing-images/).
3. Leave micro SD card in your machine and edit/create some files as below:

## Step 2: Setup the WiFi for first boot

We can create a special file which will be used to login to wifi on first boot. More reading [here](https://raspberrypi.stackexchange.com/questions/10251/prepare-sd-card-for-wifi-on-headless-pi), but we will walk you through it. 

On Windows, with your memory card image burned and memory disc still inserted, you should see two drives, which are actually two partitions on the mem disc. One is labeled __boot__. On Mac and Linux, you should also have access to the __boot__ partition of the mem disc. This is formated with the common FAT type and is where we will edit some files to help it find and log-on to your wifi on it's first boot. 

> Note: If __boot__ is not visible right away, try unplugging and re-insterting the memory card reader.

* Start a text editor: `gedit` on Linux. Notepad++ on Windows. TextEdit on a Mac.
* Paste and edit this contents to match your wifi:
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="<your network name>"
    psk="<your password>"
}

```

Replace `<your network name>` with the ID of your network. Leave the quotes. I've seen problems when the network name contained an apostrophe, like "Joe's iPhone".
Replace `<your password>` with your password, leaving it surrounded by quotes. 
If it bothers you to leave your password unencrypted, you may change the [contents later](https://unix.stackexchange.com/questions/278946/hiding-passwords-in-wpa-supplicant-conf-with-wpa-eap-and-mschap-v2) once you've gotten the pi to boot and log-in.

* Save this file to the root of __boot__ partition with the filename `wpa_supplicant.conf`. On first boot, this file will be moved to `/etc/wpa_supplicant/wpa_supplicant.conf` where it may be edited later. If you are using Notepad on Windows, make sure it doesn't have a .txt at the end.

## Step 3: Setup Pi's Hostname
> Note: This step only possible on a linux host pc. Otherwise you can set it up later in raspi-config after logging in to your pi.

We can also setup the hostname so that your Pi easier to find once on the network. If yours is the only Pi on the network, then you can find it with 

```
ping raspberrypi.local
```

once it's booted. If there are many other Pi's on the network, then this will have problems. If you are on a Linux machine, or are able to edit the UUID partition, then you can edit the `/etc/hostname` and `/etc/hosts` files now to make finding your pi on the network easier after boot. Edit those to replace `raspberrypi` with a name of your choosing. Use all lower case, no special characters, no hyphens, yes underscores `_`. 

```
sudo vi /media/userID/UUID/etc/hostname
sudo vi /media/userID/UUID/etc/hosts
```

## Step 4: Enable SSH on Boot

Put a file named __ssh__ in the root of your __boot__ partition.


Now you're SD card is ready. Eject it from your computer, put it in the Pi 
and plug in the Pi.


## Step 5: Connecting to the Pi

If you followed the above instructions to add wifi access you're Pi should
now be connected to your wifi network. Now you need to find it's IP address
so you can connect to it via SSH. 

The easiest way (on Ubuntu) is to use the `findcar` donkey command. You can try `ping raspberrypi.local`. If you've modified the hostname, then you should try: `ping <your hostname>.local`. This will fail on a windows machine. Windows users will need the full IP address (unless using cygwin). 

If you are having troubles locating your Pi on the network, you will want to plug in an HDMI monitor and USB keyboard into the Pi. Boot it. Login with:

* Username: __pi__
* Password: __raspberry__
 
Then try the command:

```
ifconfig wlan0
```

If this has a valid IPv4 address, 4 groups of numbers separated by dots, then you can try that with your SSH command. If you don't see anything like that, then your wifi config might have a mistake. You can try to fix with

```
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

If you don't have a HDMI monitor and keyboard, you can plug-in the Pi with a CAT5 cable to a router with DHCP. If that router is on the same network as your PC, you can try:

```
ping raspberrypi.local
```

Hopefully, one of those methods worked and you are now ready to SSH into your Pi. On Mac and Linux, you can open Terminal. On Windows you can install [Putty](http://www.putty.org/), [one of the alternatives](https://www.htpcbeginner.com/best-ssh-clients-windows-putty-alternatives/2/), or on Windows 10 you may have ssh via the command prompt.

If you have a command prompt, you can try:

```
ssh pi@raspberrypi.local
```

or

```
ssh pi@<your pi ip address>
```

or via Putty.

* Username: __pi__
* Password: __raspberry__
* Hostname:`<your pi IP address>`

## Step 6: Update and Upgrade

```bash
sudo apt-get update
sudo apt-get upgrade
```

## Step 7: Raspi-config

```bash
sudo raspi-config
```

* change default password for pi
* change hostname
* enable Interfacing Options | I2C
* enable Interfacing Options | Camera
* Advanced Options | Exapand Filesystem

Choose <Finish> and hit enter.

> Note: Reboot after changing these settings. Should happen if you say yes.

## Step 8: Install Dependencies

```bash
sudo apt-get install build-essential python3 python3-dev python3-virtualenv python3-numpy python3-picamera python3-pandas python3-rpi.gpio i2c-tools avahi-utils joystick libopenjp2-7-dev libtiff5-dev gfortran libatlas-base-dev libopenblas-dev libhdf5-serial-dev git
```

## Step 9: Install Optional OpenCV Dependencies

If you are going for a minimal install, you can get by without these. But it can be handy to have OpenCV.

```bash
sudo apt-get install libilmbase-dev libopenexr-dev libgstreamer1.0-dev libjasper-dev libwebp-dev libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev libqtgui4 libqt4-test
```

##  Step 10: Setup Virtual Env

```bash
python3 -m virtualenv -p python3 env --system-site-packages
echo "source env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```
Modifying your .bashrc in this way will automatically enable this environment each time you login. To return to the system python you can type `deactivate`.

##  Step 11: Install Donkeycar Python Code

* Change to a dir you would like to use as the head of your projects.

```
mkdir projects
cd projects
```

* Get the latest donkeycar from Github.

```bash
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
pip install -e .[pi]
pip install tensorflow
```

You can validate your tensorflow install with

```bash
python -c "import tensorflow"
```

Warnings like this are normal:
```
/home/pi/env/lib/python3.5/importlib/_bootstrap.py:222: RuntimeWarning: compiletime version 3.4 of module 'tensorflow.python.framework.fast_tensor_util' does not match runtime version 3.5
  return f(*args, **kwds)
/home/pi/env/lib/python3.5/importlib/_bootstrap.py:222: RuntimeWarning: builtins.type size changed, may indicate binary incompatibility. Expected 432, got 412
  return f(*args, **kwds)
```

##  Step 12: Install Optional OpenCV

If you've opted to install the OpenCV dependencies earlier, you can install Python OpenCV bindings now with

```bash
pip install opencv-python
python -c "import cv2"
```

And if no errors, you have OpenCV installed!

----

### Next, [create your Donkeycar application](/guide/create_application/).
