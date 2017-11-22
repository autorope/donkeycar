# Controller Parts

## Local Web Controller

The default controller to drive the car with your phone or browser. This has a web live preview of camera. Control options include:

1. A virtual joystick
2. The tilt, when using a mobile device with supported accelerometer
3. A physical joystick using the web adapter. Support varies per browser, OS, and joystick combination.


## Physical Joystick Controller

The default web controller may be replaced with a one line change to use a physical joystick part for input. This uses the OS device /dev/input/js0 by default. In theory, any joystick device that the OS mounts like this can be used. In practice, the behavior will change depending on the model of joystick ( Sony, or knockoff ), or XBox controller and the Bluetooth driver used to support it. The default code has been written and tested with a [Sony brand PS3 Sixaxis controller](https://www.amazon.com/Dualshock-Wireless-Controller-Charcoal-playstation-3). Other controllers may work, but will require alternative Bluetooth installs, and tweaks to the software for correct axis and buttons.

These can be used plugged in with a USB cable - but the default code and os driver has a bug polling this configuration. It's been much more stable, and convenient, to setup Bluetooth for a wireless, responsive control.

### Change to config.py or run with --js

```
python manage.py drive --js
```

Will enable driving with the joystick. This disables the live preview of the camera and the web page features. If you modify config.py to make USE_JOYSTICK_AS_DEFAULT = True, then you do not need to run with the --js.

### Bluetooth Setup

Follow [this guide](https://pythonhosted.org/triangula/sixaxis.html). You can ignore steps past the 'Accessing the SixAxis from Python' section. I will include steps here in case the link becomes stale.

``` bash
sudo apt-get install bluetooth libbluetooth3 libusb-dev
sudo systemctl enable bluetooth.service
sudo usermod -G bluetooth -a pi
```

Reboot after changing the user group.

Plug in the PS3 with USB cable. Hit center PS logo button. Get and build the command line pairing tool. Run it:

```bash
wget http://www.pabr.org/sixlinux/sixpair.c
gcc -o sixpair sixpair.c -lusb
sudo ./sixpair
```

Use bluetoothctl to pair
```bash
bluetoothctl
agent on
devices
trust <MAC ADDRESS>
default-agent
quit
```

Unplug USB cable. Hit center PS logo button.

To test that the Bluetooth PS3 remote is working, verify that /dev/input/js0 exists.

```bash
ls /dev/input/js0
```

### Charging PS3 Sixaxis Joystick

For some reason, this joystick doesn't like to charge in a powered USB port that doesn't have an active Bluetooth control and OS driver. This means a phone type USB charger will not work, and charging from a Windows machine doesn't work either.

You can always charge from the Raspberry Pi, though.  Just plug the joystick into the Pi and power the Pi using a charger or your PC, and you are good to go.

### New Battery for PS3 Sixaxis Joystick

Sometimes these controllers can be quite old. Here's a link to a [new battery](http://a.co/5k1lbns). Be careful when taking off the cover. Remove 5 screws. There's a tab on the top half between the hand grips. You'll want to split/open it from the front and try pulling the bottom forward as you do, or you'll break the tab off as I did.
