#!/usr/bin/env python3
"""
Scripts for operating the RoboHAT MM1 by Robotics Masters with the Donkeycar

author: @wallarug (Cian Byrne) 2019
contrib: @peterpanstechland 2019
"""

import time

try:
    import serial
except ImportError:
    print("PySerial not found.  Please install: pip install pyserial")

class RoboHATController:
    '''
    Driver to read signals from SAMD51 and convert into steering and throttle outputs
    Input input signal range: 1000 to 2000
    Output range: -1.00 to 1.00
    '''

    def __init__(self):
        # standard variables
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False

        #Serial port - laptop: 'COM3', Arduino: '/dev/ttyACM0'
        try:
            self.serial = serial.Serial('/dev/ttyS0', 115200, timeout=1)
        except serial.SerialException:
            print("Serial port not found!  Please enable: sudo raspi-config")
        except serial.SerialTimeoutException:
            print("Serial connection timed out!")

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass

    def update(self):
        # delay on startup to avoid crashing
        print("Warming serial port...")
        time.sleep(3)

        while True:
            try:
                line = str(self.serial.readline().decode()).strip('\n').strip('\r')
            except:
                print("Serial Error!")
                break
            output = line.split(", ")
            if len(output) == 2:
                if output[0].isnumeric() and output[1].isnumeric():
                    self.angle = (float(output[0])-1500)/500
                    self.throttle = (float(output[1])-1500)/500
                    if self.throttle > 0.01:
                        self.recording = True
                        print("Recording")
                    else:
                        self.recording = False
                    time.sleep(0.01)

    def run(self, img_arr=None):
        return self.run_threaded()

    def run_threaded(self, img_arr=None):
        #print("Signal:", self.angle, self.throttle)
        return self.angle, self.throttle, self.mode, self.recording


class RoboHATDriver:
    """
    PWM motor controller using Robo HAT MM1 boards.
    This is developed by Robotics Masters
    """
    def __init__(self):
        # Initialise the Robo HAT using the serial port
        self.pwm = serial.Serial('/dev/ttyS0', 115200, timeout=1)

    def set_pulse(self, throttle, steering):
        try:
            if throttle > 0:
                output_throttle = dk.utils.map_range(throttle,
                                           0, 1.0,
                                           1500, 2000)
            else:
                output_throttle = dk.utils.map_range(throttle,
                                           -1, 0,
                                           1000, 1500)

            if steering > 0:
                output_steering = dk.utils.map_range(steering,
                                           0, 1.0,
                                           1500, 2000)
            else:
                output_steering = dk.utils.map_range(steering,
                                           -1, 0,
                                           1000, 1500)

            packet = "{0},{1}".format(str(output_throttle).zfill(4), str(output_steering).zfill(4))
            self.pwm.write(b"%d, %d\r" % (eval(packet)))
            print("%d, %d\r" % (eval(packet)))
        except OSError as err:
            print("Unexpected issue setting PWM (check wires to motor board): {0}".format(err))

    def run(self, throttle, steering):
        self.set_pulse(throttle, steering)

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass

