# IMU

IMUs or inertial measurement units are parts that sense the inertial forces on a robot. They vary depending on sensor, but may commonly include linear and rotational accelleration. They may sometimes include magnetometer to give global compasss facing dir. Frequently temperature is available from these as it affects their sensitivity.

## MPU6050
This is a cheap, small, and moderately precise imu. Commonly available at [Amazon](https://www.amazon.com/s/ref=nb_sb_noss_2?url=search-alias%3Dindustrial&field-keywords=MPU6050).


* Typically uses the I2C interface and can be chained off the default PWM PCA9685 board. This configuration will also provide power.
* Outputs acceleration X, Y, Z, Gyroscope X, Y, Z, and temperature.
* Chip built-in 16bit AD converter, 16bit data output
* Gyroscopes range: +/- 250 500 1000 2000 degree/sec
* Acceleration range: ±2 ±4 ±8 ±16g

##### Software Setup

Install smbus:

from package:
``` bash
 sudo apt install python3-smbus
```

or from source:

```bash
sudo apt-get install i2c-tools libi2c-dev python-dev python3-dev
git clone https://github.com/pimoroni/py-smbus.git
cd py-smbus/library
python setup.py build
sudo python setup.py install
```

Install pip lib for mpu6050
```bash
pip install mpu6050-raspberrypi
```

