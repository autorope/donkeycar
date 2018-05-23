import sys
import os
import argparse
import json
import time

import donkeycar as dk
from donkeycar.parts.datastore import Tub
from donkeycar.utils import *

class CreateJoystick(object):

    def __init__(self):
        self.last_button = None
        self.last_axis = None
        self.running = False
        self.thread = None
        self.motion_axis = []
        self.ignore_axis = False
        self.ignore_buttons = False

    def poll(self):
        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if button is not None and not self.ignore_buttons:
                print(button)
                self.last_button = button
                self.last_axis = None
            elif axis is not None and not self.ignore_axis:
                if not axis in self.motion_axis:
                    self.last_axis = axis
                    self.last_button = None

    def get_button_press(self, duration=10.0):
        self.last_button = None

        start = time.time()

        while self.last_button is None and time.time() - start < duration:
            time.sleep(0.1)

        return self.last_button

    def get_axis_move(self, duration=2.0):
        self.last_axis = None
        axis_samples = {}

        start = time.time()

        while time.time() - start < duration:
            if self.last_axis:
                if self.last_axis in axis_samples:
                    axis_samples[self.last_axis] = axis_samples[self.last_axis] + 1
                else:
                    axis_samples[self.last_axis] = 1

        most_movement = None
        most_iter = 0
        for key, value in axis_samples.items():
            if value > most_iter:
                most_movement = key
                most_iter = value

        return most_movement

    def create_joystick(self, args):
        from donkeycar.parts.controller import JoystickCreatorController

        print("Welcome to Joystick Creator Wizard.")
        print("This will walk you through the steps to create a python class to use your controller.")
        print("The first steps will create a label for each of the buttons and axis controls.")
        print("Then we will create a mapping of labels to actions.")
        print("Please plug-in your controller via USB or bluetooth.")
        input('Enter to continue ')
        print()
        
        self.init_js_device()
        print()
        
        self.init_polling_js()

        self.find_gyro()

        print()
        self.name_buttons()

        print()
        self.name_axes()

        print()
        self.write_python_class_file()

        print()
        print('------------------------------------------')
        print('Now we will create a mapping of labels to actions.')

        self.map_steering_throttle()
        self.map_button_controls()

        self.shutdown()

    def init_js_device(self):
        js_cr = None

        #Get device file and create js creator helper class
        while js_cr is None:
            print("Which device file would you like to use?")
            dev_fn = input("Hit Enter for default: /dev/input/js0 or type alternate path: ")
            if len(dev_fn) is 0:
                dev_fn = '/dev/input/js0'

            print()
            print("Attempting to open device at that file...")
            try:
                js_cr = JoystickCreatorController(dev_fn=dev_fn)
                res = js_cr.init_js()
                if res:
                    print("Found and accessed input device file.")
                else:
                    js_cr = None
            except Exception as e:
                print("threw exception:" + str(e))
                js_cr = None

            if js_cr is None:
                ret = input("Failed to open device. try again? [Y/n] : ")
                if ret.upper() == "N":
                    exit(0)

        self.js = js_cr.js

    def init_polling_js(self):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.poll)
        self.thread.daemon = True
        self.thread.start()

    def find_gyro(self):
        print("Next we are going to look for gyroscope data.")
        input("For 5 seconds, move controller and rotate on each axis. Enter to start moving: ")
        start = time.time()
        while time.time() - start < 5.0:
            if self.last_axis is not None and not self.last_axis in self.motion_axis:
                self.motion_axis.append(self.last_axis)

        print()
        if len(self.motion_axis) > 0:
            print("Ok, we found %d axes that stream gyroscope data." % len(self.motion_axis))
        else:
            print("Ok, we didn't see any events. So perhaps your controller doesn't emit gyroscope data. No problem.")

    def name_buttons(self):
        print('Next we are going to name all the buttons you would like to use.')
        done = False
        self.ignore_axis = True

        while not done:
            print('Tap a button on the controller. Any previously mapped button to quit')
            
            self.get_button_press()

            if self.last_button is None:
                print("No button was pressed in last 10 seconds. It's possible that your buttons all generate axis commands.")
                ret = input("Keep mapping buttons? [Y, n]")
                if ret == 'n':
                    break
            elif 'unknown' in self.last_button:
                code_str = self.last_button.split('(')[1][:-1]
                print('got button code:', code_str)
                try:
                    code = int(code_str, 16)
                except Exception as e:
                    code = None
                    print("failed to parse code", str(e))

                if code is not None:
                    if code in self.js.button_names:
                        done = True
                        break
                    label = input("what name to give to this button: (Q to quit) ")
                    if len(label) == 0:
                        print("no name given. skipping.")
                    elif label.upper() == 'Q':
                        done = True
                    else:
                        self.js.button_names[code] = label
            else:
                print('got press: ', self.last_button)

            print()

        
        print("Created button map:")
        print(self.js.button_names)

    def name_axes(self):
        print('Next we are going to name all the axis you would like to use.')

        done = False
        self.ignore_axis = False

        while not done:
            print('Prepare to move one axis on the controller for 2 sec.')
            ret = input("Hit Enter to begin. Q to quit. ")
            if ret == 'q':
                break
            
            most_movement = self.get_axis_move()

            if most_movement is None:
                print("Didn't detect any movement.")
                res = input("Try again? [Y/n]: ")
                if res == "n":
                    done = True
                    break
                else:
                    continue

            if 'unknown' in most_movement:
                code_str = most_movement.split('(')[1][:-1]
                print('Most movement on axis code:', code_str)
                try:
                    code = int(code_str, 16)
                except Exception as e:
                    code = None
                    print("Failed to parse code", str(e))

                if code is not None:
                    label = input("What name to give to this axis: (Q to quit) ")
                    if len(label) == 0:
                        print("No name given. skipping.")
                    elif label == 'q':
                        done = True
                    else:
                        self.js.axis_names[code] = label
            else:
                print('Got axis: ', self.last_axis)
            print()

        print("Created axis map:")
        print(self.js.axis_names)

    def write_python_class_file(self):
        pyth_filename = None
        outfile = None
        while pyth_filename is None:
            print("Now we will write these values to a new python file.")
            pyth_filename = input("What is the name of python file to create joystick code? [default: joystick.py]")
            if len(pyth_filename) == 0:
                pyth_filename = 'joystick.py'
            print()
            try:
                outfile = open(pyth_filename, "wt")
            except:
                ret = input("failed to open filename. Enter another filename? [Y,n]")
                if ret == "n":
                    break
                pyth_filename = None
            print()
            
        if outfile is not None:
            classname = ("What is the name of joystick class? [default: MyJoystick] ")
            if len(classname) == 0:
                classname = "MyJoystick"
            file_header = \
            '''
            from donkeycar.parts.controller import Joystick, JoystickController


            class %s(Joystick):
                #An interface to a physical joystick available at /dev/input/js0
                def __init__(self, *args, **kwargs):
                    super(%s, self).__init__(*args, **kwargs)

            ''' % (classname, classname )

            outfile.write(file_header)

            outfile.write('        self.button_names = {\n')
            for key, value in self.js.button_names.items():
                outfile.write("            %s : '%s',\n" % (str(key), str(value)))
            outfile.write('        }\n\n\n')
            
            outfile.write('        self.axis_names = {\n')

            for key, value in self.js.axis_names.items():
                outfile.write("            %s : '%s',\n" % (str(key), str(value)))
            outfile.write('        }\n\n\n')

            outfile.close()
            print(pyth_filename, "written.")

    def map_steering_throttle(self):
        self.axis_map = []
        print("First steering.")
        axis = self.get_axis_action('Move the controller axis you wish to use for steering. Continue moving for 2 seconds.')
        
        if axis is None:
            print("No mapping for steering.")
        else:
            print('Mapping %s to steering.' % axis)
            for key, value in self.js.axis_names.items():
                if key == axis or value == axis:
                    self.axis_map.append((value, "self.set_steering"))
                    break

        print("Next throttle.")
        axis = self.get_axis_action('Move the controller axis you wish to use for throttle. Continue moving for 2 seconds.')
        
        if axis is None:
            print("No mapping for throttle.")
        else:
            print('Mapping %s to throttle.' % axis)
            for key, value in self.js.axis_names.items():
                if key == axis or value == axis:
                    self.axis_map.append((value, "self.set_throttle"))
                    break


    def map_button_controls(self):
        unmapped_controls = [\
            ('toggle_mode','changes the drive mode between user, local, and local_angle'),
            ('toggle_manual_recording','toggles recording records on and off'),
            ('erase_last_N_records','erases the last 100 records while driving'),
            ('emergency_stop','executes a full back throttle to bring car to a quick stop'),
            ('increase_max_throttle','increases the max throttle, also used for constant throttle val'),
            ('decrease_max_throttle','decreases the max throttle, also used for constant throttle val'),
            ('toggle_constant_throttle', 'toggle the mode of supplying constant throttle')
        ]

        self.mappped_controls = []

        done = False
        while not done:
            for iContrl, control, help in enumerate(unmapped_controls):
                print(iContrl, control, '\t', help)

        
    def get_axis_action(self, prompt):
        done = False        
        while not done:
            print(prompt)
            ret = input("Hit Enter to begin. Q to quit. ")
            if ret.upper() == 'Q':
                return None

            most_movement = self.get_axis_move()

            if most_movement is None:
                print("Didn't detect any movement.")
                res = input("Try again? [Y/n]: ")
                if res == "n":
                    return None
                else:
                    continue


    def shutdown(self):
        self.running = False
        if self.thread:
            print('shutting down js thread')
            self.thread.join()
            self.thread = None
        print("done")

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createjs', usage='%(prog)s [options]')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        try:
            self.create_joystick(args)
        except KeyboardInterrupt:
            self.shutdown()

