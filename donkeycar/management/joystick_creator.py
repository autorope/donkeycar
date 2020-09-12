import sys
import os
import argparse
import json
import time
import math

from donkeycar.utils import *
from donkeycar.parts.controller import JoystickCreatorController

try:
    from prettytable import PrettyTable
except:
    print("need: pip install PrettyTable")

class CreateJoystick(object):

    def __init__(self):
        self.last_button = None
        self.last_axis = None
        self.axis_val = 0
        self.running = False
        self.thread = None
        self.gyro_axis = []
        self.axis_map = []
        self.ignore_axis = False
        self.mapped_controls = []

    def poll(self):
        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if button is not None:
                self.last_button = button
                self.last_axis = None
                self.axis_val = 0.0
            elif axis is not None and not self.ignore_axis:
                if not axis in self.gyro_axis:
                    self.last_axis = axis
                    self.last_button = None
                    self.axis_val = axis_val

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
                    try:
                        axis_samples[self.last_axis] = axis_samples[self.last_axis] + math.fabs(self.axis_val)
                    except:
                        try:
                            axis_samples[self.last_axis] = math.fabs(self.axis_val)
                        except:
                            pass
                else:
                    axis_samples[self.last_axis] = math.fabs(self.axis_val)
            
        most_movement = None
        most_val = 0
        for key, value in axis_samples.items():
            if value > most_val:
                most_movement = key
                most_val = value

        return most_movement

    def clear_scr(self):
        print(chr(27) + "[2J")

    def create_joystick(self, args):
        
        self.clear_scr()
        print("##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##")
        print("## Welcome to Joystick Creator Wizard. ##")
        print("##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##")
        print("This will generate code to use your joystick with a Donkey car.")
        print()
        print("Overview:")
        print()
        print("First we name each button, then each axis control.")
        print("Next we map names to actions.")
        print("Finally we output a python file you can use in your project.")
        print()
        input('Hit Enter to continue')
        self.clear_scr()
        print("Please plug-in your controller via USB or bluetooth. Make sure status lights are on and device is mapped.")
        input('Enter to continue ')
        self.clear_scr()
        
        self.init_js_device()
        print()
        
        self.init_polling_js()
        self.clear_scr()

        self.find_gyro()
        self.clear_scr()

        self.explain_config()
        self.clear_scr()

        self.name_buttons()
        self.clear_scr()

        self.name_axes()
        self.clear_scr()

        self.map_steering_throttle()
        self.clear_scr()

        self.map_button_controls()
        self.clear_scr()

        self.revisit_topic()
        self.clear_scr()

        self.write_python_class_file()

        print("Check your new python file to see the controller implementation. Import this in manage.py and use for control.")

        self.shutdown()

    def init_js_device(self):
        from donkeycar.parts.controller import JoystickCreatorController

        js_cr = None

        #Get device file and create js creator helper class
        while js_cr is None:
            print("Where can we find the device file for your joystick?")
            dev_fn = input("Hit Enter for default: /dev/input/js0 or type alternate path: ")
            if len(dev_fn) is 0:
                dev_fn = '/dev/input/js0'

            print()
            print("Attempting to open device at that file...")
            try:
                js_cr = JoystickCreatorController(dev_fn=dev_fn)
                res = js_cr.init_js()
                if res:
                    print("Found and accessed input device.")
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
        input("Hit Enter to continue")

    def init_polling_js(self):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.poll)
        self.thread.daemon = True
        self.thread.start()

    def find_gyro(self):
        print("Next we are going to look for gyroscope data.")
        input("For 5 seconds, move controller and rotate on each axis. Hit Enter then start moving: ")
        start = time.time()
        while time.time() - start < 5.0:
            if self.last_axis is not None and not self.last_axis in self.gyro_axis:
                self.gyro_axis.append(self.last_axis)

        print()
        if len(self.gyro_axis) > 0:
            print("Ok, we found %d axes that stream gyroscope data. We will ignore those during labelling and mapping." % len(self.gyro_axis))
        else:
            print("Ok, we didn't see any events. So perhaps your controller doesn't emit gyroscope data. No problem.")
        
        input("Hit Enter to continue ")

    def get_code_from_button(self, button):
        code = button
        if 'unknown' in button:
            try:
                code_str = button.split('(')[1][:-1]
                code = int(code_str, 16)
            except Exception as e:
                code = None
                print("failed to parse code", str(e))
        return code

    def explain_config(self):
        print("We will display the current progress in this set of tables:")
        print()
        self.print_config()
        print("\nAs you name buttons and map them to controls this table will be updated.")
        input("Hit enter to continue")


    def name_buttons(self):
        done = False
        self.ignore_axis = True

        self.print_config()

        print('Next we will give every button a name. Not analog yet. We will do that next.')

        while not done:

            print('Tap a button to name it.')
            
            self.get_button_press()

            if self.last_button is None:
                print("No button was pressed in last 10 seconds. It's possible that your buttons all generate axis commands.")
                ret = input("Keep mapping buttons? [Y, n]")
                if ret == 'n':
                    break
            elif 'unknown' in self.last_button:
                code = self.get_code_from_button(self.last_button)

                if code is not None:
                    if code in self.js.button_names:
                        ret = input("This button has a name: %s. Are you done naming? (y/N) " % self.js.button_names[code])
                        if ret.upper() == "Y":
                            done = True
                            break
                    label = input("What name to give to this button:")
                    if len(label) == 0:
                        print("No name given. skipping.")
                    else:
                        self.clear_scr()
                        self.js.button_names[code] = label
                        self.print_config()
            else:
                print('got press: ', self.last_button)

            self.clear_scr()
            self.print_config()
            

    def print_config(self):
        pt = PrettyTable()
        pt.field_names = ["button code", "button name"]
        for key, value in self.js.button_names.items():
            pt.add_row([str(hex(key)), str(value)])
        print("Button Map:")
        print(pt)

        pt = PrettyTable()
        pt.field_names = ["axis code", "axis name"]
        for key, value in self.js.axis_names.items():
            pt.add_row([str(hex(key)), str(value)])
        print("Axis Map:")
        print(pt)

        pt = PrettyTable()
        pt.field_names = ["control", "action"]
        for button, control in self.mapped_controls:
            pt.add_row([button, control])
        for axis, control in self.axis_map:
            pt.add_row([axis, control])
        print("Control Map:")
        print(pt)

    def name_axes(self):
        self.print_config()
        print()
        print('Next we are going to name all the axis you would like to use.')

        done = False
        self.ignore_axis = False

        while not done:
            print('Prepare to move one axis on the controller for 2 sec.')
            ret = input("Hit Enter to begin. D when done. ")
            if ret.upper() == 'D':
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
                    label = input("What name to give to this axis: (D when done) ")
                    if len(label) == 0:
                        print("No name given. skipping.")
                    elif label.upper() == 'D':
                        done = True
                    else:
                        self.js.axis_names[code] = label
                        self.clear_scr()
                        self.print_config()
            else:
                print('Got axis: ', self.last_axis)
            print()

    def write_python_class_file(self):
        pyth_filename = None
        outfile = None
        while pyth_filename is None:
            print("Now we will write these values to a new python file.")
            pyth_filename = input("What is the name of python file to create joystick code? [default: my_joystick.py]")
            if len(pyth_filename) == 0:
                pyth_filename = 'my_joystick.py'
            print('using filename:', pyth_filename)
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
            classname = input("What is the name of joystick class? [default: MyJoystick] ")
            if len(classname) == 0:
                classname = "MyJoystick"
            file_header = \
            '''
from donkeycar.parts.controller import Joystick, JoystickController


class %s(Joystick):
    #An interface to a physical joystick available at /dev/input/js0
    def __init__(self, *args, **kwargs):
        super(%s, self).__init__(*args, **kwargs)

            \n''' % (classname, classname )

            outfile.write(file_header)

            outfile.write('        self.button_names = {\n')
            for key, value in self.js.button_names.items():
                outfile.write("            %s : '%s',\n" % (str(hex(key)), str(value)))
            outfile.write('        }\n\n\n')
            
            outfile.write('        self.axis_names = {\n')

            for key, value in self.js.axis_names.items():
                outfile.write("            %s : '%s',\n" % (str(hex(key)), str(value)))
            outfile.write('        }\n\n\n')

            js_controller = \
            '''
class %sController(JoystickController):
    #A Controller object that maps inputs to actions
    def __init__(self, *args, **kwargs):
        super(%sController, self).__init__(*args, **kwargs)


    def init_js(self):
        #attempt to init joystick
        try:
            self.js = %s(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        #init set of mapping from buttons to function calls
            \n''' % (classname, classname, classname)

            outfile.write(js_controller)

            outfile.write('        self.button_down_trigger_map = {\n')
            for button, control in self.mapped_controls:
                outfile.write("            '%s' : self.%s,\n" % (str(button), str(control)))
            outfile.write('        }\n\n\n')
            
            outfile.write('        self.axis_trigger_map = {\n')
            for axis, control in self.axis_map:
                outfile.write("            '%s' : self.%s,\n" % (str(axis), str(control)))
            outfile.write('        }\n\n\n')

            outfile.close()
            print(pyth_filename, "written.")

    def map_control_axis(self, control_name, control_fn):
        while True:
            axis = self.get_axis_action('Move the controller axis you wish to use for %s. Continue moving for 2 seconds.' % control_name)
            
            mapped = False

            if axis is None:
                print("No mapping for %s." % control_name)
            else:
                #print("axis", axis)
                code = self.get_code_from_button(axis)
                for key, value in self.js.axis_names.items():
                    #print('key', key, 'value', value)
                    if key == code or value == code:
                        print('Mapping %s to %s.\n' % (value, control_name))
                        mapped = value
                        break
            if mapped:
                ret = input('Is this mapping ok? (y, N) ')
                if ret.upper() == 'Y':
                    self.axis_map.append((mapped, control_fn))
                    return
            else:
                ret = input('axis not recognized. try again? (Y, n) ')
                if ret.upper() == 'N':
                    return


    def map_steering_throttle(self):

        self.axis_map = []

        self.print_config()
        print()
        print('Now we will create a mapping of controls to actions.\n')

        print("First steering.")
        self.map_control_axis("steering", "set_steering")

        self.clear_scr()
        self.print_config()
        print()
        print("Next throttle.")
        self.map_control_axis("throttle", "set_throttle")


    def map_button_controls(self):
        unmapped_controls = [\
            ('toggle_mode','changes the drive mode between user, local, and local_angle'),
            ('erase_last_N_records','erases the last 100 records while driving'),
            ('emergency_stop','executes a full back throttle to bring car to a quick stop'),
            ('increase_max_throttle','increases the max throttle, also used for constant throttle val'),
            ('decrease_max_throttle','decreases the max throttle, also used for constant throttle val'),
            ('toggle_constant_throttle', 'toggle the mode of supplying constant throttle'),
            ('toggle_manual_recording','toggles recording records on and off')
        ]
        
        self.mapped_controls = []
        self.print_config()
        print()
        print("Next we are going to assign button presses to controls.")
        print()

        while len(unmapped_controls) > 0:

            pt = PrettyTable()
            pt.field_names = ['Num', 'Control', 'Help']
            print("Unmapped Controls:")
            for i, td in enumerate(unmapped_controls):
                control, help = td
                pt.add_row([i + 1, control, help])
            print(pt)

            print()
            try:
                ret = " "
                while (not ret.isdigit() and ret.upper() != 'D') or (ret.isdigit() and (int(ret) < 1 or int(ret) > len(unmapped_controls))):
                    ret = input("Press the number of control to map (1-%d). D when done. " % len(unmapped_controls))

                if ret.upper() == 'D':
                    break

                iControl = int(ret) - 1
            except:
                continue

            
            print('Press the button to map to control:', unmapped_controls[iControl][0])
            self.get_button_press()

            if self.last_button is None:
                print("No button was pressed in last 10 seconds.")
                ret = input("Keep mapping commands? [Y, n]")
                if ret == 'n':
                    break
            else:
                code = self.get_code_from_button(self.last_button)
                if code in self.js.button_names: 
                    button_name = self.js.button_names[code]
                else:
                    button_name = self.last_button
                self.mapped_controls.append((button_name, unmapped_controls[iControl][0]))
                unmapped_controls.pop(iControl)
                self.clear_scr()
                self.print_config()
                print()

        print('done mapping controls')
        print()

    def revisit_topic(self):
        done = False
        while not done:
            self.clear_scr()
            self.print_config()
            print("Now we are nearly done! Are you happy with this config or would you like to revisit a topic?")
            print("H)appy, please continue to write out python file.")
            print("B)uttons need renaming.")
            print("A)xes need renaming.")
            print("T)hrottle and steering need remap.")
            print("R)emap buttons to controls.")
            
            ret = input("Select option ").upper()
            if ret == 'H':
                done = True
            elif ret == 'B':
                self.name_buttons()
            elif ret == 'A':
                self.name_axes()
            elif ret == 'T':
                self.map_steering_throttle()
            elif ret == 'R':
                self.map_button_controls()          


    def get_axis_action(self, prompt):
        done = False        
        while not done:
            print(prompt)
            ret = input("Hit Enter to begin. D when done. ")
            if ret.upper() == 'D':
                return None

            most_movement = self.get_axis_move()

            if most_movement is None:
                print("Didn't detect any movement.")
                res = input("Try again? [Y/n]: ")
                if res == "n":
                    return None
                else:
                    continue
            else:
                return most_movement


    def shutdown(self):
        self.running = False
        if self.thread:
            self.thread = None

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

