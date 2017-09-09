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

```
virtualenv env -p python3
source env/bin/activate
git clone https://github.com/wroscoe/donkey donkeycar
pip install -e donkeycar
donkeycar findcar
```

This will show your ip address, promt for your password, and then search 
for your cars ip address. 

> If your car's ip address is not shown then:
> 1. find another way to scan your local network for your raspbery pi 
> 2. connect a monitor to your pi to connect to the the same wifi as your computer. 


Assuming that you did find your pi on the network. You can now connect to it
remotely via ssh. 

```
ssh pi@<your_pi_ip_address>
```

The default username is 'pi' and the password is 'raspberry'


### Create your car application.

#### with web browser.
```
donkey createcar --template donkey2 --path ~/d2
```


#### with PS3 controller
```
donkey createcar --template donkey2_with_joystick --path ~/d2_wj
```



#### Install another fork of donkeycar

``` 
pip uninstall donkeycar
git clone --depth=1 https://github.com/tawnkramer/donkey donkey_tkramer
cd donkey_tkramer
pip install -e .
```
