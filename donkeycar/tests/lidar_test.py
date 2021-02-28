from rplidar import RPLidar
import time
import serial

import glob
import time # Time module
temp_list = glob.glob ('/dev/ttyUSB*')
result = []
for a_port in temp_list:
    try:
        s = serial.Serial(a_port)
        s.close()
        result.append(a_port)
    except serial.SerialException:
        pass
print("available ports", result)
lidar = RPLidar(result[0], baudrate=115200)

info = lidar.get_info()
print(info)

health = lidar.get_health()
print(health)

for i, scan in enumerate(lidar.iter_scans()):
    print('%d: Got %d measurments' % (i, len(scan)))
    if i > 10:
        break

lidar.stop()
lidar.stop_motor()
lidar.disconnect()
