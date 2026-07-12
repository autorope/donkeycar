#!/usr/bin/env python3
import time

SENSOR_MPU6050 = 'mpu6050'
SENSOR_MPU9250 = 'mpu9250'

DLP_SETTING_DISABLED = 0
CONFIG_REGISTER = 0x1A


class IMU:
    '''
    Installation:

    - MPU6050
    sudo apt install python3-smbus
    or
    sudo apt-get install i2c-tools libi2c-dev python-dev python3-dev
    git clone https://github.com/pimoroni/py-smbus.git
    cd py-smbus/library
    python setup.py build
    sudo python setup.py install

    pip install mpu6050-raspberrypi

    - MPU9250
    pip install mpu9250-jmdev

    '''

    def __init__(self, addr=0x68, poll_delay=0.0166, sensor=SENSOR_MPU6050, dlp_setting=DLP_SETTING_DISABLED):
        self.sensortype = sensor
        if self.sensortype == SENSOR_MPU6050:
            from mpu6050 import mpu6050 as MPU6050
            self.sensor = MPU6050(addr)

            if (dlp_setting > 0):
                self.sensor.bus.write_byte_data(self.sensor.address, CONFIG_REGISTER, dlp_setting)

        else:
            from mpu9250_jmdev.registers import AK8963_ADDRESS, GFS_1000, AFS_4G, AK8963_BIT_16, AK8963_MODE_C100HZ
            from mpu9250_jmdev.mpu_9250 import MPU9250

            self.sensor = MPU9250(
                address_ak=AK8963_ADDRESS,
                address_mpu_master=addr,  # In 0x68 Address
                address_mpu_slave=None,
                bus=1,
                gfs=GFS_1000,
                afs=AFS_4G,
                mfs=AK8963_BIT_16,
                mode=AK8963_MODE_C100HZ)

            if (dlp_setting > 0):
                self.sensor.writeSlave(CONFIG_REGISTER, dlp_setting)
            self.sensor.calibrateMPU6500()
            self.sensor.configure()

        # self.accel = {'x': 0., 'y': 0., 'z': 0.}
        # self.gyro = {'x': 0., 'y': 0., 'z': 0.}
        # self.quat = {'i': 0., 'j': 0., 'k': 0., 'real': 0.}
        self.accel = (0., 0., 0.)
        self.gyro = (0., 0., 0.)
        self.quat = (0., 0., 0., 0.)
        self.poll_delay = poll_delay
        self.on = True

    def update(self):
        while self.on:
            self.poll()
            time.sleep(self.poll_delay)

    def poll(self):
        try:
            if self.sensortype == SENSOR_MPU6050:
                self.accel, self.gyro, self.temp = self.sensor.get_all_data()
            else:
                from mpu9250_jmdev.registers import GRAVITY
                ret = self.sensor.getAllData()
                self.accel = (ret[1] * GRAVITY, ret[2] * GRAVITY, ret[3] * GRAVITY)
                self.gyro = (ret[4], ret[5], ret[6])
                self.mag = (ret[13], ret[14], ret[15])
                self.temp = ret[16]
        except:
            print('failed to read imu!!')

    def run_threaded(self):
        return self.accel, self.gyro, self.temp

    def run(self):
        self.poll()
        return self.accel, self.gyro, self.temp

    def shutdown(self):
        self.on = False


class Bno08xIMU:
    """
    Installation:
    pip install adafruit-circuitpython-bno08x
    """

    def __init__(self, poll_delay=0.0166, addr=0x4A):
        import board
        import busio
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_bno08x import BNO_REPORT_ACCELEROMETER, BNO_REPORT_GYROSCOPE, BNO_REPORT_ROTATION_VECTOR

        # Initialize I2C bus
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = BNO08X_I2C(self.i2c, address=addr)

        # Explicitly enable the streams needed for navigation and fusion
        self.sensor.enable_feature(BNO_REPORT_ACCELEROMETER)
        self.sensor.enable_feature(BNO_REPORT_GYROSCOPE)
        self.sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)

        # self.accel = {'x': 0., 'y': 0., 'z': 0.}
        # self.gyro = {'x': 0., 'y': 0., 'z': 0.}
        # self.quat = {'i': 0., 'j': 0., 'k': 0., 'real': 0.}
        self.accel = (0., 0., 0.)
        self.gyro = (0., 0., 0.)
        self.quat = (0., 0., 0., 0.)
        self.poll_delay = poll_delay
        self.on = True

    def update(self):
        import time
        while self.on:
            self.poll()
            time.sleep(self.poll_delay)

    def poll(self):
        try:
            ax, ay, az = self.sensor.acceleration
            self.accel = (ax, ay, az)

            gx, gy, gz = self.sensor.gyro
            self.gyro = (gx, gy, gz)

            # Quaternions are ideal for avoiding gimbal lock during fusion
            qi, qj, qk, qr = self.sensor.quaternion
            self.quat = (qi, qj, qk, qr)
        except Exception as e:
            print(f"Failed to read BNO08x: {e}")

    # Instead of returning flat scalars:
    # return self.accel['x'], self.accel['y'], self.accel['z'], self.gyro['x'] ...

    def run_threaded(self):
        accel = self.accel  # (ax, ay, az)
        gyro = self.gyro  # (gx, gy, gz)
        
        # If using the BNO08x, include the quaternion tuple as well
        if hasattr(self, 'quat'):
            quat = self.quat  # (qi, qj, qk, qr)
            return accel, gyro, quat
            
        return accel, gyro, self.temp

    def run(self):
        self.poll()
        return self.run_threaded()

    def shutdown(self):
        self.on = False


if __name__ == "__main__":
    iter = 0
    import sys

    sensor_type = SENSOR_MPU6050
    dlp_setting = DLP_SETTING_DISABLED
    if len(sys.argv) > 1:
        sensor_type = sys.argv[1]
    if len(sys.argv) > 2:
        dlp_setting = int(sys.argv[2])

    if sensor_type.lower() == 'bno08x':
        p = Bno08xIMU()
    else:
        p = IMU(sensor=sensor_type)

    while iter < 100:
        data = p.run()
        print(data)
        time.sleep(0.1)
        iter += 1

