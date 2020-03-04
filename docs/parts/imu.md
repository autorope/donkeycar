# IMU

IMUs or inertial measurement units are parts that sense the inertial forces on a robot. They vary depending on sensor, but may commonly include linear and rotational accelleration. They may sometimes include magnetometer to give global compasss facing dir. Frequently temperature is available from these as it affects their sensitivity.

## MPU6050/MPU9250

This is a cheap, small, and moderately precise imu. Commonly available at [Amazon](https://www.amazon.com/s/ref=nb_sb_noss_2?url=search-alias%3Dindustrial&field-keywords=MPU6050).

MPU9250 offers additional integrated magnetometer.

* Typically uses the I2C interface and can be chained off the default PWM PCA9685 board. This configuration will also provide power.
* MPU6050: Outputs acceleration X, Y, Z, Gyroscope X, Y, Z, and temperature.
* MPU6250: Outputs acceleration X, Y, Z, Gyroscope X, Y, Z, Magnetometer X, Y, Z and temperature.
* Chip built-in 16bit AD converter, 16bit data output
* Gyroscopes range: +/- 250 500 1000 2000 degree/sec
* Acceleration range: ±2 ±4 ±8 ±16g

### Software Setup

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
For MPU6050: 

Install pip lib for `mpu6050`:

```bash
pip install mpu6050-raspberrypi
```

For MPU9250: 

Install pip lib for `mpu9250-jmdev`:

```bash
pip install mpu9250-jmdev
```

### Configuration
Enable the following configurations to your `myconfig.py`:

``` python
#IMU
HAVE_IMU = True
IMU_SENSOR = 'mpu9250'          # (mpu6050|mpu9250)
IMU_DLP_CONFIG = 3
```
`IMU_SENSOR` can be either `mpu6050` or `mpu9250` based on the sensor you are using.

`IMU_DLP_CONFIG` allows to change the digital lowpass filter settings for your IMU. Lower frequency settings (see below) can filter high frequency noise at the expense of increased latency in IMU sensor data.
Valid settings are from 0 to 6:

- `0` 250Hz
- `1` 184Hz
- `2` 92Hz
- `3` 41Hz
- `4` 20Hz 
- `5` 10Hz
- `6` 5Hz

### Notes on MPU9250
At startup the MPU9250 driver performs calibration to zero accel and gyro bias. Usually the process takes less than 10 seconds, and in that time avoid moving or touching the car.
Please place the car on the ground before starting Donkey 
