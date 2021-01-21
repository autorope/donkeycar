# Get Your Raspberry Pi Working

![donkey](/assets/logos/rpi_logo.png)

- [Get Your Raspberry Pi Working](#get-your-raspberry-pi-working)
  - [Step 1: Flash the SD Card](#step-1-flash-the-sd-card)
    - [Robocar Store Pre-built image](#robocar-store-pre-built-image)
    - [Ground up install](#ground-up-install)
  - [Step 2: Setup the WiFi for first boot](#step-2-setup-the-wifi-for-first-boot)
  - [Step 3: Setup Pi's Hostname](#step-3-setup-pis-hostname)
  - [Step 4: Enable SSH on Boot](#step-4-enable-ssh-on-boot)
  - [Step 5: Connecting to the Pi](#step-5-connecting-to-the-pi)
  - [Step 6: Update and Upgrade](#step-6-update-and-upgrade)
  - [Step 7: Raspi-config](#step-7-raspi-config)
  - [Step 8: Install Dependencies](#step-8-install-dependencies)
  - [Step 9: Optional - Install OpenCV Dependencies](#step-9-optional---install-opencv-dependencies)
  - [Step 10: Setup Virtual Env](#step-10-setup-virtual-env)
  - [Step 11: Install Donkeycar Python Code](#step-11-install-donkeycar-python-code)
  - [Step 12: Optional - Install OpenCV](#step-12-optional---install-opencv)
    - [Next, create your Donkeycar application.](#next-create-your-donkeycar-application)

## Step 1: Flash the SD Card

### Robocar Store Pre-built image

Robocar Store provide a pre-built image so you can just use software like Etcher to quickly get started. If you are using this image, you still need to perform step 2-5 below but you can skip step 6 - 10 as we have done that for you. You will probably save around 30 - 45 minutes if you use this image.

* Donkey Car v3.0.2 on Stretch - [Download](https://www.dropbox.com/s/27bt4ut6fufg1nb/robocarstore_dk302_stretch.zip?dl=0)
* Donkey Car v3.1.0 on Stretch - [Download](https://www.dropbox.com/s/z8uhfoetlxwpsua/robocarstore_dk310_stretch.img.gz?dl=0)

hostname: raspberrypi

* Donkey Car v3.1.0 on Buster (Pi 4) - [Download](https://www.dropbox.com/s/a7booipqanalh2d/robocarstore_dk310_buster.img.gz?dl=0)

hostname: pi4


The uncompressed image will be around 16GB. Download [Etcher](https://www.balena.io/etcher/) and burn the image to the SD card. As we have shrinked the partition to improve the speed to burn the image, you need to expand the partition by running `sudo raspi-config`. If in doubt, check how to do this on google.


### Ground up install

> Note:  If you plan to use the mobile app, consider using the pre-built image. Refer to the [mobile app user guide](../mobile_app.md) for details. 

You need to flash a micro SD image with an operating system.

1. Download [Raspian Lite(Stretch)](https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2019-04-09/2019-04-08-raspbian-stretch-lite.zip) (352MB).
2. Follow OS specific guides [here](https://www.raspberrypi.org/documentation/installation/installing-images/).
3. Leave micro SD card in your machine and edit/create some files as below:

## Step 2: Setup the WiFi for first boot

We can create a special file which will be used to login to wifi on first boot. More reading [here](https://raspberrypi.stackexchange.com/questions/10251/prepare-sd-card-for-wifi-on-headless-pi), but we will walk you through it.

On Windows, with your memory card image burned and memory disc still inserted, you should see two drives, which are actually two partitions on the mem disc. One is labeled __boot__. On Mac and Linux, you should also have access to the __boot__ partition of the mem disc. This is formated with the common FAT type and is where we will edit some files to help it find and log-on to your wifi on it's first boot.

> Note: If __boot__ is not visible right away, try unplugging and re-inserting the memory card reader.

* Start a text editor: `gedit` on Linux. Notepad++ on Windows. TextEdit on a Mac.
* Possible `country` codes to use can be found [here](https://www.thinkpenguin.com/gnu-linux/country-code-list)
* Paste and edit this contents to match your wifi, adjust as needed:

```text
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="<your network name>"
    psk="<your password>"
}

```

Note - `country` defines allowed wifi channels, ensure to set it properly to your location and hardware.

Replace `<your network name>` with the ID of your network. Leave the quotes. I've seen problems when the network name contained an apostrophe, like "Joe's iPhone".
Replace `<your password>` with your password, leaving it surrounded by quotes.
If it bothers you to leave your password unencrypted, you may change the [contents later](https://unix.stackexchange.com/questions/278946/hiding-passwords-in-wpa-supplicant-conf-with-wpa-eap-and-mschap-v2) once you've gotten the pi to boot and log-in.

* Save this file to the root of __boot__ partition with the filename `wpa_supplicant.conf`. On first boot, this file will be moved to `/etc/wpa_supplicant/wpa_supplicant.conf` where it may be edited later. If you are using Notepad on Windows, make sure it doesn't have a .txt at the end.

## Step 3: Setup Pi's Hostname

> Note: This step only possible on a Linux host pc. Otherwise you can set it up later in `raspi-config` after logging in to your pi.

We can also setup the hostname so that your Pi easier to find once on the network. If yours is the only Pi on the network, then you can find it with

```bash
ping raspberrypi.local
```

once it's booted. If there are many other Pi's on the network, then this will have problems. If you are on a Linux machine, or are able to edit the UUID partition, then you can edit the `/etc/hostname` and `/etc/hosts` files now to make finding your pi on the network easier after boot. Edit those to replace `raspberrypi` with a name of your choosing. Use all lower case, no special characters, no hyphens, yes underscores `_`.

```bash
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

```bash
ifconfig wlan0
```

or just all Ip addresses assigned to the pi (wifi or cable):

```bash
ip -br a
```

If this has a valid IPv4 address, 4 groups of numbers separated by dots, then you can try that with your SSH command. If you don't see anything like that, then your wifi config might have a mistake. You can try to fix with

```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

If you don't have a HDMI monitor and keyboard, you can plug-in the Pi with a CAT5 cable to a router with DHCP.
If that router is on the same network as your PC, you can try:

```bash
ping raspberrypi.local
```

Hopefully, one of those methods worked and you are now ready to SSH into your Pi. On Mac and Linux, you can open Terminal.
On Windows you can install [Putty](http://www.putty.org/), [one of the alternatives](https://www.htpcbeginner.com/best-ssh-clients-windows-putty-alternatives/2/), or on Windows 10 you may have ssh via the command prompt.

If you have a command prompt, you can try:

```bash
ssh pi@raspberrypi.local
```

or

```bash
ssh pi@<your pi ip address>
```

or via Putty.

* Username: `pi`
* Password: `raspberry`
* Hostname: `<your pi IP address>`

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
* enable `Interfacing Options` - `I2C`
* enable `Interfacing Options` - `Camera`
* select `Advanced Options` - `Expand Filesystem` so you can use your whole sd-card storage

Choose `<Finish>` and hit enter.

> Note: Reboot after changing these settings. Should happen if you select `yes`.

## Step 8: Install Dependencies

```bash
sudo apt-get install build-essential python3 python3-dev python3-pip python3-virtualenv python3-numpy python3-picamera python3-pandas python3-rpi.gpio i2c-tools avahi-utils joystick libopenjp2-7-dev libtiff5-dev gfortran libatlas-base-dev libopenblas-dev libhdf5-serial-dev git ntp
```

## Step 9: Optional - Install OpenCV Dependencies

If you are going for a minimal install, you can get by without these. But it can be handy to have OpenCV.

```bash
sudo apt-get install libilmbase-dev libopenexr-dev libgstreamer1.0-dev libjasper-dev libwebp-dev libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev libqtgui4 libqt4-test
```

##  Step 10: Setup Virtual Env

This needs to be done only once:

```bash
python3 -m virtualenv -p python3 env --system-site-packages
echo "source env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```

Modifying your `.bashrc` in this way will automatically enable this environment each time you login. To return to the system python you can type `deactivate`.

##  Step 11: Install Donkeycar Python Code

* Create and change to a directory you would like to use as the head of your projects.

```bash
mkdir projects
cd projects
```

* Get the latest donkeycar from Github.

```bash
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
pip install -e .[pi]
pip install numpy --upgrade
wget "https://raw.githubusercontent.com/PINTO0309/Tensorflow-bin/master/tensorflow-2.3.1-cp37-none-linux_armv7l_download.sh"
chmod u+x tensorflow-2.3.1-cp37-none-linux_armv7l_download.sh
tensorflow-2.3.1-cp37-none-linux_armv7l_download.sh
pip install tensorflow-2.3.1-cp37-none-linux_armv7l.whl
```

You can validate your tensorflow install with

```bash
python -c "import tensorflow"
```

##  Step 12: Optional - Install OpenCV

If you've opted to install the OpenCV dependencies earlier, you can install Python OpenCV bindings now with command:

```bash
sudo apt install python3-opencv
```

If that failed, you can try pip:

```bash
pip install opencv-python
```

Then test to see if import succeeds.

``` bash
python -c "import cv2"
```

And if no errors, you have OpenCV installed!

----

### Next, [create your Donkeycar application](/guide/create_application/).
