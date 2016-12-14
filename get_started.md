# Get Started
This doc will walk you through how to setup your donkey.


## Bill of Materials.
#### Required
* Raspberry Pi 3 B ($35)
* Micro USB power adapter. ($9)
* USB Keyboard 
* USB Mouse
* Monitor 
* HDMI cable (to connect monitor to PI) ($7)
* Micro SD Card (campatible with Raspberry Pi) ($8)
* Servo Sheild ($15)
* RC CAR (($120-300))

#### Optional
* Xbox 360 Controller
* Xbox USB Adapter



## Setup
These instructions are based on [Geoff Boeing's post on setting up scientific python on a Raspberry Pi](http://geoffboeing.com/2016/03/scientific-python-raspberry-pi/).

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