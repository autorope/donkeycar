#import pyserial library

import serial
import time
import numpy as np
from collections import deque

# Store 1 frame of data

class B0602Lidar:

    ser = None
    port = ''
    baudrate = 115200
    angle = 0
    signalStrength = 0
    dist = 0
    debug = False
    single_scan = {}

    # realted bit

    flag = []
    data = []
    length = 0
    data_length = 0
    cmd = ''
    cyc = 0B11000000000000101

    zero_offset = 0
    rpm = 0

    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        '''Initilize B0602Lidar object for communicating with the sensor.
        Parameters
        ----------
        port : str
            Serial port name to which sensor is connected
        baudrate : int, optional
            Baudrate for serial connection (the default is 115200)
        '''
        print("Initializing the B0602 Lidar")
        print("Port:",port)
        self.port = port
        self.baudrate = baudrate
        self.ser = self._connect()

    def _connect(self):
        '''Connects to the serial port with the name `self.port`.'''
        ser = serial.Serial()
        ser.baudrate = 115200
        ser.port = self.port
        try:
            ser.open()
            if ser.is_open:
                print("B0602 Lidar Connected")
        except serial.serialutil.SerialException as err:
            print(err)
            exit(0)
        return ser

    def _bytes_to_int(self,input_bytes):  # change byte to int
        isinstance(input_bytes, bytes) or exit(99)
        if (len(input_bytes) == 0): return 0
        # (input_bytes[0] < 0x80) or exit (98)

        shift = i1 = 0
        for p in range(1, len(input_bytes) + 1):
            i1 += (input_bytes[-p] << shift)
            shift += 8

        return i1

    def iter_measurements(self):
        '''
        Iterate over measurements

        Yields
        ------
        new_scan : bool
            True if measurment belongs to a new scan
        quality : int
            Reflected laser pulse strength
        angle : float
            The measurment heading angle in degree unit [0, 360)
        distance : float
            Measured object distance related to the sensor's rotation center.
            In millimeter unit. Set to 0 when measurment is invalid.
        '''
        self.data.clear()
        self.single_scan.clear()

        while True:
            c = self.ser.read()
            if self.debug: print("  ",c)
            if c == b'\xAA':  # starting flag 
                cur = time.time()
                if self.debug: print("Current time tick:", cur)
                if self.debug: print("Package start")
                temp = []
                temp = self.ser.read(2)
                if self.debug: print("Length bit:", format(temp[0], '02x'), format(temp[1], '02x'))
                length = self._bytes_to_int(temp)
                if self.debug: print("Length of packet:", length)
                addr = self.ser.read()
                if addr == b'\x00':
                    if self.debug: print("addr = 0x00")
                else:
                    print("Addr not match: addr =",format(ord(addr), '02x'))
                    continue
                type = self.ser.read()
                if type == b'\x61':
                    if self.debug: print("type = 0x61")
                else:
                    print("type not match: type =",type)
                    continue
                cmd = self.ser.read()
                if cmd == b'\xAD':
                    if self.debug: print("Command = 0xAD")
                else:
                    if cmd == b'\xAE':
                        print("Command = \xAE")
                        print("Lidar Sensor Error")
                        break
                    else:
                        print("cmd not match: cmd =", format(cmd, '02x'))
                data_length_byte = self.ser.read(2)
                data_length = self._bytes_to_int(data_length_byte)
                if self.debug: print("Expected data length =", data_length)
                if length - data_length == 8:
                    if self.debug: print("bit length confirmed")
                else:
                    print("bit length not match, length =",length - data_length)
                    break
                rpm = self.ser.read()[0] * 0.05 # Need to convert to int
                if self.debug: print("(r/s) =", rpm)
                zero_offset_bit = self.ser.read(2)
                if self.debug: print("Zero offset bit:", format(zero_offset_bit[0], '02x'), format(zero_offset_bit[1], '02x'))
                zero_offest = self._bytes_to_int(zero_offset_bit)
                if zero_offest >= 2 ** 15:
                    zero_offest -= 2 ** 16
                if self.debug: print("Zero offset(0.01degree) =", zero_offest)
                if self.debug: print("Data Point in packet:",int((data_length - 5)/ 3))
                data_pts = int((data_length - 5)/ 3)

                angle_bit = self.ser.read(2)
                if self.debug: print("Angle bit:", format(angle_bit[0], '02x'), format(angle_bit[1], '02x'))
                start_angle = self._bytes_to_int(angle_bit)/100 + zero_offest
                if self.debug: print("Angle(0.01degree)", start_angle)

                new_scan = True

                for i in range(1, data_pts+1):
                    if self.debug: print("Loop count:", i)
                    signalStrength_bit = self.ser.read()
                    if self.debug: print("signal Strength bit:", format(signalStrength_bit[0], '02x'))
                    signalStrength = ord(signalStrength_bit)
                    if self.debug: print("signal Strength:", format(signalStrength))
                    dist_bit = self.ser.read(2)
                    if self.debug: print("Dist bit:", format(dist_bit[0], '02x'), format(dist_bit[1], '02x'))
                    dist = self._bytes_to_int(dist_bit) * 0.25  # in mm
                    angle = start_angle + 22.5 * (i-1) / data_pts
                    if self.debug: print("Distance (mm):", dist)
                    if self.debug: print("angle (0.01degree):", angle)
                    self.data.append([angle, dist])

                    yield (new_scan, signalStrength, angle, dist)

                    new_scan = False

                end = time.time()
                if self.debug: print("Time take for 1 packet", (end - cur) * 1000)
                if self.debug: print("Data package:", self.data)
                self.single_scan[start_angle] = self.data
                self.single_scan['r/s'] = rpm
                #print("Data:",self.single_scan)
                crc = self.ser.read(2)
                if self.debug: print("CRC check:",crc)
                #return self.single_scan

    def iter_scans(self, max_buf_size=2000, min_len=5):
        '''
        Iterate over scans. Note that consumer must be fast enough,

        Yields
        ------
        scan : list
            List of the measurments. Each measurment is tuple with following
            format: (quality, angle, distance). For values description please
            refer to `iter_measurements` method's documentation.
        '''
        scan = []
        iterator = self.iter_measurements()
        for i, (new_scan, quality, angle, distance) in enumerate(iterator):
            if new_scan:
                if len(scan) > min_len:
                    yield scan
                scan = []
            if quality > 0 and distance > 0:
                scan.append((quality, angle, distance))

