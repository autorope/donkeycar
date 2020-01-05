# OLED Displays

OLED displays can be used to show information about the current state of the car. This is especially useful in the when collecting data for training, and when racing. 

The OLED display currently displays the following information:
* The IP address of the car (`eth` and `wlan`)
* The number of records collected, for training.
* The driving mode (also as icon on 128x64 displays)

## Supported displays

The display part supports following display types using I2C communication:
* 0.91" with 128x32 pixel resolution ([example](https://www.adafruit.com/product/3527))
* 0.96" with 128x64 pixel resolution ([example](https://www.adafruit.com/product/938))

## Hardware Setup

Simply connect the display to the I2C pins on the Raspberry Pi or the Jetson Nano. Use `bus 1` so the display can be inserted directly on the pins. [Here](https://cdn-shop.adafruit.com/1200x900/3527-04.jpg) is an example of what that looks like.

## Software Setup

Enable the display in `myconfig.py`.

```python
#SSD1306_OLED_DISPLAY
SSD1306_USE_DISPLAY = False            #enable the display
SSD1306_WIDTH = 128                    #display width in pixel
SSD1306_HEIGHT = 32                    #display height in pixel
SSD1306_WLAN_INTERFACE_NAME = "wlan0"  #wlan interface name
SSD1306_ETH_INTERFACE_NAME = "eth0"    #ethernet interface name
SSD1306_I2C_ADDR = 0x3C                #I2C address
SSD1306_I2C_BUSNUM = None              #none will auto detect
SSD1306_PROCESS_LIMIT = 32             #number of display commands per thread cycle
```

## Troubleshooting

* If the display does not show something, use the tool `i2cdetect` to check of the display appears as a I2C device in Linux(usually with the address 0x3C). Check the wiring first to make sure, that the display is connected correctly to your compute board. If the display does not show up then, set the SSD1306_I2C_BUSNUM from _None_ (auto detect - known to work on Raspberry Pi 3+ and 4) to _1_ (known to work on Jetson Nano.)
* To get the name of your network interfaces use the tool `ifconfig` on Linux.
* To get faster display updates increase the value of _SSD1306_PROCESS_LIMIT_ variable.
* If you use I2C communication to control your servos using a PCA6985 controller and you observe slow servo and ESC reactions while the display updates, decrease the value _SSD1306_PROCESS_LIMIT_.
* Also consider decreasing the value of _SSD1306_PROCESS_LIMIT_, to reduce CPU time usage for display updates
