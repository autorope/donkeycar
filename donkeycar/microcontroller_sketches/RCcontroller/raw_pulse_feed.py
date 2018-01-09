import serial
from time import sleep

''' 
This takes input from an Arduino Uno which is converting
the RC receiver pulses into a INT value. This script is
useful for determining the CENTER, LOW, and HIGH values 
returned by your car once you've gotten it trimmed correctly

The Arduino blindly sends pulse to the buffer, currently
at twice the Hz of this script. (40 Hz). 
'''

# attach to the Arduino
dev = '/dev/ttyACM0' # Arduino Due, Uno, Teensy
#dev = '/dev/ttyUSB0' # Arduino Dueminulnova

# create a serial connection. (plug USB from Arduino into Pi)
ser = serial.Serial(dev,57600)
print("Initialized Serial");

# 20 is the default Hz for Donkey Car
hz = 20

# convert this scripts hz to a decimal sleep value
sleep_time = 1000/float(hz)/1000.0

def getLatestStatus():
    ''' This clears the buffer and returns only the last value
        This is faster than polling the arduino for the latest value
    '''
    status = b''
    while ser.inWaiting() > 0:
	# read and discard any values except the most recent.
        # when Arduino Hz = 2x python Hz this results in 1 to 2
        # discarded results
        status = ser.readline()
        
    # return it as an array
    # raw format = b'1234 1234\r\n' from the Arduino
    try:
        vel_angle_raw = status.strip().decode("utf-8").split(" ")
    except Exception:
        # unable to decode the values from the Arduino. Typically happens
        # at startup when the serial connection is being started and lasts
        # a few cycles. Junk in the trunk..
        vel_angle_raw = ['0' for x in range(self.num_channels)]
    return vel_angle_raw

while True:
	# While forever, get the most recent command the 
	# arduino has sent
	vel_angle_raw = getLatestStatus()

	if len(vel_angle_raw)==2:
		# if there are two values, convert to INT
		print(list(map(int,vel_angle_raw)))
		
	# wait Hz amount of time to recover next command
	sleep(sleep_time)
