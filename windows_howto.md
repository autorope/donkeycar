3 Manual Setup:
##### This uses minimal space on your memory card, is easy to upgrade and make changes to source

flash 8GB+ memory card with minimal jessie:
* https://downloads.raspberrypi.org/raspbian_lite_latest
* https://sourceforge.net/projects/win32diskimager/files/latest/download


login:
* username: pi
* password: raspberry


use rasp-config to setup some useful options
```bash
sudo raspi-config
```
* change hostname
* change password
* interface options: 
  * enable camera
  * enable SSH
  * enable I2C

reboot.

do a package refresh and get latest:    
```bash
sudo apt-get update
sudo apt-get upgrade
```

install packages from ubuntu
```bash
sudo apt-get install git
sudo apt-get install python3 python3-pip python3-virtualenv
sudo apt-get install python3-pip python3-dev
```

get latest donkey code
```bash
git clone https://github.com/tawnkramer/donkey
cd donkey
```

install anaconda:
```bash
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-armv7l.sh
bash Miniconda3-latest-Linux-armv7l.sh
source ~/.bashrc
```

setup python environment
```bash
conda env create -f donkey_env.yml
source activate donkey
```

upgrade numpy. This can take a long time as it involves compiling the latest.
```bash
pip install --upgrade numpy
```

setup tensorflow
```bash
wget https://github.com/samjabrahams/tensorflow-on-raspberry-pi/releases/download/v1.1.0/tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
pip install tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
```

setup donkey
```
pip install -e .
```

setup initial files and dir for data
```bash
donkey createcar --template donkey2_with_joystick --path ~/d2_wj 
```

to run your donkey with a joystick control
```bash
cd ~/d2_wj
python manage.py drive
```

---

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
conda env create -f win_environment.yml
activate donkey
```

once to setup:
```bash
pip install -e .
donkey createcar --path ~/d2
```

---
# Normal usage
in future runs, when you start a new session, you will want to:
* start a new Anaconda Prompt from windows start menu
* cd projects\donkey
* activate donkey
* cd ~/d2 or ~/d2_js on pi

 

