
import serial
import time
from donkeycar.parts.lidar import RPlidar, YDlidar

port = '/dev/ttyUSB0'
lasttime = time.time()


def read_lidar(port):
    global lasttime2
    angle, distance = YDlidar.update(debug = True)
    print("angle", angle)
    print("distance", distance)
    lasttime2 = time.time()


while True:
    read_lidar(port)