# This is for a quadrature wheel or motor encoder that is being read by an offboard microcontroller
# such as an Arduino or Teensy that is feeding serial data to the RaspberryPy or Nano via USB serial. 
# The microcontroller should be flashed with this sketch (use the Arduino IDE to do that): https://github.com/zlite/donkeycar/tree/master/donkeycar/parts/encoder/encoder
# Make sure you check the sketch to make sure you've got your encoder plugged into the right pins, or edit it to reflect the pins you are using.

# You will need to calibrate the mm_per_tick line below to reflect your own car. Just measure out a meter and roll your car
# along it. Change the number below until it the distance reads out almost exactly 1.0 

# This samples the odometer at 10HZ and does a moving average over the past ten readings to derive a velocity

import serial
import time
import serial.tools.list_ports
for item in serial.tools.list_ports.comports():
  print( item )
ser = serial.Serial('/dev/ttyACM0', 115200, 8, 'N', 1, timeout=1)
# initialize the odometer values
mm_per_tick = 0.0000599   # edit this for your own car
ave_velocity = []
for i in range(10):
    ave_velocity.append(0)
ser.write(str.encode('reset'))  # restart the encoder to zero

def update():
    last_time = time.time()
    start_distance = 0
    ticks = 0
    # keep looping infinitely until the thread is stopped
    while True:
        input = ser.readline()
        ticks = input.decode()
        ticks = ticks.strip()  # remove any whitespace
        if (ticks.isnumeric()):
            ticks = int(ticks)
            # print("ticks=", ticks)
            current_time = time.time()
    #       print('seconds:', seconds)
            if current_time >= last_time + 0.1:   # print at 10Hz
                end_distance = ticks * mm_per_tick
                instant_velocity = (end_distance-start_distance)*10  # multiply times ten to convert to m/s
                for i in range(9):
                    ave_velocity[9-i] = ave_velocity[8-i]  # move the time window down one
                ave_velocity[0] = instant_velocity  # stick the latest reading at the start
                velocity = sum(ave_velocity)/len(ave_velocity)  # moving average
                print('distance (m):', round(end_distance,3))
                print('velocity (m/s):', round(velocity,3))
                last_time = current_time
                start_distance = end_distance

update()