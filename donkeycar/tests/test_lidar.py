import pytest


def has_lidar():
    """ Determine if test platform (nano, pi) has lidar"""
    # for now just return false, better to use an environ
    return False


@pytest.mark.skipif(not has_lidar(), reason='Need lidar installed')
def test_rp_lidar():
    from rplidar import RPLidar
    import serial
    import glob

    temp_list = glob.glob('/dev/ttyUSB*')
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
        print(f'{i}: Got {len(scan)} measurements')
        if i > 10:
            break

    lidar.stop()
    lidar.stop_motor()
    lidar.disconnect()


@pytest.mark.skipif(not has_lidar(), reason='Need lidar installed')
def test_py_lidar3():
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

    port = result[0]  # linux
    # PyLidar3.your_version_of_lidar(port,chunk_size)
    ydlidar = PyLidar3.YdLidarX4(port)
    if ydlidar.Connect():
        print(ydlidar.GetDeviceInfo())
        gen = ydlidar.StartScanning()
        t = time.time() # start time
        while (time.time() - t) < 30:  # scan for 30 seconds
            print(next(gen))
            time.sleep(0.5)
        ydlidar.StopScanning()
        ydlidar.Disconnect()
    else:
        print("Error connecting to device")


@pytest.mark.skipif(not has_lidar(), reason='Need lidar installed')
def test_simple_express_scan():
    from pyrplidar import PyRPlidar
    import time
    lidar = PyRPlidar()
    lidar.connect(port="/dev/ttyUSB0", baudrate=115200, timeout=3)
    # Linux   : "/dev/ttyUSB0"
    # MacOS   : "/dev/cu.SLAB_USBtoUART"
    # Windows : "COM5"

    lidar.set_motor_pwm(500)
    time.sleep(2)
    scan_generator = lidar.start_scan_express(4)

    for count, scan in enumerate(scan_generator()):
        print(count, scan)
        if count == 20: break

    lidar.stop()
    lidar.set_motor_pwm(0)
    lidar.disconnect()
