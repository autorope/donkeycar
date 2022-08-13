#!/usr/bin/env python3
from __future__ import print_function
"""
Script for using a Pixhawk running any ArduPilot- or PX4-based code with Donkeycar 

author: @zlite (Chris Anderson), 2022
contrib: @wallarug (Cian Byrne) 2019
contrib: @peterpanstechland 2019
contrib: @sctse999 2020

If you're getting a permissions error on the USB port: "sudo chmod 666 /dev/ttyACM0"

requires: 
--gcc (sudo apt install gcc)
--pymavlink (pip install pymavlink)
--docopt (pip install docopt)

"""

import time
import donkeycar as dk
import config as cfg

debug = False

try:
    import serial
except ImportError:
    print("PySerial not found.  Please install: pip install pyserial")

try:
    from pymavlink import mavutil
except ImportError:
    print("Pymavlink not found.  Please install: pip install pymavlink")


class MavlinkController:
    '''
    Driver to read MAVLink RC data from a Pixhawk, for manual control
    '''

    def __init__(self, cfg, debug=False):
        # standard variables
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False
        self.STEERING_MID = cfg.MAVLINK_STEERING_MID
        self.MAX_FORWARD = cfg.MAVLINK_FORWARD
        self.STOPPED_PWM = cfg.MAVLINK_STOPPED_PWM
        self.MAX_REVERSE = cfg.MAVLINK_MAX_REVERSE
        self.SHOW_STEERING_VALUE = cfg.MAVLINK_SHOW_STEERING_VALUE
        self.DEAD_ZONE = cfg.JOYSTICK_DEADZONE
        self.debug = debug

        master = mavutil.mavlink_connection(cfg.MAVLINK_SERIAL_PORT, baud = 115200)

    def read_serial(self):
        '''
        Read the MAVLink values from the serial port connected to the Pixhawk
        '''
        # create a mavlink serial instance
        msg = master.recv_match()
        if not msg:
            return       
        else:
            if msg.get_type() == "ATTITUDE":
                print ("pitch", round(msg.pitch,2), "roll", round(msg.roll,2), "yaw", round(msg.yaw,2), "pitchspeed", round(msg.pitchspeed,2), "rollspeed", round(msg.rollspeed,2), "yawspeed", round(msg.yawspeed,2)) 
            if msg.get_type() == "GLOBAL_POSITION_INT":
                print ("lat:", msg.lat, "lon:", msg.lon)            
            if msg.get_type() == "RC_CHANNELS":
#                print ("Ch1:", msg.chan1_raw, "Ch2:", msg.chan2_raw, "Ch3:", msg.chan3_raw)                         
                angle_pwm = msg.chan1_raw
                throttle_pwm = msg.chan3_raw
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
                print("MAVlink: Error reading serial input!")
                break

    def run(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image or None
        :param mode: default user/mode
        :param recording: default recording mode
        """
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image
        :param mode: default user/mode
        :param recording: default recording mode
        """
        self.img_arr = img_arr

        #
        # enforce defaults if they are not none.
        #
        if mode is not None:
            self.mode = mode
        if recording is not None:
            self.recording = recording

        return self.angle, self.throttle, self.mode, self.recording


class MavlinkDriver:
    """
    PWM motor controller, for output to motors and servos.
    """

    def __init__(self, cfg, debug=False):
        self.MAX_FORWARD = cfg.MAVLINK_MAX_FORWARD
        self.MAX_REVERSE = cfg.MAVLINK_MAX_REVERSE
        self.STOPPED_PWM = cfg.MAVLINK_STOPPED_PWM
        self.STEERING_MID = cfg.MAVLINK_STEERING_MID
        self.debug = debug
        master = mavutil.mavlink_connection(cfg.MAVLINK_SERIAL_PORT, baud = 115200)

    """
    Steering and throttle should range between -1.0 to 1.0. This function will
    trim value great than 1.0 or less than 1.0
    """
    def set_servo_pwm(self, servo_n, microseconds):
        """ Sets AUX 'servo_n' output PWM pulse-width.

        Uses https://mavlink.io/en/messages/common.html#MAV_CMD_DO_SET_SERVO

        'servo_n' is the AUX port to set (assumes port is configured as a servo).
            Valid values are 1-3 in a normal BlueROV2 setup, but can go up to 8
            depending on Pixhawk type and firmware.
        'microseconds' is the PWM pulse-width to set the output to. Commonly
            between 1100 and 1900 microseconds.

        """
        # master.set_servo(servo_n+8, microseconds) or:
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0,            # first transmission of this command
            servo_n + 8,  # servo instance, offset by 8 MAIN outputs
            microseconds, # PWM pulse-width
            0,0,0,0,0     # unused parameters
        )
    def trim_out_of_bound_value(self, value):
        if value > 1:
            print("MAVLink: Warning, value out of bound. Value = {}".format(value))
            return 1.0
        elif value < -1:
            print("MAVLink: Warning, value out of bound. Value = {}".format(value))
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
                self.set_servo_pwm(1, output_steering)
                self.set_servo_pwm(2, output_throttle)
                self.set_servo_pwm(3, output_throttle)
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

    def run(self, steering, throttle):
        self.set_pulse(steering, throttle)

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass

if debug:
    print ("starting debug")
    MavlinkController.read_serial