import threading
import serial

port = '/dev/ttyACM0'
baud = 9600

serial_port = serial.Serial(port, baud, timeout=0)

def handle_data(data):
    print(data)

def read_from_port(ser):
    while True:
        reading = ser.readline().decode()
        handle_data(reading)

thread = threading.Thread(target=read_from_port, args=(serial_port,))
thread.start()