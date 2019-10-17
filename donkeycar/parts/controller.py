
import os
import array
import time
import struct
import random
from threading import Thread
import logging

from prettytable import PrettyTable

#import for syntactical ease
from donkeycar.parts.web_controller.web import LocalWebController

class Joystick(object):
    '''
    An interface to a physical joystick
    '''
    def __init__(self, dev_fn='/dev/input/js0'):
        self.axis_states = {}
        self.button_states = {}
        self.axis_names = {}
        self.button_names = {}
        self.axis_map = []
        self.button_map = []
        self.jsdev = None
        self.dev_fn = dev_fn


    def init(self):
        try:
            from fcntl import ioctl
        except ModuleNotFoundError:
            self.num_axes = 0
            self.num_buttons = 0
            print("no support for fnctl module. joystick not enabled.")
            return False

        if not os.path.exists(self.dev_fn):
            print(self.dev_fn, "is missing")
            return False

        '''
        call once to setup connection to device and map buttons
        '''
        # Open the joystick device.
        print('Opening %s...' % self.dev_fn)
        self.jsdev = open(self.dev_fn, 'rb')

        # Get the device name.
        buf = array.array('B', [0] * 64)
        ioctl(self.jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
        self.js_name = buf.tobytes().decode('utf-8')
        print('Device name: %s' % self.js_name)

        # Get number of axes and buttons.
        buf = array.array('B', [0])
        ioctl(self.jsdev, 0x80016a11, buf) # JSIOCGAXES
        self.num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(self.jsdev, 0x80016a12, buf) # JSIOCGBUTTONS
        self.num_buttons = buf[0]

        # Get the axis map.
        buf = array.array('B', [0] * 0x40)
        ioctl(self.jsdev, 0x80406a32, buf) # JSIOCGAXMAP

        for axis in buf[:self.num_axes]:
            axis_name = self.axis_names.get(axis, 'unknown(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            self.axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(self.jsdev, 0x80406a34, buf) # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = self.button_names.get(btn, 'unknown(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0
            #print('btn', '0x%03x' % btn, 'name', btn_name)

        return True


    def show_map(self):
        '''
        list the buttons and axis found on this joystick
        '''
        print ('%d axes found: %s' % (self.num_axes, ', '.join(self.axis_map)))
        print ('%d buttons found: %s' % (self.num_buttons, ', '.join(self.button_map)))


    def poll(self):
        '''
        query the state of the joystick, returns button which was pressed, if any,
        and axis which was moved, if any. button_state will be None, 1, or 0 if no changes,
        pressed, or released. axis_val will be a float from -1 to +1. button and axis will
        be the string label determined by the axis map in init.
        '''
        button = None
        button_state = None
        axis = None
        axis_val = None

        if self.jsdev is None:
            return button, button_state, axis, axis_val

        # Main event loop
        evbuf = self.jsdev.read(8)

        if evbuf:
            tval, value, typev, number = struct.unpack('IhBB', evbuf)

            if typev & 0x80:
                #ignore initialization event
                return button, button_state, axis, axis_val

            if typev & 0x01:
                button = self.button_map[number]
                #print(tval, value, typev, number, button, 'pressed')
                if button:
                    self.button_states[button] = value
                    button_state = value
                    logging.info("button: %s state: %d" % (button, value))

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue
                    logging.debug("axis: %s val: %f" % (axis, fvalue))

        return button, button_state, axis, axis_val


class PyGameJoystick(object):
    def __init__(self, which_js=0):
        import pygame

        # Initialize the joysticks
        pygame.joystick.init()

        self.joystick = pygame.joystick.Joystick(which_js)
        self.joystick.init()
        name = self.joystick.get_name()
        print("detected joystick device:", name)

        self.axis_states = [ 0.0 for i in range(self.joystick.get_numaxes())]
        self.button_states = [ 0 for i in range(self.joystick.get_numbuttons() + self.joystick.get_numhats() * 4)]
        self.axis_names = {}
        self.button_names = {}


    def poll(self):
        button = None
        button_state = None
        axis = None
        axis_val = None

        self.joystick.init()

        for i in range( self.joystick.get_numaxes() ):
            val = self.joystick.get_axis( i )
            if self.axis_states[i] != val:
                axis = self.axis_names[i]
                axis_val = val
                self.axis_states[i] = val
                logging.debug("axis: %s val: %f" % (axis, val))


        for i in range( self.joystick.get_numbuttons() ):
            state = self.joystick.get_button( i )
            if self.button_states[i] != state:
                button = self.button_names[i]
                button_state = state
                self.button_states[i] = state
                logging.info("button: %s state: %d" % (button, state))

        for i in range( self.joystick.get_numhats() ):
            hat = self.joystick.get_hat( i )
            horz, vert = hat
            iBtn = self.joystick.get_numbuttons() + (i * 4)
            states = (horz == -1, horz == 1, vert == -1, vert == 1)
            for state in states:
                state = int(state)
                if self.button_states[iBtn] != state:
                    button = self.button_names[iBtn]
                    button_state = state
                    self.button_states[iBtn] = state
                iBtn += 1

        return button, button_state, axis, axis_val


class JoystickCreator(Joystick):
    '''
    A Helper class to create a new joystick mapping
    '''
    def __init__(self, *args, **kwargs):
        super(JoystickCreator, self).__init__(*args, **kwargs)

        self.axis_names = {}
        self.button_names = {}

    def poll(self):

        button, button_state, axis, axis_val = super(JoystickCreator, self).poll()

        return button, button_state, axis, axis_val


class PS3JoystickOld(Joystick):
    '''
    An interface to a physical PS3 joystick available at /dev/input/js0
    Contains mapping that worked for Raspian Jessie drivers
    '''
    def __init__(self, *args, **kwargs):
        super(PS3JoystickOld, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00 : 'left_stick_horz',
            0x01 : 'left_stick_vert',
            0x02 : 'right_stick_horz',
            0x05 : 'right_stick_vert',

            0x1a : 'tilt_x',
            0x1b : 'tilt_y',
            0x3d : 'tilt_a',
            0x3c : 'tilt_b',

            0x32 : 'L1_pressure',
            0x33 : 'R1_pressure',
            0x31 : 'R2_pressure',
            0x30 : 'L2_pressure',

            0x36 : 'cross_pressure',
            0x35 : 'circle_pressure',
            0x37 : 'square_pressure',
            0x34 : 'triangle_pressure',

            0x2d : 'dpad_r_pressure',
            0x2e : 'dpad_d_pressure',
            0x2c : 'dpad_u_pressure',
        }

        self.button_names = {
            0x120 : 'select',
            0x123 : 'start',
            0x2c0 : 'PS',

            0x12a : 'L1',
            0x12b : 'R1',
            0x128 : 'L2',
            0x129 : 'R2',
            0x121 : 'L3',
            0x122 : 'R3',

            0x12c : "triangle", 
            0x12d : "circle",
            0x12e : "cross",
            0x12f : 'square',

            0x124 : 'dpad_up',
            0x126 : 'dpad_down',
            0x127 : 'dpad_left',
            0x125 : 'dpad_right',
        }


class PS3Joystick(Joystick):
    '''
    An interface to a physical PS3 joystick available at /dev/input/js0
    Contains mapping that work for Raspian Stretch drivers
    '''
    def __init__(self, *args, **kwargs):
        super(PS3Joystick, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00 : 'left_stick_horz',
            0x01 : 'left_stick_vert',
            0x03 : 'right_stick_horz',
            0x04 : 'right_stick_vert',

            0x02 : 'L2_pressure',
            0x05 : 'R2_pressure',
        }

        self.button_names = {
           0x13a : 'select', #8 314
           0x13b : 'start', #9 315
           0x13c : 'PS', #a  316

           0x136 : 'L1', #4 310
           0x137 : 'R1', #5 311
           0x138 : 'L2', #6 312
           0x139 : 'R2', #7 313
           0x13d : 'L3', #b 317
           0x13e : 'R3', #c 318

           0x133 : "triangle",  #2 307
           0x131 : "circle",    #1 305
           0x130 : "cross",    #0 304
           0x134 : 'square',    #3 308

           0x220 : 'dpad_up', #d 544
           0x221 : 'dpad_down', #e 545
           0x222 : 'dpad_left', #f 546
           0x223 : 'dpad_right', #10 547
       }


class PS4Joystick(Joystick):
    '''
    An interface to a physical PS4 joystick available at /dev/input/js0
    '''
    def __init__(self, *args, **kwargs):
        super(PS4Joystick, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00 : 'left_stick_horz',
            0x01 : 'left_stick_vert',
            0x02 : 'right_stick_horz',
            0x05 : 'right_stick_vert',

            0x03 : 'left_trigger_axis',
            0x04 : 'right_trigger_axis',

            0x10 : 'dpad_leftright',
            0x11 : 'dpad_updown',

            0x19 : 'tilt_a',
            0x1a : 'tilt_b',
            0x1b : 'tilt_c',

            0x06 : 'motion_a',
            0x07 : 'motion_b',
            0x08 : 'motion_c',
        }

        self.button_names = {

            0x130 : 'square',
            0x131 : 'cross',
            0x132 : 'circle',
            0x133 : 'triangle',

            0x134 : 'L1',
            0x135 : 'R1',
            0x136 : 'L2',
            0x137 : 'R2',
            0x13a : 'L3',
            0x13b : 'R3',

            0x13d : 'pad',
            0x138 : 'share',
            0x139 : 'options',
            0x13c : 'PS',
        }


class PS3JoystickPC(Joystick):
    '''
    An interface to a physical PS3 joystick available at /dev/input/js1
    Seems to exhibit slightly different codes because driver is different?
    when running from ubuntu 16.04, it will interfere w mouse until:
    xinput set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0
    It also wants /dev/input/js1 device filename, not js0
    '''
    def __init__(self, *args, **kwargs):
        super(PS3JoystickPC, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00 : 'left_stick_horz',
            0x01 : 'left_stick_vert',
            0x03 : 'right_stick_horz',
            0x04 : 'right_stick_vert',

            0x1a : 'tilt_x',
            0x1b : 'tilt_y',
            0x3d : 'tilt_a',
            0x3c : 'tilt_b',

            0x32 : 'L1_pressure',
            0x33 : 'R1_pressure',
            0x05 : 'R2_pressure',
            0x02 : 'L2_pressure',

            0x36 : 'cross_pressure',
            0x35 : 'circle_pressure',
            0x37 : 'square_pressure',
            0x34 : 'triangle_pressure',

            0x2d : 'dpad_r_pressure',
            0x2e : 'dpad_d_pressure',
            0x2c : 'dpad_u_pressure',
        }

        self.button_names = {
            0x13a : 'select',
            0x13b : 'start',
            0x13c : 'PS',

            0x136 : 'L1',
            0x137 : 'R1',
            0x138 : 'L2',
            0x139 : 'R2',
            0x13d : 'L3',
            0x13e : 'R3',

            0x133 : "triangle",
            0x131 : "circle",
            0x130 : "cross",
            0x134 : 'square',

            0x220 : 'dpad_up',
            0x221 : 'dpad_down',
            0x222 : 'dpad_left',
            0x223 : 'dpad_right',
        }


class PyGamePS3Joystick(PyGameJoystick):
    '''
    An interface to a physical PS3 joystick available via pygame
    Windows setup: https://github.com/nefarius/ScpToolkit/releases/tag/v1.6.238.16010
    '''
    def __init__(self, *args, **kwargs):
        super(PyGamePS3Joystick, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00 : 'left_stick_horz',
            0x01 : 'left_stick_vert',
            0x02 : 'analog_trigger',
            0x03 : 'right_stick_vert',
            0x04 : 'right_stick_horz',
        }

        self.button_names = {
            0 : "cross",
            1 : "circle",
            2 : 'square',
            3 : "triangle",

            6 : 'select',
            7 : 'start',

            4 : 'L1',
            5 : 'R1',
            8 : 'L3',
            9 : 'R3',

            10 : 'dpad_left',
            11 : 'dpad_right',
            12 : 'dpad_down',
            13 : 'dpad_up',
        }


class XboxOneJoystick(Joystick):
    '''
    An interface to a physical joystick 'Xbox Wireless Controller' controller.
    This will generally show up on /dev/input/js0.
    - Note that this code presumes the built-in linux driver for 'Xbox Wireless Controller'.
      There is another user land driver called xboxdrv; this code has not been tested
      with that driver.
    - Note that this controller requires that the bluetooth disable_ertm parameter
      be set to true; to do this:
      - edit /etc/modprobe.d/xbox_bt.conf
      - add the line: options bluetooth disable_ertm=1
      - reboot to tha this take affect.
      - after reboot you can vertify that disable_ertm is set to true entering this
        command oin a terminal: cat /sys/module/bluetooth/parameters/disable_ertm
      - the result should print 'Y'.  If not, make sure the above steps have been done corretly.

    credit:
    https://github.com/Ezward/donkeypart_ps3_controller/blob/master/donkeypart_ps3_controller/part.py
    '''
    def __init__(self, *args, **kwargs):
        super(XboxOneJoystick, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00: 'left_stick_horz',
            0x01: 'left_stick_vert',
            0x02: 'right_stick_horz',
            0x05: 'right_stick_vert',
            0x09: 'right_trigger',
            0x0a: 'left_trigger',
            0x10: 'dpad_horz',
            0x11: 'dpad_vert',
        }

        self.button_names = {
            0x130: 'a_button',
            0x131: 'b_button',
            0x133: 'x_button',
            0x134: 'y_button',
            0x136: 'left_shoulder',
            0x137: 'right_shoulder',
            0x13b: 'options',
        }


class LogitechJoystick(Joystick):
    '''
    An interface to a physical Logitech joystick available at /dev/input/js0
    Contains mapping that work for Raspian Stretch drivers
    Tested with Logitech Gamepad F710
    https://www.amazon.com/Logitech-940-000117-Gamepad-F710/dp/B0041RR0TW
    credit:
    https://github.com/kevkruemp/donkeypart_logitech_controller/blob/master/donkeypart_logitech_controller/part.py
    '''
    def __init__(self, *args, **kwargs):
        super(LogitechJoystick, self).__init__(*args, **kwargs)

        self.axis_names = {
            0x00: 'left_stick_horz',
            0x01: 'left_stick_vert',
            0x03: 'right_stick_horz',
            0x04: 'right_stick_vert',

            0x02: 'L2_pressure',
            0x05: 'R2_pressure',

            0x10: 'dpad_leftright', # 1 is right, -1 is left
            0x11: 'dpad_up_down', # 1 is down, -1 is up
        }

        self.button_names = {
            0x13a: 'back',  # 8 314
            0x13b: 'start',  # 9 315
            0x13c: 'Logitech',  # a  316

            0x130: 'A',
            0x131: 'B',
            0x133: 'X',
            0x134: 'Y',

            0x136: 'L1',
            0x137: 'R1',

            0x13d: 'left_stick_press',
            0x13e: 'right_stick_press',
        }


class Nimbus(Joystick):
    #An interface to a physical joystick available at /dev/input/js0
    #contains mappings that work for the SteelNimbus joystick
    #on Jetson TX2, JetPack 4.2, Ubuntu 18.04
    def __init__(self, *args, **kwargs):
        super(Nimbus, self).__init__(*args, **kwargs)

        self.button_names = {
            0x130 : 'a',
            0x131 : 'b',
            0x132 : 'x',
            0x133 : 'y',
            0x135 : 'R1',
            0x137 : 'R2',
            0x134 : 'L1',
            0x136 : 'L2',
        }

        self.axis_names = {
            0x0 : 'lx',
            0x1 : 'ly',
            0x2 : 'rx',
            0x5 : 'ry',
            0x11 : 'hmm',
            0x10 : 'what',
        }


class WiiU(Joystick):
    #An interface to a physical joystick available at /dev/input/js0
    #contains mappings may work for the WiiUPro joystick
    #This was taken from
    #https://github.com/autorope/donkeypart_bluetooth_game_controller/blob/master/donkeypart_bluetooth_game_controller/wiiu_config.yml
    #and need testing!
    def __init__(self, *args, **kwargs):
        super(WiiU, self).__init__(*args, **kwargs)

        self.button_names = {
            305: 'A',
            304: 'B',
            307: 'X',
            308: 'Y',
            312: 'LEFT_BOTTOM_TRIGGER',
            310: 'LEFT_TOP_TRIGGER',
            313: 'RIGHT_BOTTOM_TRIGGER',
            311: 'RIGHT_TOP_TRIGGER',
            317: 'LEFT_STICK_PRESS',
            318: 'RIGHT_STICK_PRESS',
            314: 'SELECT',
            315: 'START',
            547: 'PAD_RIGHT',
            546: 'PAD_LEFT',
            544: 'PAD_UP',
            545: 'PAD_DOWN',
            316: 'HOME',
          }

        self.axis_names = {
            0: 'LEFT_STICK_X',
            1: 'LEFT_STICK_Y',
            3: 'RIGHT_STICK_X',
            4: 'RIGHT_STICK_Y',
        }


class JoystickController(object):
    '''
    JoystickController is a base class. You will not use this class directly,
    but instantiate a flavor based on your joystick type. See classes following this.

    Joystick client using access to local physical input. Maps button
    presses into actions and takes action. Interacts with the Donkey part
    framework.
    '''

    ES_IDLE = -1
    ES_START = 0
    ES_THROTTLE_NEG_ONE = 1
    ES_THROTTLE_POS_ONE = 2
    ES_THROTTLE_NEG_TWO = 3


    def __init__(self, poll_delay=0.0,
                 throttle_scale=1.0,
                 steering_scale=1.0,
                 throttle_dir=-1.0,
                 dev_fn='/dev/input/js0',
                 auto_record_on_throttle=True):

        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.poll_delay = poll_delay
        self.running = True
        self.last_throttle_axis_val = 0
        self.throttle_scale = throttle_scale
        self.steering_scale = steering_scale
        self.throttle_dir = throttle_dir
        self.recording = False
        self.constant_throttle = False
        self.auto_record_on_throttle = auto_record_on_throttle
        self.dev_fn = dev_fn
        self.js = None
        self.tub = None
        self.num_records_to_erase = 100
        self.estop_state = self.ES_IDLE
        self.chaos_monkey_steering = None
        self.dead_zone = 0.0

        self.button_down_trigger_map = {}
        self.button_up_trigger_map = {}
        self.axis_trigger_map = {}
        self.init_trigger_maps()

        self.shiftKeyHistory=[]
        self.shiftModeHistory={}
        self.menulist=[]
        self.menudescr=[]
        self.shiftkey=""
        self.V=None
        self.cfg=None

    def init_js(self):
        '''
        Attempt to init joystick. Should be definied by derived class
        Should return true on successfully created joystick object
        '''
        raise(Exception("Subclass needs to define init_js"))


    def init_trigger_maps(self):
        '''
        Creating mapping of buttons to functions.
        Should be definied by derived class
        '''
        raise(Exception("init_trigger_maps"))


    def set_deadzone(self, val):
        '''
        sets the minimim throttle for recording
        '''
        self.dead_zone = val


    def print_controls(self):
        '''
        print the mapping of buttons and axis to functions
        '''
        pt = PrettyTable()
        pt.field_names = ["control", "action"]
        for button, control in self.button_down_trigger_map.items():
            pt.add_row([button, control.__name__])
        for axis, control in self.axis_trigger_map.items():
            pt.add_row([axis, control.__name__])
        print("Joystick Controls:")
        print(pt)

        # print("Joystick Controls:")
        # print("On Button Down:")
        # print(self.button_down_trigger_map)
        # print("On Button Up:")
        # print(self.button_up_trigger_map)
        # print("On Axis Move:")
        # print(self.axis_trigger_map)


    def set_button_down_trigger(self, button, func):
        '''
        assign a string button descriptor to a given function call
        '''
        self.button_down_trigger_map[button] = func


    def set_button_up_trigger(self, button, func):
        '''
        assign a string button descriptor to a given function call
        '''
        self.button_up_trigger_map[button] = func


    def set_axis_trigger(self, axis, func):
        '''
        assign a string axis descriptor to a given function call
        '''
        self.axis_trigger_map[axis] = func


    def set_tub(self, tub):
        self.tub = tub


    def erase_last_N_records(self):
        if self.tub is not None:
            try:
                self.tub.erase_last_n_records(self.num_records_to_erase)
                print('erased last %d records.' % self.num_records_to_erase)
            except:
                print('failed to erase')


    def on_throttle_changes(self):
        '''
        turn on recording when non zero throttle in the user mode.
        '''
        if self.auto_record_on_throttle:
            self.recording = (abs(self.throttle) > self.dead_zone and self.mode == 'user')


    def emergency_stop(self):
        '''
        initiate a series of steps to try to stop the vehicle as quickly as possible
        '''
        print('E-Stop!!!')
        self.mode = "user"
        self.recording = False
        self.constant_throttle = False
        self.estop_state = self.ES_START
        self.throttle = 0.0


    def update(self):
        '''
        poll a joystick for input events
        '''

        #wait for joystick to be online
        while self.running and self.js is None and not self.init_js():
            time.sleep(3)

        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if axis is not None and axis in self.axis_trigger_map:
                '''
                then invoke the function attached to that axis
                '''
                self.axis_trigger_map[axis](axis_val)

            if button and button_state >= 1 and button in self.button_down_trigger_map:
                '''
                then invoke the function attached to that button
                '''
                self.button_down_trigger_map[button]()

            if button and button_state == 0 and button in self.button_up_trigger_map:
                '''
                then invoke the function attached to that button
                '''
                self.button_up_trigger_map[button]()

            time.sleep(self.poll_delay)

    def update_adv(self):
        '''
        poll a joystick for input events
        '''
        self.shiftkey=""
        #wait for joystick to be online
        while self.running and self.js is None and not self.init_js():
            time.sleep(3)

        while self.running:
            button, button_state, axis, axis_val = self.js.poll()
            if axis is not None :
                if axis in self.key_translate_map:      
                   axis=self.key_translate_map[axis]  # This would not be needed if we standardized the axis names... 
               
                shifted_axis=self.shiftkey+axis
                if  shifted_axis in self.axis_trigger_map:
                   if type(self.axis_trigger_map[shifted_axis]) is str :
                       funcstr=self.axis_trigger_map[shifted_axis]
                       funcstr2=funcstr.replace("%val%",str(axis_val))
                       exec(funcstr2)
                   else:
                      self.axis_trigger_map[shifted_axis](axis_val)
                else:
                   if axis[:1]=="|":
                       k,dp1,dp2= axis.split("|")
                       button,button_state= self.buttonize(axis_val,dp1,dp2,dp1+"_"+dp2)

            if button and button_state >= 1 :
                '''
                then invoke the function attached to that button
                '''
                if button in self.key_translate_map:
                   button=self.key_translate_map[button] # This would not be needed if we standardized the button names...

                button=self.shiftkey+button
                if button in self.button_down_trigger_map:
                    if type(self.button_down_trigger_map[button]) is str :
                        funcstr=self.button_down_trigger_map[button]
                        exec(funcstr)
                    else:
                        self.button_down_trigger_map[button]
 
                     

            if button and button_state == 0:
                '''
                then invoke the function attached to that button
                '''
                if button in self.key_translate_map:
                   button=self.key_translate_map[button]

                if button in self.shiftModeHistory :
                  self.shift_out(button)
                else:
                  button=self.shiftkey+button
                  if button in self.button_up_trigger_map:
                     if type(self.button_up_trigger_map[button]) is str :
                        funcstr=self.button_up_trigger_map[button]
                        exec(funcstr)
                     else:
                        self.button_up_trigger_map[button]

            time.sleep(self.poll_delay)

    def buttonize(self,axis_val,keypad1,keypad2,keypadup):
        if axis_val==1 : 
           button=keypad2
           button_state=1
        elif axis_val==-1: 
           button=keypad1
           button_state=1
        else :
           button=keypadup
           button_state=0
        return button,button_state
 
    def display(self,mystring):
        print (mystring)
        self.set_input_val("DisplayStr",mystring) # publish the display in case a part would want to display on a oled screen ...

    def menu_in(self,Mode,descr=""):
        self.shiftkey=Mode+"+"
        if descr !="" :print(descr)

    def menu_next(self,MenuString):
        i=self.menulist.index(MenuString)
        l=len(self.menulist)-1
        if i>=l : 
            nm=0
        else : 
            nm=i+1
        self.menu_in(self.menulist[nm],self.menudescr[nm])
        
    def menu_register(self,MenuString,button_down_trigger_map,button_up_trigger_map,axis_trigger_map,descr=""):
        self.menulist.append(MenuString)
        self.menudescr.append(descr)
        for t in button_up_trigger_map:
            self.button_up_trigger_map[t]=button_up_trigger_map[t]
        for t in button_down_trigger_map:
            self.button_down_trigger_map[t]=button_down_trigger_map[t]
        for t in axis_trigger_map:
            self.axis_trigger_map[t]=axis_trigger_map[t] 


    def shift_in(self,btn,Mode,descr=""):
        self.shiftKeyHistory.append(btn)
        self.shiftModeHistory[btn]=self.shiftkey
        self.shiftkey=Mode+"+"
        if descr !="" :print(descr)

    def shift_out(self,btn):
        i=self.shiftKeyHistory.index(btn)
        l=len(self.shiftKeyHistory)
        self.shiftkey=self.shiftModeHistory[btn]
        for k in range(i,l):
          del self.shiftModeHistory[ self.shiftKeyHistory[k]]
        self.shiftKeyHistory=self.shiftKeyHistory[0:i]

    def inc_input_val(self,varstring,increment,maxvalue) :
        if self.V.mem.get ([varstring])[0] is None :  self.V.mem.put ([varstring],0)
        newval=self.V.mem.get ([varstring])[0]+increment
        if newval>maxvalue:newval=maxvalue
        self.V.mem.put ([varstring],newval)
        self.display (varstring + "=" + str(newval))

    def dec_input_val(self,varstring,increment,minvalue) :
        if self.V.mem.get ([varstring])[0] is None :  self.V.mem.put ([varstring],0)
        newval=self.V.mem.get ([varstring])[0]-increment
        if newval<minvalue:newval=minvalue
        self.V.mem.put ([varstring],newval)
        self.display (varstring + "=" + str(newval))

    def set_input_val(self,varstring,newval):
        self.V.mem.put ([varstring],newval)
   
    def inc_cfg_val(self,varstring,varstep,varmax):
        if not hasattr(self.cfg,varstring): setattr(self.cfg,varstring,0)
        newval=getattr(self.cfg,varstring)+varstep
        if newval>varmax:newval=varmax
        setattr(self.cfg,varstring,newval)
        self.display(varstring + "=" + str(newval))

    def dec_cfg_val(self,varstring,varstep,varmin):
        if not hasattr(self.cfg,varstring):setattr(self.cfg,varstring,0)
        newval=getattr(self.cfg,varstring)-varstep
        if newval<varmin:newval=varmin
        setattr(self.cfg,varstring,newval)
        self.display(varstring + "=" + str(newval))

    def set_cfg_val(self,varstring,newval) :
        setattr(self.cfg,varstring,newval)

    def get_part(self,ClassName="",ObjName=""):
        for entry in self.V.parts:
           p = entry['part']            
           if (p.__class__.__name__ )== ClassName :
              if (hasattr(p,"ObjName") ):
                 if p.ObjName==ObjName:
                     return p
              else: 
                 if ObjName=="" or ObjName is None : return p	

    def inc_part_val(self,varname,  step, vmax,ObjName=None,ClassName=None):
        p=self.get_part(ObjName=ObjName,ClassName=ClassName)
        if p is not None : v=getattr(p,varname)+step
        if v>vmax : v=vmax
        setattr(p,varname,v)
        self.display(varname+"="+str(v))

    def dec_part_val(self,varname,  step, vmin,ObjName=None,ClassName=None):
        p=self.get_part(ObjName=ObjName,ClassName=ClassName)
        if p is not None : v=getattr(p,varname)-step
        if v<vmin : v=vmin
        setattr(p,varname,v)
        self.display(varname+"="+str(v))

    def set_part_val(self,varname,newval,ObjName=None,ClassName=None):
        p=self.get_part(ObjName=ObjName,ClassName=ClassName)
        if p is not None :setattr(p,varname,newval)

    def copy_cfg_to_part(self,cfg_varstring,part_varstring,ObjName=None,ClassName=None ):
        p=self.get_part(ObjName=ObjName,ClassName=ClassName)
        if p is not None :setattr(p,part_varstring,getattr(self.cfg,cfg_varstring))

    def print_cfg_vals(self,varstrings):
        val_array= varstrings.split(",")
        for valstr in val_array: 
          if hasattr(self.cfg,valstr):      
             self.display(valstr+"="+str(getattr(self.cfg,valstr)))


    def set_steering(self, axis_val):
        self.angle = self.steering_scale * axis_val
        #print("angle", self.angle)


    def set_throttle(self, axis_val):
        #this value is often reversed, with positive value when pulling down
        self.last_throttle_axis_val = axis_val
        self.throttle = (self.throttle_dir * axis_val * self.throttle_scale)
        #print("throttle", self.throttle)
        self.on_throttle_changes()


    def toggle_manual_recording(self):
        '''
        toggle recording on/off
        '''
        if self.auto_record_on_throttle:
            print('auto record on throttle is enabled.')
        elif self.recording:
            self.recording = False
        else:
            self.recording = True

        print('recording:', self.recording)


    def increase_max_throttle(self):
        '''
        increase throttle scale setting
        '''
        self.throttle_scale = round(min(1.0, self.throttle_scale + 0.01), 2)
        if self.constant_throttle:
            self.throttle = self.throttle_scale
            self.on_throttle_changes()
        else:
            self.throttle = (self.throttle_dir * self.last_throttle_axis_val * self.throttle_scale)

        print('throttle_scale:', self.throttle_scale)


    def decrease_max_throttle(self):
        '''
        decrease throttle scale setting
        '''
        self.throttle_scale = round(max(0.0, self.throttle_scale - 0.01), 2)
        if self.constant_throttle:
            self.throttle = self.throttle_scale
            self.on_throttle_changes()
        else:
            self.throttle = (self.throttle_dir * self.last_throttle_axis_val * self.throttle_scale)

        print('throttle_scale:', self.throttle_scale)


    def toggle_constant_throttle(self):
        '''
        toggle constant throttle
        '''
        if self.constant_throttle:
            self.constant_throttle = False
            self.throttle = 0
            self.on_throttle_changes()
        else:
            self.constant_throttle = True
            self.throttle = self.throttle_scale
            self.on_throttle_changes()
        print('constant_throttle:', self.constant_throttle)


    def toggle_mode(self):
        '''
        switch modes from:
        user: human controlled steer and throttle
        local_angle: ai steering, human throttle
        local: ai steering, ai throttle
        '''
        if self.mode == 'user':
            self.mode = 'local_angle'
        elif self.mode == 'local_angle':
            self.mode = 'local'
        else:
            self.mode = 'user'
        print('new mode:', self.mode)


    def chaos_monkey_on_left(self):
        self.chaos_monkey_steering = -0.2


    def chaos_monkey_on_right(self):
        self.chaos_monkey_steering = 0.2


    def chaos_monkey_off(self):
        self.chaos_monkey_steering = None


    def run_threaded(self, img_arr=None):
        self.img_arr = img_arr

        '''
        process E-Stop state machine
        '''
        if self.estop_state > self.ES_IDLE:
            if self.estop_state == self.ES_START:
                self.estop_state = self.ES_THROTTLE_NEG_ONE
                return 0.0, -1.0 * self.throttle_scale, self.mode, False
            elif self.estop_state == self.ES_THROTTLE_NEG_ONE:
                self.estop_state = self.ES_THROTTLE_POS_ONE
                return 0.0, 0.01, self.mode, False
            elif self.estop_state == self.ES_THROTTLE_POS_ONE:
                self.estop_state = self.ES_THROTTLE_NEG_TWO
                self.throttle = -1.0 * self.throttle_scale
                return 0.0, self.throttle, self.mode, False
            elif self.estop_state == self.ES_THROTTLE_NEG_TWO:
                self.throttle += 0.05
                if self.throttle >= 0.0:
                    self.throttle = 0.0
                    self.estop_state = self.ES_IDLE
                return 0.0, self.throttle, self.mode, False

        if self.chaos_monkey_steering is not None:
            return self.chaos_monkey_steering, self.throttle, self.mode, False

        return self.angle, self.throttle, self.mode, self.recording


    def run(self, img_arr=None):
        raise Exception("We expect for this part to be run with the threaded=True argument.")
        return None, None, None, None


    def shutdown(self):
        #set flag to exit polling thread, then wait a sec for it to leave
        self.running = False
        time.sleep(0.5)


class JoystickCreatorController(JoystickController):
    '''
    A Controller object helps create a new controller object and mapping
    '''
    def __init__(self, *args, **kwargs):
        super(JoystickCreatorController, self).__init__(*args, **kwargs)


    def init_js(self):
        '''
        attempt to init joystick
        '''
        try:
            self.js = JoystickCreator(self.dev_fn)
            if not self.js.init():
                self.js = None
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None

        return self.js is not None


    def init_trigger_maps(self):
        '''
        init set of mapping from buttons to function calls
        '''
        pass


class PS3JoystickController(JoystickController):
    '''
    A Controller object that maps inputs to actions
    '''
    def __init__(self, *args, **kwargs):
        super(PS3JoystickController, self).__init__(*args, **kwargs)


    def init_js(self):
        '''
        attempt to init joystick
        '''
        try:
            self.js = PS3Joystick(self.dev_fn)
            if not self.js.init():
                self.js = None
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        '''
        init set of mapping from buttons to function calls
        '''

        self.button_down_trigger_map = {
            'select' : self.toggle_mode,
            'circle' : self.toggle_manual_recording,
            'triangle' : self.erase_last_N_records,
            'cross' : self.emergency_stop,
            'dpad_up' : self.increase_max_throttle,
            'dpad_down' : self.decrease_max_throttle,
            'start' : self.toggle_constant_throttle,
            "R1" : self.chaos_monkey_on_right,
            "L1" : self.chaos_monkey_on_left,
        }

        self.button_up_trigger_map = {
            "R1" : self.chaos_monkey_off,
            "L1" : self.chaos_monkey_off,
        }

        self.axis_trigger_map = {
            'left_stick_horz' : self.set_steering,
            'right_stick_vert' : self.set_throttle,
        }


class PS4JoystickController(JoystickController):
    '''
    A Controller object that maps inputs to actions
    '''
    def __init__(self, *args, **kwargs):
        super(PS4JoystickController, self).__init__(*args, **kwargs)


    def init_js(self):
        '''
        attempt to init joystick
        '''
        try:
            self.js = PS4Joystick(self.dev_fn)
            if not self.js.init():
                self.js = None
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        '''
        init set of mapping from buttons to function calls for ps4
        '''

        self.button_down_trigger_map = {
            'share' : self.toggle_mode,
            'circle' : self.toggle_manual_recording,
            'triangle' : self.erase_last_N_records,
            'cross' : self.emergency_stop,
            'L1' : self.increase_max_throttle,
            'R1' : self.decrease_max_throttle,
            'options' : self.toggle_constant_throttle,
        }

        self.axis_trigger_map = {
            'left_stick_horz' : self.set_steering,
            'right_stick_vert' : self.set_throttle,
        }


class XboxOneJoystickController(JoystickController):
    '''
    A Controller object that maps inputs to actions
    credit:
    https://github.com/Ezward/donkeypart_ps3_controller/blob/master/donkeypart_ps3_controller/part.py
    '''
    def __init__(self, *args, **kwargs):
        super(XboxOneJoystickController, self).__init__(*args, **kwargs)


    def init_js(self):
        '''
        attempt to init joystick
        '''
        try:
            self.js = XboxOneJoystick(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def magnitude(self, reversed = False):
        def set_magnitude(axis_val):
            '''
            Maps raw axis values to magnitude.
            '''
            # Axis values range from -1. to 1.
            minimum = -1.
            maximum = 1.
            # Magnitude is now normalized in the range of 0 - 1.
            magnitude = (axis_val - minimum) / (maximum - minimum)
            if reversed:
                magnitude *= -1
            self.set_throttle(magnitude)
        return set_magnitude


    def init_trigger_maps(self):
        '''
        init set of mapping from buttons to function calls
        '''

        self.button_down_trigger_map = {
            'a_button': self.toggle_mode,
            'b_button': self.toggle_manual_recording,
            'x_button': self.erase_last_N_records,
            'y_button': self.emergency_stop,
            'right_shoulder': self.increase_max_throttle,
            'left_shoulder': self.decrease_max_throttle,
            'options': self.toggle_constant_throttle,
        }

        self.axis_trigger_map = {
            'left_stick_horz': self.set_steering,
            'right_stick_vert': self.set_throttle,
            # Forza Mode
            'right_trigger': self.magnitude(),
            'left_trigger': self.magnitude(reversed = True),
        }


class LogitechJoystickController(JoystickController):
    '''
    A Controller object that maps inputs to actions
    credit:
    https://github.com/kevkruemp/donkeypart_logitech_controller/blob/master/donkeypart_logitech_controller/part.py
    '''
    def __init__(self, *args, **kwargs):
        super(LogitechJoystickController, self).__init__(*args, **kwargs)


    def init_js(self):
        '''
        attempt to init joystick
        '''
        try:
            self.js = LogitechJoystick(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        '''
        init set of mapping from buttons to function calls
        '''

        self.button_down_trigger_map = {
            'start': self.toggle_mode,
            'B': self.toggle_manual_recording,
            'Y': self.erase_last_N_records,
            'A': self.emergency_stop,
            'back': self.toggle_constant_throttle,
            "R1" : self.chaos_monkey_on_right,
            "L1" : self.chaos_monkey_on_left,
        }

        self.button_up_trigger_map = {
            "R1" : self.chaos_monkey_off,
            "L1" : self.chaos_monkey_off,
        }

        self.axis_trigger_map = {
            'left_stick_horz': self.set_steering,
            'right_stick_vert': self.set_throttle,
            'dpad_leftright' : self.on_axis_dpad_LR,
            'dpad_up_down' : self.on_axis_dpad_UD,
        }

    def on_axis_dpad_LR(self, val):
        if val == -1.0:
            self.on_dpad_left()
        elif val == 1.0:
            self.on_dpad_right()

    def on_axis_dpad_UD(self, val):
        if val == -1.0:
            self.on_dpad_up()
        elif val == 1.0:
            self.on_dpad_down()

    def on_dpad_up(self):
        self.increase_max_throttle()

    def on_dpad_down(self):
        self.decrease_max_throttle()

    def on_dpad_left(self):
        print("dpad left un-mapped")

    def on_dpad_right(self):
        print("dpad right un-mapped")


class NimbusController(JoystickController):
    #A Controller object that maps inputs to actions
    def __init__(self, *args, **kwargs):
        super(NimbusController, self).__init__(*args, **kwargs)


    def init_js(self):
        #attempt to init joystick
        try:
            self.js = Nimbus(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        #init set of mapping from buttons to function calls

        self.button_down_trigger_map = {
            'y' : self.erase_last_N_records,
            'b' : self.toggle_mode,
            'a' : self.emergency_stop,
        }

        self.axis_trigger_map = {
            'lx' : self.set_steering,
            'ry' : self.set_throttle,
        }


class WiiUController(JoystickController):
    #A Controller object that maps inputs to actions
    def __init__(self, *args, **kwargs):
        super(WiiUController, self).__init__(*args, **kwargs)


    def init_js(self):
        #attempt to init joystick
        try:
            self.js = WiiU(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def init_trigger_maps(self):
        #init set of mapping from buttons to function calls

        self.button_down_trigger_map = {
            'Y' : self.erase_last_N_records,
            'B' : self.toggle_mode,
            'A' : self.emergency_stop,
        }

        self.axis_trigger_map = {
            'LEFT_STICK_X' : self.set_steering,
            'RIGHT_STICK_Y' : self.set_throttle,
        }


class JoyStickPub(object):
    '''
    Use Zero Message Queue (zmq) to publish the control messages from a local joystick
    '''
    def __init__(self, port = 5556, dev_fn='/dev/input/js1'):
        import zmq
        self.dev_fn = dev_fn
        self.js = PS3JoystickPC(self.dev_fn)
        self.js.init()
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind("tcp://*:%d" % port)


    def run(self):
        while True:
            button, button_state, axis, axis_val = self.js.poll()
            if axis is not None or button is not None:
                if button is None:
                    button  = "0"
                    button_state = 0
                if axis is None:
                    axis = "0"
                    axis_val = 0
                message_data = (button, button_state, axis, axis_val)
                self.socket.send_string( "%s %d %s %f" % message_data)
                print("SENT", message_data)


class JoyStickSub(object):
    '''
    Use Zero Message Queue (zmq) to subscribe to control messages from a remote joystick
    '''
    def __init__(self, ip, port = 5556):
        import zmq
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://%s:%d" % (ip, port))
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.button = None
        self.button_state = 0
        self.axis = None
        self.axis_val = 0.0
        self.running = True


    def shutdown(self):
        self.running = False
        time.sleep(0.1)


    def update(self):
        while self.running:
            payload = self.socket.recv().decode("utf-8")
            #print("got", payload)
            button, button_state, axis, axis_val = payload.split(' ')
            self.button = button
            self.button_state = (int)(button_state)
            self.axis = axis
            self.axis_val = (float)(axis_val)
            if self.button == "0":
                self.button = None
            if self.axis == "0":
                self.axis = None


    def run_threaded(self):
        pass


    def poll(self):
        ret = (self.button, self.button_state, self.axis, self.axis_val)
        self.button = None
        self.axis = None
        return ret

class adv_class():
    def __init__(self,ctr):
       self.button_down_trigger_map = {
            'BUTTON_UP' : ctr.erase_last_N_records,
            'BUTTON_DOWN' : ctr.toggle_mode,
            'HOME' : ctr.emergency_stop,
            'R1' : 'self.shift_in("R1","TRAIN_MODE",descr="ENTER TRAIN MODE")',
            'TRAIN_MODE+L2' : 'self.recording=True',
            'TRAIN_MODE+R2' : 'self.recording=False',
            'TRAIN_MODE+BUTTON_RIGHT' : ctr.chaos_monkey_on_right,
            'TRAIN_MODE+BUTTON_LEFT' : ctr.chaos_monkey_on_left,
            'TRAIN_MODE+BUTTON_UP' :  ctr.emergency_stop,

            'L1' : 'self.shift_in("L1","SYSTEM_MODE",descr="ENTER SYSTEM_MODE")',
            }

       self.button_up_trigger_map = {
            }

       self.axis_trigger_map = {
            'left_stick_horz' : ctr.set_steering,
            'right_stick_vert' : ctr.set_throttle,
            'TRAIN_MODE+left_stick_horz' : ctr.set_steering,
            'TRAIN_MODE+right_stick_vert' : ctr.set_throttle,
        }

       self.CALIBRATE_MODE_button_down_trigger_map = {
            'CALIBRATE_MODE+R1' : 'self.menu_next("CALIBRATE_MODE")',
            'CALIBRATE_MODE+HOME2' :'self.print_controls(Mode="CALIBRATE_MODE") # Display Help ',

            'CALIBRATE_MODE+BUTTON_LEFT' : 'self.shift_in("BUTTON_LEFT","CALIBRATE_PWMSTEERING_LEFT",descr="EDIT STEERING_LEFT_PWM")',
            'CALIBRATE_PWMSTEERING_LEFT+dpad_up' : 'self.inc_cfg_val("STEERING_LEFT_PWM",10,1500)' + '\n' + 
                                                   'self.copy_cfg_to_part("STEERING_LEFT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_LEFT+dpad_down' : 'self.dec_cfg_val("STEERING_LEFT_PWM",10,120)'+ '\n' + 
                                                     'self.copy_cfg_to_part("STEERING_LEFT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_LEFT+dpad_left' : 'self.dec_cfg_val("STEERING_LEFT_PWM",1,120)'+ '\n' + 
                                                     'self.copy_cfg_to_part("STEERING_LEFT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_LEFT+dpad_right' : 'self.inc_cfg_val("STEERING_LEFT_PWM",1,1500)'+ '\n' + 
                                                      'self.copy_cfg_to_part("STEERING_LEFT_PWM","right_pulse",ClassName="PWMSteering")',

            'CALIBRATE_MODE+BUTTON_RIGHT' : 'self.shift_in("BUTTON_RIGHT","CALIBRATE_PWMSTEERING_RIGHT",descr="EDIT STEERING_RIGHT_PWM")',
            'CALIBRATE_PWMSTEERING_RIGHT+dpad_up' : 'self.inc_cfg_val("STEERING_RIGHT_PWM",10,1500)' + '\n' +
                                                    'self.copy_cfg_to_part("STEERING_RIGHT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_RIGHT+dpad_down' : 'self.dec_cfg_val("STEERING_RIGHT_PWM",10,120)'+ '\n' + 
                                                      'self.copy_cfg_to_part("STEERING_RIGHT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_RIGHT+dpad_left' : 'self.dec_cfg_val("STEERING_RIGHT_PWM",1,120)'+ '\n' + 
                                                      'self.copy_cfg_to_part("STEERING_RIGHT_PWM","right_pulse",ClassName="PWMSteering")',
            'CALIBRATE_PWMSTEERING_RIGHT+dpad_right' : 'self.inc_cfg_val("STEERING_RIGHT_PWM",1,1500)'+ '\n' + 
                                                       'self.copy_cfg_to_part("STEERING_RIGHT_PWM","right_pulse",ClassName="PWMSteering")',

            'CALIBRATE_MODE+HOME1' : 'self.print_cfg_vals("STEERING_LEFT_PWM,STEERING_RIGHT_PWM,THROTTLE_FORWARD_PWM,THROTTLE_STOPPED_PWM,THROTTLE_REVERSE_PWM") # Display cfg values ',
            'CALIBRATE_MODE+BUTTON_UP' : 'self.shift_in("BUTTON_UP","CALIBRATE_THROTTLE_FORWARD_PWM",descr="EDIT THROTTLE_FORWARD_PWM")',
            'CALIBRATE_THROTTLE_FORWARD_PWM+dpad_up' : 'self.inc_cfg_val("THROTTLE_FORWARD_PWM",10,1500)' + '\n' + 
                                                       'self.copy_cfg_to_part("THROTTLE_FORWARD_PWM","max_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_FORWARD_PWM+dpad_down' : 'self.dec_cfg_val("THROTTLE_FORWARD_PWM",10,120)'+ '\n' + 
                                                         'self.copy_cfg_to_part("THROTTLE_FORWARD_PWM","max_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_FORWARD_PWM+dpad_left' : 'self.dec_cfg_val("THROTTLE_FORWARD_PWM",1,120)'+ '\n' + 
                                                         'self.copy_cfg_to_part("THROTTLE_FORWARD_PWM","max_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_FORWARD_PWM+dpad_right' : 'self.inc_cfg_val("THROTTLE_FORWARD_PWM",1,1500)'+ '\n' + 
                                                          'self.copy_cfg_to_part("THROTTLE_FORWARD_PWM","max_pulse",ClassName="PWMThrottle")',

            'CALIBRATE_MODE+BUTTON_DOWN' : 'self.shift_in("BUTTON_UP","CALIBRATE_THROTTLE_STOPPED_PWM",descr="EDIT THROTTLE_STOPPED_PWM")',
            'CALIBRATE_THROTTLE_STOPPED_PWM+dpad_up' : 'self.inc_cfg_val("THROTTLE_STOPPED_PWM",10,1500)' + '\n' +
                                                       'self.copy_cfg_to_part("THROTTLE_STOPPED_PWM","zero_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_STOPPED_PWM+dpad_down' : 'self.dec_cfg_val("THROTTLE_STOPPED_PWM",10,120)'+ '\n' +
                                                         'self.copy_cfg_to_part("THROTTLE_STOPPED_PWM","zero_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_STOPPED_PWM+dpad_left' : 'self.dec_cfg_val("THROTTLE_STOPPED_PWM",1,120)'+ '\n' +
                                                         'self.copy_cfg_to_part("THROTTLE_STOPPED_PWM","zero_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_THROTTLE_STOPPED_PWM+dpad_right' : 'self.inc_cfg_val("THROTTLE_STOPPED_PWM",1,1500)'+ '\n' +
                                                          'self.copy_cfg_to_part("THROTTLE_STOPPED_PWM","zero_pulse",ClassName="PWMThrottle")',

            'CALIBRATE_MODE+L2' : 'self.shift_in("BUTTON_UP","CALIBRATE_REVERSE_PWM",descr="EDIT THROTTLE_REVERSE_PWM")',
            'CALIBRATE_REVERSE_PWM+dpad_up' : 'self.inc_cfg_val("THROTTLE_REVERSE_PWM",10,1500)' + '\n' +
                                                       'self.copy_cfg_to_part("THROTTLE_REVERSE_PWM","min_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_REVERSE_PWM+dpad_down' : 'self.dec_cfg_val("THROTTLE_REVERSE_PWM",10,120)'+ '\n' +
                                                         'self.copy_cfg_to_part("THROTTLE_REVERSE_PWM","min_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_REVERSE_PWM+dpad_left' : 'self.dec_cfg_val("THROTTLE_REVERSE_PWM",1,120)'+ '\n' +
                                                         'self.copy_cfg_to_part("THROTTLE_REVERSE_PWM","min_pulse",ClassName="PWMThrottle")',
            'CALIBRATE_REVERSE_PWM+dpad_right' : 'self.inc_cfg_val("THROTTLE_REVERSE_PWM",1,1500)'+ '\n' +
                                                          'self.copy_cfg_to_part("THROTTLE_REVERSE_PWM","min_pulse",ClassName="PWMThrottle")',

             }

       self.CALIBRATE_MODE_axis_trigger_map = {
            }
       self.CALIBRATE_MODE_button_up_trigger_map = {
            }


       self.CAMERA_MODE_button_down_trigger_map = {
            'CAMERA_MODE+R1' : 'self.menu_next("CAMERA_MODE")',
            'CAMERA_MODE+HOME2' : 'self.print_controls(Mode="CAMERA_MODE") # Display Help ',

            'CAMERA_MODE+BUTTON_RIGHT' : 'self.shift_in("BUTTON_RIGHT","CAMERA_CROP_TOP_EDIT",descr="EDIT OI_CROP_TOP")',
            'CAMERA_CROP_TOP_EDIT+dpad_up' : 'self.inc_cfg_val("ROI_CROP_TOP",10,self.cfg.IMAGE_H-self.cfg.ROI_CROP_BOTTOM)', 
            'CAMERA_CROP_TOP_EDIT+dpad_down' : 'self.dec_cfg_val("ROI_CROP_TOP",10,0)',
            'CAMERA_CROP_TOP_EDIT+dpad_left' : 'self.dec_cfg_val("ROI_CROP_TOP",1,0)',
            'CAMERA_CROP_TOP_EDIT+dpad_right' : 'self.inc_cfg_val("ROI_CROP_TOP",1,self.cfg.IMAGE_H-self.cfg.ROI_CROP_BOTTOM)',

            'CAMERA_MODE+BUTTON_DOWN' : 'self.shift_in("BUTTON_DOWN","CAMERA_CROP_BOTTOM_EDIT",descr="EDIT OI_CROP_BOTTOM")',
            'CAMERA_CROP_BOTTOM_EDIT+dpad_up' : 'self.inc_cfg_val("ROI_CROP_BOTTOM",10,self.cfg.IMAGE_H-self.cfg.ROI_CROP_TOP)',
            'CAMERA_CROP_BOTTOM_EDIT+dpad_down' : 'self.dec_cfg_val("ROI_CROP_BOTTOM",10,0)',
            'CAMERA_CROP_BOTTOM_EDIT+dpad_left' : 'self.dec_cfg_val("ROI_CROP_BOTTOM",1,0)',
            'CAMERA_CROP_BOTTOM_EDIT+dpad_right' : 'self.inc_cfg_val("ROI_CROP_BOTTOM",1,self.cfg.IMAGE_H-self.cfg.ROI_CROP_TOP)',

            'CAMERA_AUGMENT_LEVEL_EDIT+dpad_up' : 'self.inc_input_val("IMG_AUGMENT_LEVEL",10,30)',
            'CAMERA_AUGMENT_LEVEL_EDIT+dpad_down' : 'self.dec_input_val("IMG_AUGMENT_LEVEL",10,0)',
            'CAMERA_AUGMENT_LEVEL_EDIT+dpad_left' : 'self.dec_input_val("IMG_AUGMENT_LEVEL",1,0)',
            'CAMERA_AUGMENT_LEVEL_EDIT+dpad_right' : 'self.inc_input_val("IMG_AUGMENT_LEVEL",1,30)',

            'CAMERA_MODE+BUTTON_UP' : 'self.shift_in("BUTTON_UP","CAMERA_TILT_EDIT",descr="EDIT CAMERA_TILT ( +L2/+R2 : edit PWM_DOWN/PWM_UP)" )',
            'CAMERA_TILT_EDIT+dpad_up' : 'self.inc_cfg_val("CAMERA_TILT_CENTER_PWM",10,1500)',
            'CAMERA_TILT_EDIT+dpad_down' : 'self.dec_cfg_val("CAMERA_TILT_CENTER_PWM",10,0)',
            'CAMERA_TILT_EDIT+dpad_left' : 'self.dec_cfg_val("CAMERA_TILT_CENTER_PWM",1,0)',
            'CAMERA_TILT_EDIT+dpad_right' : 'self.inc_cfg_val("CAMERA_TILT_CENTER_PWM",1,1500)',

            'CAMERA_TILT_EDIT+L2' : 'self.shift_in("L2","CAMERA_TILT_EDIT_PWM_DOWN",descr="EDIT CAMERA_TILT_PWM_DOWN")',
            'CAMERA_TILT_EDIT_PWM_DOWN+dpad_up' : 'self.inc_cfg_val("CAMERA_TILT_PWM_DOWN",10,1500)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",-1)',
            'CAMERA_TILT_EDIT_PWM_DOWN+dpad_down' : 'self.dec_cfg_val("CAMERA_TILT_PWM_DOWN",10,0)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",-1)',

            'CAMERA_TILT_EDIT_PWM_DOWN+dpad_left' : 'self.dec_cfg_val("CAMERA_TILT_PWM_DOWN",1,0)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",-1)',

            'CAMERA_TILT_EDIT_PWM_DOWN+dpad_right' : 'self.inc_cfg_val("CAMERA_TILT_PWM_DOWN",1,1500)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",-1)',

            'CAMERA_TILT_EDIT+R2' : 'self.shift_in("R2","CAMERA_TILT_EDIT_PWM_UP",descr="EDIT CAMERA_TILT_PWM_UP")',
            'CAMERA_TILT_EDIT_PWM_UP+dpad_up' : 'self.inc_cfg_val("CAMERA_TILT_PWM_UP",10,1500)'+'\n'+
                                                'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                'self.set_input_val("user_camera_tilt",1)',
            'CAMERA_TILT_EDIT_PWM_UP+dpad_down' : 'self.dec_cfg_val("CAMERA_TILT_PWM_UP",10,0)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",1)',

            'CAMERA_TILT_EDIT_PWM_UP+dpad_left' : 'self.dec_cfg_val("CAMERA_TILT_PWM_UP",1,0)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",1)',

            'CAMERA_TILT_EDIT_PWM_UP+dpad_right' : 'self.inc_cfg_val("CAMERA_TILT_PWM_UP",1,1500)'+'\n'+
                                                  'self.copy_cfg_to_part("CAMERA_TILT_PWM_DOWN","left_pulse",ClassName="PWMSteering",ObjName="camera_tilt_servo")'+'\n'+
                                                  'self.set_input_val("user_camera_tilt",1)',
 

            'CAMERA_MODE+BUTTON_LEFT' : 'self.shift_in("BUTTON_LEFT","CAMERA_PAN_EDIT",descr="EDIT CAMERA_PAN_CENTER_PWM( +L2/+R2 : edit LEFT_PWM/RIGHT_PWM)")',
            'CAMERA_PAN_EDIT+dpad_up' : 'self.inc_cfg_val("CAMERA_PAN_CENTER_PWM",10,1500) # Edit Camera Pan CENTER_PWM (+10)',
            'CAMERA_PAN_EDIT+dpad_down' : 'self.dec_cfg_val("CAMERA_PAN_CENTER_PWM",10,0) # Edit Camera Pan CENTER_PWM (-10)',
            'CAMERA_PAN_EDIT+dpad_left' : 'self.dec_cfg_val("CAMERA_PAN_CENTER_PWM",1,0) # Edit Camera Pan CENTER_PWM (-1)',
            'CAMERA_PAN_EDIT+dpad_right' : 'self.inc_cfg_val("CAMERA_PAN_CENTER_PWM",1,1500)# Edit Camera Pan CENTER_PWM (+1)',


            'CAMERA_PAN_EDIT+L2' : 'self.shift_in("L2","CAMERA_PAN_EDIT_LEFT_PWM",descr="EDIT CAMERA_PAN_LEFT_PWM")',
            'CAMERA_PAN_EDIT_LEFT_PWM+dpad_up' : 'self.inc_cfg_val("CAMERA_PAN_LEFT_PWM",10,1500) # Edit Camera Pan LEFT_PWM (+10)'+'\n'+
                                                 'self.copy_cfg_to_part("CAMERA_PAN_LEFT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                 'self.set_input_val("user_camera_pan",-1)',

            'CAMERA_PAN_EDIT_LEFT_PWM+dpad_down' : 'self.dec_cfg_val("CAMERA_PAN_LEFT_PWM",10,0) # Edit Camera Pan LEFT_PWM (-10)'+'\n'+
                                                   'self.copy_cfg_to_part("CAMERA_PAN_LEFT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                   'self.set_input_val("user_camera_pan",-1)',

            'CAMERA_PAN_EDIT_LEFT_PWM+dpad_left' : 'self.dec_cfg_val("CAMERA_PAN_LEFT_PWM",1,0) # Edit Camera Pan LEFT_PWM (-1)'+'\n'+
                                           'self.copy_cfg_to_part("CAMERA_PAN_LEFT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                           'self.set_input_val("user_camera_pan",-1)',

            'CAMERA_PAN_EDIT_LEFT_PWM+dpad_right' : 'self.inc_cfg_val("CAMERA_PAN_LEFT_PWM",1,1500) # Edit Camera Pan LEFT_PWM (+1)'+'\n'+
                                           'self.copy_cfg_to_part("CAMERA_PAN_LEFT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                           'self.set_input_val("user_camera_pan",-1)',


            'CAMERA_PAN_EDIT+R2' : 'self.shift_in("R2","CAMERA_PAN_EDIT_RIGHT_PWM",descr="EDIT CAMERA_PAN_RIGHT_PWM")',
            'CAMERA_PAN_EDIT_RIGHT_PWM+dpad_up' : 'self.inc_cfg_val("CAMERA_PAN_RIGHT_PWM",10,1500) # Edit Camera Pan Right_PWM (+10)'+'\n'+
                                                 'self.copy_cfg_to_part("CAMERA_PAN_RIGHT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                 'self.set_input_val("user_camera_pan",1)',

            'CAMERA_PAN_EDIT_RIGHT_PWM+dpad_down' : 'self.dec_cfg_val("CAMERA_PAN_RIGHT_PWM",10,0) # Edit Camera Pan Right_PWM (-10)'+'\n'+
                                                 'self.copy_cfg_to_part("CAMERA_PAN_RIGHT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                 'self.set_input_val("user_camera_pan",1)',

            'CAMERA_PAN_EDIT_RIGHT_PWM+dpad_left' : 'self.dec_cfg_val("CAMERA_PAN_RIGHT_PWM",1,0) # Edit Camera Pan Right_PWM (-1)'+'\n'+
                                                 'self.copy_cfg_to_part("CAMERA_PAN_RIGHT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                 'self.set_input_val("user_camera_pan",1)',

            'CAMERA_PAN_EDIT_RIGHT_PWM+dpad_right' : 'self.inc_cfg_val("CAMERA_PAN_RIGHT_PWM",1,1500) # Edit Camera Pan Right_PWM (+1)'+'\n'+
                                                 'self.copy_cfg_to_part("CAMERA_PAN_RIGHT_PWM","left_pulse",ClassName="PWMSteering",ObjName="camera_pan_servo")'+'\n'+
                                                 'self.set_input_val("user_camera_pan",1)',




            'CAMERA_MODE+dpad_right' : 'self.inc_input_val("user_camera_pan",0.1,1) # Move Camera Pan (+0.1)',
            'CAMERA_MODE+dpad_left' : 'self.dec_input_val("user_camera_pan",0.1,-1) # Move Camera Pan (-0.1)',
            'CAMERA_MODE+dpad_up' : 'self.inc_input_val("user_camera_tilt",0.1,1) # Move Camera Tilt (+0.1)',
            'CAMERA_MODE+dpad_down' : 'self.dec_input_val("user_camera_tilt",0.1,-1) # Move Camera Tilt (-0.1)',

            'CAMERA_MODE+HOME1' : 'self.print_cfg_vals("STEERING_LEFT_PWM,CAMERA_PAN_CENTER_PWM,CAMERA_TILT_PWM_UP") # Display cfg Camera Settings ',
            'CAMERA_MODE+B' : 'self.V.profiler.report()'+'\n'+'print("NewLine")',

            }
       self.CAMERA_MODE_button_up_trigger_map = {
            }

       self.CAMERA_MODE_axis_trigger_map = {
            'CAMERA_MODE+left_stick_vert' : 'self.set_input_val("user_camera_tilt",-%val%) # Move Camera Tilt ',
            'CAMERA_MODE+right_stick_horz' : 'self.set_input_val("user_camera_pan",%val%)  # Move Camera Pan ',
            }


       self.SYSTEM_MODE_button_down_trigger_map = {
            'SYSTEM_MODE+R1' : 'self.menu_next("SYSTEM_MODE")',
            'SYSTEM_MODE+HOME2' : 'self.print_controls(Mode="SYSTEM_MODE") # Display Help ',
            'SYSTEM_MODE+BUTTON_RIGHT' : 'self.shift_in("BUTTON_RIGHT","CAMERA_AUGMENT_LEVEL_EDIT",descr="EDIT CAMERA_AUGMENT_LEVEL")',
            }

       self.SYSTEM_MODE_button_up_trigger_map = {
            }

       self.SYSTEM_MODE_axis_trigger_map = {
            }

       self.key_translate_map={
            'Y' : 'BUTTON_LEFT',
            'A' : 'BUTTON_RIGHT',
            'X' : 'BUTTON_UP',
            'B' : 'BUTTON_DOWN',
            'a' : 'BUTTON_DOWN', 
            'b' : 'BUTTON_RIGHT',
            'a_button' : 'BUTTON_DOWN',
            'b_button' : 'BUTTON_RIGHT',
            'x_button' : 'BUTTON_LEFT',
            'y_button' : 'BUTTON_RIGHT', 
            'triangle' :'BUTTON_UP',
            'circle' :'BUTTON_RIGHT',
            'cross' :'BUTTON_DOWN',
            'square' :'BUTTON_LEFT',
            'PAD_RIGHT' : 'dpad_right',
            'PAD_LEFT' : 'dpad_left',
            'PAD_UP' : 'dpad_up',
            'PAD_DOWN' : 'dpad_down',
            'LEFT_BOTTOM_TRIGGER' :'L2' ,
            'LEFT_TOP_TRIGGER' :'L1',
            'RIGHT_BOTTOM_TRIGGER' : 'R2',
            'RIGHT_TOP_TRIGGER' : 'R1',
            'share' : 'HOME1',
            'back' : 'HOME1',
            'select' : 'HOME1',
            'SELECT' : 'HOME1',
            'START'  : 'HOME2',
            'PS' : 'HOME', 
            'Logitech' : 'HOME',
            'start' : 'HOME2',
            'options' : 'HOME2',
            'dpad_horz' : '|dpad_left|dpad_right',
            'dpad_leftright' :  '|dpad_left|dpad_right',
            'dpad_up_down' : '|dpad_up|dpad_down',
            'dpad_vert' : '|dpad_up|dpad_down',
            'left_shoulder' : 'L1',
            'right_shoulder' : 'R1',
            'LEFT_STICK_X' : 'left_stick_horz',
            'LEFT_STICK_Y' : 'left_stick_vert',
            'RIGHT_STICK_X' : 'right_stick_horz',
            'RIGHT_STICK_Y' : 'right_stick_vert',
            'lx' : 'left_stick_horz',
            'ly' : 'left_stick_vert',
            'rx' : 'right_stick_horz',
            'ry' : 'right_stick_vert',
        }

    def print_controls_adv(self,Mode=""):
        '''
        print the mapping of buttons and axis to functions
        '''
        pt = PrettyTable()
        pt.field_names = ["control", "action"]
        for button, control in self.button_down_trigger_map.items():
          n=button.find("+")
          #print (button[:n] +"="+Mode)
 
          if (n>0 and button[:n]==Mode) or (Mode=="" and n<=0):

            if type(control) is str :
                 n=control.find("descr=")
                 if n>0 : control=control[n+6:][:-1]
                 n=control.find("#")
                 if n>0 : control=control[n+1:]
                 pt.add_row([button, control])
            else:
                 pt.add_row([button, control.__name__])

        for axis, control in self.axis_trigger_map.items():
          n=axis.find("+")
          if (n>0 and axis[:n]==Mode) or (Mode=="" and n<=0):

            if type(control) is str :
                  n=control.find("descr=")
                  if n>0 : control=control[n+6:][:-1]
                  n=control.find("#")
                  if n>0 : control=control[n+1:]

                  pt.add_row([axis, control])
            else:
                  pt.add_row([axis, control.__name__])

        print("Advanced Joystick Controls:")
        print(pt)


def get_js_controller(cfg,Vobject=None):
    cont_class = None
    if cfg.CONTROLLER_TYPE == "ps3":
        cont_class = PS3JoystickController
    elif cfg.CONTROLLER_TYPE == "ps4":
        cont_class = PS4JoystickController
    elif cfg.CONTROLLER_TYPE == "nimbus":
        cont_class = NimbusController
    elif cfg.CONTROLLER_TYPE == "xbox":
        cont_class = XboxOneJoystickController
    elif cfg.CONTROLLER_TYPE == "wiiu":
        cont_class = WiiUController
    elif cfg.CONTROLLER_TYPE == "F710":
        cont_class = LogitechJoystickController
    else:
        raise("Unknown controller type: " + cfg.CONTROLLER_TYPE)

    ctr = cont_class(throttle_dir=cfg.JOYSTICK_THROTTLE_DIR,
                                throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
                                steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
   
    if hasattr(cfg, 'CONTROLLER_ADVANCED'): 
       if cfg.CONTROLLER_ADVANCED == True:
           if Vobject is not None :
               ctr.cfg=cfg
               adv=adv_class(ctr) # replace some of the controller functions and data with the advanced version : 
               setattr(ctr, 'update', ctr.update_adv)
               setattr(ctr, 'print_controls', adv.print_controls_adv)
               setattr(ctr, 'button_down_trigger_map',adv.button_down_trigger_map)
               setattr(ctr, 'button_up_trigger_map',adv.button_up_trigger_map)
               setattr(ctr, 'axis_trigger_map',adv.axis_trigger_map)
               setattr(ctr, 'key_translate_map',adv.key_translate_map)
               ctr.V=Vobject
 
               # Standard menus are registered here, but each part could register it's own menu...
               ctr.menu_register("SYSTEM_MODE",adv.SYSTEM_MODE_button_down_trigger_map,{},{},descr="ENTER SYSTEM_MODE")
               ctr.menu_register("CALIBRATE_MODE",adv.CALIBRATE_MODE_button_down_trigger_map,{},{},descr="ENTER CALIBRATION_MODE")
               ctr.menu_register("CAMERA_MODE",adv.CAMERA_MODE_button_down_trigger_map,{},adv.CAMERA_MODE_axis_trigger_map,descr="ENTER CAMERA_MODE")
 
           else:
               print ('\n'+"Warning: to use Advanced Controller mode, you need to modify the manage.py file : 'get_js_controller(cfg,Vobject=V)'"+'\n')
 
    ctr.set_deadzone(cfg.JOYSTICK_DEADZONE)
    return ctr

if __name__ == "__main__":
    '''
    publish ps3 controller
    when running from ubuntu 16.04, it will interfere w mouse until:
    xinput set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0
    '''
    print("You may need:")
    print('xinput set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0')
    p = JoyStickPub()
    p.run()
