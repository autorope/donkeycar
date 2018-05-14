# FAQ
---------

### What types of RC cars work with the donkey platform?
Most hobby grade RC cars will work fine with the electronics but you'll need to make your own baseplate and camera
holder. To make sure the car will work with Donkey check theses things.

* it has a separate ESC and reciever. Some of the cheaper cars have these combined so it would require soldering to
connect the Donkey motor controller to the ESC.
* The ESC uses three-wire connectors. This will make it easy to just plug into the Donkey hardware.
* Brushed motors are easier because they can go slower but brushless motors can work as well.

For more information, see [Roll Your Own](/roll_your_own.md).

### What car can I use if I'm not in the USA?
The easiest thing to do would be to take your parts down to your local RC / hobby shop and check that the car you want
works with the parts. Here are some parts people have said work in other countries.

* Austrailia: [KAOS](https://www.hobbywarehouse.com.au/hsp-94186-18694k-kaos-blue-rc-truck.html) (functionally equivalent to the Exceed Magnet)
* China: [HSP 94186](https://item.taobao.com/item.htm?spm=a1z02.1.2016030118.d2016038.314a2de7XhDszO&id=27037536775&scm=1007.10157.81291.100200300000000&pvid=dd956496-2837-41c8-be44-ecbcf48f1eac) (functionally equivalent to the Exceed Magnet)
* Add your country to this list (click edit this in top left corner)


### How can I make my own track?
You can use tape, ribbon or even rope. The most popular tracks are 4ft wide and have 2in white borders with a dashed
yellow center line. The Oakland track is about 70 feet around the center line. Key race characteristics include:
* straightaways.
* left and right turns
* hairpin turn
* start/finish line.


### Will Donkey Work on different hardware?
Yes. It's all python so you can run it on any system. Usually the hard part of porting Donkey will be getting the hardware working.
Here are a couple systems that people have tried or talked about.

* NVIDA TX2 - This was implemented with a webcam and used a teensy to controll the motor/servos.
* Pi-Zero - Untested but people have gotten OpenCV and Tensorflow installed so it seems possible.



### How do I create my own Raspberry Pi Disk?
This requires an extra 4 hours when command.

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
