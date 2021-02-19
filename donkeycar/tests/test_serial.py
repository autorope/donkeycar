
import serial
import time
port = '/dev/ttyACM0'
baud = 9600

lasttime = time.time()
ser = serial.Serial(port, baud, timeout = 0.1)
# initialize the odometer values
ser.write(str.encode('reset'))  # restart the encoder to zero

ascii = ''

while True:
    lasttime = time.time()
    while (ser.in_waiting > 0) and (time.time() < lasttime + .001):   # read the serial port for a millisecond
        buffer = ser.readline()
        ascii = buffer.decode('ascii')
    if ascii != '':
        print('ascii=', ascii)
        ascii = ''