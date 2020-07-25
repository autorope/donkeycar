#!/usr/bin/env python3
"""
Scripts for operating the RoboHAT MM1 by Robotics Masters with the Donkeycar

author: @wallarug (Cian Byrne) 2019
contrib: @peterpanstechland 2019
contrib: @sctse999 2020

Note: To be used with code.py bundled in this repo. See donkeycar/contrib/robohat/code.py
"""

import time
import donkeycar as dk

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

    def __init__(self, cfg, debug=False):
        # standard variables
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False
        self.STEERING_MID = cfg.MM1_STEERING_MID
        self.MAX_FORWARD = cfg.MM1_MAX_FORWARD
        self.STOPPED_PWM = cfg.MM1_STOPPED_PWM
        self.MAX_REVERSE = cfg.MM1_MAX_REVERSE
        self.SHOW_STEERING_VALUE = cfg.MM1_SHOW_STEERING_VALUE
        self.DEAD_ZONE = cfg.JOYSTICK_DEADZONE
        self.debug = debug

        try:
            self.serial = serial.Serial(cfg.MM1_SERIAL_PORT, 115200, timeout=1)
        except serial.SerialException:
            print("Serial port not found!  Please enable: sudo raspi-config")
        except serial.SerialTimeoutException:
            print("Serial connection timed out!")

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass

    def read_serial(self):
        '''
        Read the rc controller value from serial port. Map the value into
        steering and throttle

        Format ####,#### whereas the 1st number is steering and 2nd is throttle
        '''
        line = str(self.serial.readline().decode()).strip('\n').strip('\r')

        output = line.split(", ")
        if len(output) == 2:
            if self.SHOW_STEERING_VALUE:
                print("MM1: steering={}".format(output[0]))

            if output[0].isnumeric() and output[1].isnumeric():
                angle_pwm = float(output[0])
                throttle_pwm = float(output[1])

                if self.debug:
                    print("angle_pwm = {}, throttle_pwm= {}".format(angle_pwm, throttle_pwm))


                if throttle_pwm >= self.STOPPED_PWM:
                    # Scale down the input pwm (1500 - 2000) to our max forward
                    throttle_pwm = dk.utils.map_range_float(throttle_pwm,
                                                                1500, 2000,
                                                                self.STOPPED_PWM,
                                                                self.MAX_FORWARD )
                    # print("remapping throttle_pwm from {} to {}".format(output[1], throttle_pwm))

                    # Go forward
                    self.throttle = dk.utils.map_range_float(throttle_pwm,
                                                             self.STOPPED_PWM,
                                                             self.MAX_FORWARD,
                                                             0, 1.0)
                else:
                    throttle_pwm = dk.utils.map_range_float(throttle_pwm,
                                                                1000, 1500,
                                                                self.MAX_REVERSE,
                                                                self.STOPPED_PWM)


                    # Go backward
                    self.throttle = dk.utils.map_range_float(throttle_pwm,
                                                             self.MAX_REVERSE,
                                                             self.STOPPED_PWM,
                                                             -1.0, 0)

                if angle_pwm >= self.STEERING_MID:
                    # Turn Left
                    self.angle = dk.utils.map_range_float(angle_pwm,
                                                          2000, self.STEERING_MID,
                                                          -1, 0)
                else:
                    # Turn Right
                    self.angle = dk.utils.map_range_float(angle_pwm,
                                                          self.STEERING_MID, 1000,
                                                          0, 1)

                if self.debug:
                    print("angle = {}, throttle = {}".format(self.angle, self.throttle))

                if self.throttle > self.DEAD_ZONE:
                    self.recording = True
                else:
                    self.recording = False

                time.sleep(0.01)

    def update(self):
        # delay on startup to avoid crashing
        print("Warming serial port...")
        time.sleep(3)

        while True:
            try:
                self.read_serial()
            except:
                print("MM1: Error reading serial input!")
                break

    def run(self, img_arr=None):
        return self.run_threaded()

    def run_threaded(self, img_arr=None):
        return self.angle, self.throttle, self.mode, self.recording


class RoboHATDriver:
    """
    PWM motor controller using Robo HAT MM1 boards.
    This is developed by Robotics Masters
    """

    def __init__(self, cfg, debug=False):
        # Initialise the Robo HAT using the serial port
        self.pwm = serial.Serial(cfg.MM1_SERIAL_PORT, 115200, timeout=1)
        self.MAX_FORWARD = cfg.MM1_MAX_FORWARD
        self.MAX_REVERSE = cfg.MM1_MAX_REVERSE
        self.STOPPED_PWM = cfg.MM1_STOPPED_PWM
        self.STEERING_MID = cfg.MM1_STEERING_MID
        self.debug = debug

    """
    Steering and throttle should range between -1.0 to 1.0. This function will
    trim value great than 1.0 or less than 1.0
    """

    def trim_out_of_bound_value(self, value):
        if value > 1:
            print("MM1: Warning, value out of bound. Value = {}".format(value))
            return 1.0
        elif value < -1:
            print("MM1: Warning, value out of bound. Value = {}".format(value))
            return -1.0
        else:
            return value

    def set_pulse(self, steering, throttle):
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = dk.utils.map_range(throttle,
                                                     0, 1.0,
                                                     self.STOPPED_PWM, self.MAX_FORWARD)
            else:
                output_throttle = dk.utils.map_range(throttle,
                                                     -1, 0,
                                                     self.MAX_REVERSE, self.STOPPED_PWM)

            if steering > 0:
                output_steering = dk.utils.map_range(steering,
                                                     0, 1.0,
                                                     self.STEERING_MID, 1000)
            else:
                output_steering = dk.utils.map_range(steering,
                                                     -1, 0,
                                                     2000, self.STEERING_MID)

            if self.is_valid_pwm_value(output_steering) and self.is_valid_pwm_value(output_throttle):
                if self.debug:
                    print("output_steering=%d, output_throttle=%d" % (output_steering, output_throttle))
                self.write_pwm(output_steering, output_throttle)
            else:
                print(f"Warning: steering = {output_steering}, STEERING_MID = {self.STEERING_MID}")
                print(f"Warning: throttle = {output_throttle}, MAX_FORWARD = {self.MAX_FORWARD}, STOPPED_PWM = {self.STOPPED_PWM}, MAX_REVERSE = {self.MAX_REVERSE}")
                print("Not sending PWM value to MM1")

        except OSError as err:
            print(
                "Unexpected issue setting PWM (check wires to motor board): {0}".format(err))

    def is_valid_pwm_value(self, value):
        if 1000 <= value <= 2000:
            return True
        else:
            return False

    def write_pwm(self, steering, throttle):
        self.pwm.write(b"%d, %d\r" % (steering, throttle))

    def run(self, steering, throttle):
        self.set_pulse(steering, throttle)

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass
