import PyLidar3
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


port = result[0] #linux
Obj = PyLidar3.YdLidarX4(port) #PyLidar3.your_version_of_lidar(port,chunk_size) 
if(Obj.Connect()):
    print(Obj.GetDeviceInfo())
    gen = Obj.StartScanning()
    t = time.time() # start time 
    while (time.time() - t) < 30: #scan for 30 seconds
        print(next(gen))
        time.sleep(0.5)
    Obj.StopScanning()
    Obj.Disconnect()
else:
    print("Error connecting to device")