Install PS3 controller on a RPi3
References for this information was found here:

https://github.com/RetroPie/RetroPie-Setup/wiki/PS3-Controller

https://github.com/RetroPie/RetroPie-Setup/issues/1128



Install all the dependencies:
```bash
sudo apt-get install bluetooth blueman bluez-hcidump checkinstall libusb-dev libbluetooth-dev joystick pkg-config
```

Connect the PS3 remote to the RPI3 with the USB cable

Check to see if we can see the PS3
```bash
hciconfig
hci0: Type: BR/EDR Bus: USB
 BD Address: 00:1F:81:00:06:20 ACL MTU: 1021:4 SCO MTU: 180:1
UP RUNNING PSCAN
RX bytes:1260 acl:0 sco:0 events:46 errors:0
TX bytes:452 acl:0 sco:0 commands:45 errors:0
```

Download an application to pair the PS3 remote to the RPI3


```bash
wget http://www.pabr.org/sixlinux/sixpair.c
gcc -o sixpair sixpair.c -lusb
```

Connect the PS3 remote to the RPI3 with the USB cable.

Now run the pair to see pair it with the RPI3
Run the command:
```bash
sudo ./sixpair
```

This should show something like:
```bash
Current Bluetooth master: DE:AD:BE:EF:00:00
Setting master bd_addr to: 00:1F:81:00:06:20 
```

If you do not see this, then reboot, and try again to run the applicaiton.


Now we need to install the application to use the PS3 controller through Bluetooth on /dev/input/js0
 

```
git clone https://github.com/supertypo/qtsixa.git
cd QtSixA-1.5.1/sixad
make
sudo mkdir -p /var/lib/sixad/profiles
sudo checkinstall
```

It will ask you for a summary.  I just put "PS3 Controller".


```bash
sudo sixad --start
```
When it displays its searching, press the PS Button and your golden~!)

RUN THIS APPLICATION AT START TO GET THE BLUETOOTH REMOTE TO WORK.


To install this application as a process that will run at startup:
```bash
sudo update-rc.d sixad defaults
reboot
```
This did not work for me yet.

To test that the Bluetooth PS3 remote is working, verify that /dev/input/js0 exist.

You can also run this application to view the output.
```bash
sudo jstest /dev/input/js0
```