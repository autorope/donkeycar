# FAQ 
---------
### How do I create my own Raspberry Pi Disk?

##### This uses minimal space on your memory card, is easy to upgrade and make changes to source

* [Download raspian lite](https://downloads.raspberrypi.org/raspbian_lite_latest)
* On Windows, [download disk imager](https://sourceforge.net/projects/win32diskimager/files/latest/download)
* On Mac or Linux, [download Etcher](https://etcher.io)
* Follow instructions to burn image to memory card.:
      * Win32DiskImager [video](https://www.youtube.com/watch?v=SdWr-aolCSA) 
      * Win32DiskImager [writeup](https://codeyarns.com/2013/06/21/how-to-write-a-disk-image-using-win32-disk-imager/)
      * Etcher [video](https://www.youtube.com/watch?v=I6F2HoTeiFc)
      * Etcher [writeup](https://www.raspberrypi.org/magpi/pi-sd-etcher/)
      * Multiple methods [writeup](http://elinux.org/RPi_Easy_SD_Card_Setup)
* Place memory card in Pi and boot

* After booting, you will see a prompt. Login. type ```pi``` for username.

* Type ```raspberry``` for password.

* Use raspi-config to setup some useful options:
    `sudo raspi-config`
    * change hostname
    * change password
    * interface options: 
        * enable camera
        * enable SSH
        * enable I2C

* Reboot.

* Do a package refresh and get latest:
``` bash
sudo apt-get update
sudo apt-get upgrade
```

* Install packages:

``` bash
sudo apt-get install git
sudo apt-get install python3 python3-pip python3-virtualenv python3-dev virtualenv
sudo apt-get install build-essential gfortran libhdf5-dev
```

* Get latest donkey code:

``` bash
git clone https://github.com/wroscoe/donkey
cd donkey
```

* Install anaconda:

``` bash
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-armv7l.sh
bash Miniconda3-latest-Linux-armv7l.sh
source ~/.bashrc
```

* Setup python environment

``` bash
conda env create -f envs/rpi.yml
source activate donkey
```


* Upgrade numpy. This can take a long time as it involves compiling the latest.

``` bash
pip install --upgrade numpy
```

* Setup tensorflow:

``` bash
wget https://github.com/samjabrahams/tensorflow-on-raspberry-pi/releases/download/v1.1.0/tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
pip install tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
```

* Setup donkey

``` bash
pip install -e .
```

* Setup initial files and dir for data. Refer to [Get Driving](guide/get_driving.md) for options.


---
## After a reboot, I don't see the (donkey) in front of the prompt, and I get python errors when I run.
1. If you used this disc setup guide above, you used conda to manage your virtual environment. You need to activate the donkey conda environment with:
    ```
    source activate donkey
    ```
2. optionally you can add that line to the last line of your ~/.bashrc to have it active each time you login.

----
## How to get latest Donkey source
1. When donkey has changed you can get the latest source. You've installed it directly from the github repo, so getting latest is easy:
     ```
    cd donkey
    git pull origin master
    ```

2. Occasionally also the template files have changed with fixes that affect manage.py. You can create a new user directory to test. Use the same options you used to create it [from setup instructions](guide/install_software.md) but a new path. For instance:
    ```
    donkey createcar --path ~/d2_new
    ```

---