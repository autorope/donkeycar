# Install Software

### Get the Raspberry Pi working.

Before we can do anything we have to get our car's computer connected to the 
internet. The fastest way is to use the disk image created for donkey cars. 

The method for using a disk image to create a bootable SD card varies between
operating systems. These instructions are for Ubuntu but you can see more 
instructions [here](https://www.raspberrypi.org/documentation/installation/installing-images/).

1. Download [zipped disk image](https://www.dropbox.com/s/vb9wlju4aqx7i5o/donkey_2.img.zip?dl=0) (900MB). 
2. Unzip the disk image.
3. Plug your SD card into your computer.
4. Open the "Startup Disk Creator" application.
5. Select your source disk image as the one you unzipped earlier.
6. Select your SD card as the disk to use. 
7. Click "Make startup disk".


Since our pi doesn't have a monitor/keyboard/mouse let's setup the pi's wifi
now.

1. start a text editor with root privelidges ie. `sudo gedit`
2. Open the file `/etc/wpa_supplicant/wpa_supplicant.conf` in the text editor
and edit the wifi credentials to your wifi settings.

Now you're SD card is ready. Eject it from your computer, put it in the Pi 
and plug in the Pi. 



### Connecting to the Pi

If you followed the above instructions to add wifi access you're Pi should
now be connected to your wifi network. Now you need to find it's IP address
so you can connect to it via SSH. 

> Note: If you didn't setup the wifi earlier you'll need to attach a monitor,
> keyboard and mouse so you can log setup the wifi via the command line. 

The easiest way (on Ubuntu) is to use the `findcar` donkey command. Regardless 
you will wand donkeycar installed on your computer for training so lets install
donkeycar now. 

#### Install donkeycar on Linux

```
virtualenv env -p python3
source env/bin/activate
git clone https://github.com/wroscoe/donkey donkeycar
pip install -e donkeycar
```

# Windows Donkey Setup
##### Many python projects do not provide a docker install. It's useful to know how to setup the windows environment to run Donkey and/or any other python project. Its also easier to modify source.

install miniconda:
https://conda.io/miniconda.html

install git:
https://git-scm.com/download/win
use the setup for your platform. probably 64bit

from the start menu start the Andconda Prompt.

change to a dir you would like to use as the head of your projects.
```bash
mkdir projects
cd projects
```

get the latest donkey from my repo. This has fixes to run correctly on windows.
```bash
git clone https://github.com/tawnkramer/donkey
cd donkey
```

create the python anaconda environmment
```bash
conda env create -f envs\windows.yml
activate donkey
```

once to setup:
```bash
pip install -e .
donkey createcar --path ~/d2
```



#### Install another fork of donkeycar

``` 
pip uninstall donkeycar
git clone --depth=1 https://github.com/tawnkramer/donkey donkey_tkramer
cd donkey_tkramer
pip install -e .
```
