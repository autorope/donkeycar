
import serial
import time
port = '/dev/ttyACM0'
baud = 115200

lasttime = time.time()
lasttick = 0
ser = serial.Serial(port, baud, timeout = 0.1)
# initialize the odometer values
ser.write(str.encode('r'))  # restart the encoder to zero

ascii = ''


def read_serial(ser):
    global lasttime2, lasttick
    newdata = False
    input = ''
    lasttime2 = time.time()
    while (ser.in_waiting > 0):
        buffer = ser.readline()
        input = buffer.decode('ascii')
        print("encoder reading", input)
    ser.write(str.encode('p'))  # queue up another reading
    if input != '':
        temp = input.strip()  # remove any whitespace
        if (temp.isnumeric()):
            ticks = int(temp)
            newdata = True
            lasttick = ticks
    if newdata:
        return ticks
    else:
        return lasttick

while True:
    read_serial(ser)