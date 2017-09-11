# Controller Parts

## Local Web Controller

The default controller to drive the car with your phone or browser.


## PS3 Joystick

### Setup:

Follow [this guide](https://pythonhosted.org/triangula/sixaxis.html). You can ignore steps past the 'Accessing the SixAxis from Python' section.

Be sure to reboot after changing user group.

To test that the Bluetooth PS3 remote is working, verify that /dev/input/js0 exists.

```bash
ls /dev/input/js0
```

### Charging PS3 Sixaxis joystick

For some reason, they don't like to charge in a powered usb port that doesn't have an active bluetooth control and os driver. So a phone type usb charger won't work. Try a powered linux or mac laptop usb port. You should see the lights blink after plugging in and hitting center PS logo.

### New Battery for PS3 Sixaxis joystick

Sometimes these controllers can be quite old. Here's a link to a [new battery](http://a.co/5k1lbns). Be careful when taking off the cover. Remove 5 screws. There's a tab on the top half between the hand grips. You'll want to split/open it from the front and try pulling the bottom forward as you do. Or you'll break the tab off as I did.