
import pytest


def has_lidar():
    """ Determine if test platform (nano, pi) has lidar"""
    # for now just return false, better to use an environ
    return False


@pytest.mark.skipif(not has_lidar(), reason='Need lidar installed')
def test_lidar():
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

