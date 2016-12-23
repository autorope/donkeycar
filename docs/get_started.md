# Get Started
This doc will walk you through how to setup your donkey.


## Bill of Materials.
#### Required
* Raspberry Pi 3 B ($35)
* Raspberry Pi Camera ($15)
* Micro USB power adapter. ($9)
* USB Battery Pack ($15)
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

6. Install Jupyter
	```
	sudo pip3 install jupyter notebook
	```

#### Install your Camera
Follow the instructions [here](https://www.raspberrypi.org/learning/getting-started-with-picamera/worksheet/).


1. Connect your camera to the RPi.
2. Enable your camera in the Menu > Preferences > Raspberry Pi Config 
3. Restart your Pi. `sudo reboot`


#### Connect your servo sheild. 

Not sure how to do this yet. 


#### Install Donkey


clone repo & create virtual env

```
mkdir code
cd code
git clone http://github.com/wroscoe/donkey.git
cd donkey
virtualenv --system-site-packages -p python3 env 
source env/bin/activate
pip install -r requirements.txt
```


#### Connect to your donkey remotely.

Find the ip address of your Pi.
* If you have you have your monitor and keyboard connected to your Pi:
   1. Open terminal.
   2. Type `ifconfig`

* If there is no monitor connected to your Pi but your computer is connected to the same wireless network as your Pi.  
   1. Open a terminal.
   2. Find your own Ip address by typing `ifconfig'
   3. Search for your Pi's address with the command: 
   	```
    sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'
    ```
