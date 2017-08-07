
# pi3, manual setup:

flash 8GB memory card with minimal jessie:
https://downloads.raspberrypi.org/raspbian_lite_latest
https://sourceforge.net/projects/win32diskimager/files/latest/download


login:
username: pi
password: raspberry

```bash
sudo raspi-config
```

change hostname
change password
5 interface options: 
    P1 enable camera
    P2 enable SSH
    P5 enable I2C
    
```bash
sudo apt-get update --fix-missing
sudo apt-get upgrade
```

```bash
sudo apt-get install git
sudo apt-get install python3 python3-pip python3-virtualenv
sudo apt-get install python3-pip python3-dev
```

```bash
git clone https://github.com/tawnkramer/donkey
cd donkey
```

install anaconda:
```bash
#wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-armv7l.sh
bash Miniconda3-latest-Linux-armv7l.sh
```

setup python environment
```bash
conda env create -f pi_environment.yml
source activate donkey
python setup.py install
```

setup tensorflow
```bash
wget https://github.com/samjabrahams/tensorflow-on-raspberry-pi/releases/download/v1.1.0/tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
pip install tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
```
this can take a long time as it involves compiling the latest numpy.





# windows setup:

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
```

```bash
cd donkey
conda env create -f environment.yml
activate donkey
```

once to setup:
```bash
python make_paths.py
python setup.py install
```

to run server:
```bash
python scripts/serve.py
```


 

