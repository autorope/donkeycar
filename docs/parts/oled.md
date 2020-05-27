# OLED Displays

OLED displays can be used to show information about the current state of the car. This is especially useful in the when collecting data for training, and when racing. 

The OLED display currently displays the following information:
* The IP address of the car (`eth` and `wlan`)
* The number of records collected, for training.
* The driving mode.

## Supported displays

Examples of displays that are currently supported are:

* [Adafruit PiOLED - 128X32 MonoChrome OLED](https://www.adafruit.com/product/3527)

## Hardware Setup

Simply connect the display to the I2C pins on the Raspberry Pi or the Jetson Nano. Use `bus 1` so the display can be inserted directly on the pins. [Here](https://cdn-shop.adafruit.com/1200x900/3527-04.jpg) is an example of what that looks like.

## Software Setup

Enable the display in `myconfig.py`.

```python
# SSD1306_128_32
USE_SSD1306_128_32 = True     # Enable the SSD_1306 OLED Display
SSD1306_128_32_I2C_BUSNUM = 1 # I2C bus number
```

## Troubleshooting

If you are unable to start the car, ensure that the `Adafruit_SSD1306` package is installed in your virtual environment. This should automatically be installed, if you are using a recent version of `donkeycar`.

```bash
pip install Adafruit_SSD1306
```
