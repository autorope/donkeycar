# Build a Donkey Vehicle

With donkey, you can build angle steering or differential steering vehicles. This document walks through how to build both types.

#### Steps
1. [Get Parts](#1.-get-parts)
2. [Setup Raspbery Pi](#2.-setup-raspberry-pi) (30 min)
3. [Install Pi Camera](#3.-install-pi-camera) (15 min)
4. [Solder and install motor shield](#4.-solder-and-install-motor-shield) (30 min) 
5. [Install Donkey](#5.-install-donkey)
6. [Assemble vehicle](#6.-assemble-vehicle) (2 hr)
7. Drive your vehicle.  (30 min)
8. Train an autopilot.  (30 min)
9. Load autopilot to drive car.  (15 min)


### 1. Get Parts 

#### Components
* [Raspberry Pi 3 B](https://www.raspberrypi.org/products/raspberry-pi-3-model-b/) ($35)
* [Micro SD Card](https://www.sandisk.com/home/memory-cards/microsd-cards/extreme-microsd) (campatible with Raspberry Pi) ($8)
* [Raspberry Pi Camera V2](https://www.raspberrypi.org/products/camera-module-v2/) ($15)
* [Adafruit Servo Sheild](https://www.adafruit.com/product/1411) ($22)
* [USB Battery Pack](https://www.anker.com/products/A1263011) ($15)
* RC CAR (($120-300)) (car recommendations)

**[Amazon.com Shopping List](https://www.amazon.com/gp/registry/giftlist/6XBNF1EGH97Q/ref=nav_wishlist_lists_4)**

#### Custom Parts
These parts can be made using a 3D printer and laser cutter. ***If you don't have access to these tools you can build these components out of cardboard or foamboard.***
* Camera mount
* Base plate
* Roll bars 

#### Tools Needed
* Monitor with HDMI connector
* USB Mouse
* USB Keyboard
* Soldering Iron 

 



### 2. Setup Raspberry Pi
This doc will walk you through how make an RC car that can autonomousy folow lines, lanes and sidewalks. 


#### Boot your Raspberry Pi
These instructions assume you're using Ubuntu operationg system. If you don't have Ubuntu, try using the NOOB method.

1. Download recent Disk image. I use Jessie.
2. Extract disk image from zip file. 
3. Open Ubuntu's  "Startup Disk Creator" application. 
4. Insert micro usb disk via a usb adapter. This disk should show up in the Startup Disk Creator app. 
5. Select your RPi .img file and click create disk. 
6. Once the img has been created, take the SD card from your computer and put it in your RPi.
7.  Connect your Monitor with your HDMI cable, your mouse and keyboard and then finally power up the RPi by plugging in the Micro USB power adaptor. 


#### Install Basic Libraries
Since the RPi is not as powerful as a laptop, it can take a long time to install python packages (ie. numpy & PIL) using pip. Luckly Adafruit has precompiled these libraries into packages that can be installed via `apt-get`.


1. Open a terminal (Ctrl-Alt-t) and upgrade your system packages.

	```
	sudo apt-get update
	sudo apt-get upgrade
	```
2. Save These initial conditions.

	```
	dpkg -l > ~/Desktop/packages.list
	pip freeze > ~/Desktop/pip-freeze-initial.list
	```

3. Install the necessary libraries 

	```
	sudo apt-get install xsel xclip libxml2-dev libxslt-dev libzmq-dev libspatialindex-dev virtualenv
	```
4. Pandas & Jupyter Requirements
	```
	sudo apt-get install python3-lxml python3-h5py python3-numexpr python3-dateutil python3-tz python3-bs4 python3-xlrd python3-tables python3-sqlalchemy python3-xlsxwriter python3-httplib2 python3-zmq 
	```
5. Scientific Python
	```
	sudo apt-get install python3-numpy python3-matplotlib python3-scipy python3-pandas 
	```

### 3. Install Pi Camera
Follow the instructions [here](https://www.raspberrypi.org/learning/getting-started-with-picamera/worksheet/).


1. Connect your camera to the RPi.
2. Enable your camera in the Menu > Preferences > Raspberry Pi Config 
3. Restart your Pi. `sudo reboot`


###4. Solder and Install Motor Sheild

1. Assemble and test your servo shield with the instructions given by Adafruit. 



###5. Install Donkey


clone repo & create virtual env

```
mkdir code
cd code
git clone http://github.com/wroscoe/donkey.git

mkdir car
cd car
virtualenv --system-site-packages -p python3 env 
source env/bin/activate
pip install -e ../donkey[pi]
```


###6. Assemble Vehicle

This section explains how to create the custom structural components for your vehicle and use them to securely attach your camera, pi and battery.

#### Create Custom Parts
1. **Base Plate** The base plate is the structural member that provides a flat surface to attach the Pi, battery and camera.
2. **Camera Mount** The camera mount holds the Pi Camera at the correct height and angle. 
3. **Roll Bars** Protective bars to prevent damage to your camera and electronics. 



## Differential Steering Vehicle (slow)