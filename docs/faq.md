# FAQ 
---------
### How do I create my own Raspberry Pi Disk?

##### This uses minimal space on your memory card, is easy to upgrade and make changes to source

1. [Download raspian lite](https://downloads.raspberrypi.org/raspbian_lite_latest)
2. On Windows, [download disk imager](https://sourceforge.net/projects/win32diskimager/files/latest/download)
3. On Mac or Linux, [download Etcher](https://etcher.io)
4. Follow instructions to burn image to memory card.:
      * Win32DiskImager [video](https://www.youtube.com/watch?v=SdWr-aolCSA) 
      * Win32DiskImager [writeup](https://codeyarns.com/2013/06/21/how-to-write-a-disk-image-using-win32-disk-imager/)
      * Etcher [video](https://www.youtube.com/watch?v=I6F2HoTeiFc)
      * Etcher [writeup](https://www.raspberrypi.org/magpi/pi-sd-etcher/)
      * Multiple methods [writeup](http://elinux.org/RPi_Easy_SD_Card_Setup)
5. Place memory card in Pi and boot
6. After booting, you will see a prompt. Login. type ```pi``` for username.
7. Type ```raspberry``` for password.
8. use raspi-config to setup some useful options:
    ```sudo raspi-config```
    * change hostname
    * change password
    * interface options: 
        * enable camera
        * enable SSH
        * enable I2C
9. Reboot.
10. Do a package refresh and get latest:
    ```bash
    sudo apt-get update
    sudo apt-get upgrade
    ```
11. install packages:
    ```bash
    sudo apt-get install git
    sudo apt-get install python3 python3-pip python3-virtualenv
    sudo apt-get install python3-pip python3-dev
    ```

12. Get latest donkey code:
    ```bash
    git clone https://github.com/wroscoe/donkey
    cd donkey
    ```

13. Install anaconda:
    ```bash
    wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-armv7l.sh
    bash Miniconda3-latest-Linux-armv7l.sh
    source ~/.bashrc
    ```

14. Setup python environment:
    ```bash
    conda env create -f envs/rpi.yml
    source activate donkey
    ```

15. Upgrade numpy. This can take a long time as it involves compiling the latest.
    ```bash
    pip install --upgrade numpy
    ```

16. Setup tensorflow:
    ```bash
    wget https://github.com/samjabrahams/tensorflow-on-raspberry-pi/releases/download/v1.1.0/tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
    pip install tensorflow-1.1.0-cp34-cp34m-linux_armv7l.whl
    ```

17. Setup donkey
    ```
    pip install -e .
    ```

18. Setup initial files and dir for data. Refer to [setup instructions](guide/install_software.md) for options.
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

2. Occasionally also the template files have changed with fixes that affect manage.py. You can create a new user directory to test. Use the same options you used to create it [from setup instructs](guide/install_software.md) but a new path. For instance:
    ```
    donkey createcar --path ~/d2_new
    ```

---