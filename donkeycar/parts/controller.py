

import array
import time
import struct


from donkeycar.parts.web_controller.web import LocalWebController

class Joystick():
    """
    An interface to a physical joystick available at /dev/input
    """
    access_url = None #required to be consistent with web controller

    def __init__(self, dev_fn='/dev/input/js0'):
        self.axis_states = {}
        self.button_states = {}
        self.axis_map = []
        self.button_map = []
        self.jsdev = None
        self.dev_fn = dev_fn

        # These constants were borrowed from linux/input.h
        self.axis_names = {
            0x00 : 'x',
            0x01 : 'y',
            0x02 : 'z',
            0x03 : 'rx',
            0x04 : 'ry',
            0x05 : 'rz',
            0x06 : 'trottle',
            0x07 : 'rudder',
            0x08 : 'wheel',
            0x09 : 'gas',
            0x0a : 'brake',
            0x10 : 'hat0x',
            0x11 : 'hat0y',
            0x12 : 'hat1x',
            0x13 : 'hat1y',
            0x14 : 'hat2x',
            0x15 : 'hat2y',
            0x16 : 'hat3x',
            0x17 : 'hat3y',
            0x18 : 'pressure',
            0x19 : 'distance',
            0x1a : 'tilt_x',
            0x1b : 'tilt_y',
            0x1c : 'tool_width',
            0x20 : 'volume',
            0x28 : 'misc',
        }

        self.button_names = {
            0x120 : 'trigger',
            0x121 : 'thumb',
            0x122 : 'thumb2',
            0x123 : 'top',
            0x124 : 'top2',
            0x125 : 'pinkie',
            0x126 : 'base',
            0x127 : 'base2',
            0x128 : 'base3',
            0x129 : 'base4',
            0x12a : 'base5',
            0x12b : 'base6',

            #PS3 sixaxis specific
            0x12c : "triangle",
            0x12d : "circle",
            0x12e : "cross",
            0x12f : 'square',

            0x130 : 'a',
            0x131 : 'b',
            0x132 : 'c',
            0x133 : 'x',
            0x134 : 'y',
            0x135 : 'z',
            0x136 : 'tl',
            0x137 : 'tr',
            0x138 : 'tl2',
            0x139 : 'tr2',
            0x13a : 'select',
            0x13b : 'start',
            0x13c : 'mode',
            0x13d : 'thumbl',
            0x13e : 'thumbr',

            0x220 : 'dpad_up',
            0x221 : 'dpad_down',
            0x222 : 'dpad_left',
            0x223 : 'dpad_right',

            # XBox 360 controller uses these codes.
            0x2c0 : 'dpad_left',
            0x2c1 : 'dpad_right',
            0x2c2 : 'dpad_up',
            0x2c3 : 'dpad_down',
        }


    def init(self):
        from fcntl import ioctl
        """
        call once to setup connection to dev/input/js0 and map buttons
        """
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

        return True


    def show_map(self):
        """
        list the buttons and axis found on this joystick
        """
        print ('%d axes found: %s' % (self.num_axes, ', '.join(self.axis_map)))
        print ('%d buttons found: %s' % (self.num_buttons, ', '.join(self.button_map)))


    def poll(self):
        """
        query the state of the joystick, returns button which was pressed, if any,
        and axis which was moved, if any. button_state will be None, 1, or 0 if no changes,
        pressed, or released. axis_val will be a float from -1 to +1. button and axis will
        be the string label determined by the axis map in init.
        """
        button = None
        button_state = None
        axis = None
        axis_val = None

        # Main event loop
        evbuf = self.jsdev.read(8)

        if evbuf:
            tval, value, typev, number = struct.unpack('IhBB', evbuf)

            if typev & 0x80:
                #ignore initialization event
                return button, button_state, axis, axis_val

            if typev & 0x01:
                button = self.button_map[number]
                if button:
                    self.button_states[button] = value
                    button_state = value

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue

        return button, button_state, axis, axis_val


class JoystickController(object):
    """
    Joystick client using access to local physical input
    """

    def __init__(self, poll_delay=0.0,
                 max_throttle=1.0,
                 steering_axis='x',
                 throttle_axis='rz',
                 steering_scale=1.0,
                 throttle_scale=-1.0,
                 dev_fn='/dev/input/js0',
                 auto_record_on_throttle=True):

        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.poll_delay = poll_delay
        self.running = True
        self.max_throttle = max_throttle
        self.steering_axis = steering_axis
        self.throttle_axis = throttle_axis
        self.steering_scale = steering_scale
        self.throttle_scale = throttle_scale
        self.recording = False
        self.constant_throttle = False
        self.auto_record_on_throttle = auto_record_on_throttle
        self.dev_fn = dev_fn
        self.js = None

        #We expect that the framework for parts will start a new
        #thread for our update fn. We used to do that and it caused
        #two threads to be polling for js events.

    def on_throttle_changes(self):
        """
        turn on recording when non zero throttle in the user mode.
        """
        if self.auto_record_on_throttle:
            self.recording = (self.throttle != 0.0 and self.mode == 'user')

    def init_js(self):
        """
        attempt to init joystick
        """
        try:
            self.js = Joystick(self.dev_fn)
            self.js.init()
        except FileNotFoundError:
            print(self.dev_fn, "not found.")
            self.js = None
        return self.js is not None


    def update(self):
        """
        poll a joystick for input events

        button map name => PS3 button => function
        * top2 = PS3 dpad up => increase throttle scale
        * base = PS3 dpad down => decrease throttle scale
        * base2 = PS3 dpad left => increase steering scale
        * pinkie = PS3 dpad right => decrease steering scale
        * trigger = PS3 select => switch modes
        * top = PS3 start => toggle constant throttle
        * base5 = PS3 left trigger 1
        * base3 = PS3 left trigger 2
        * base6 = PS3 right trigger 1
        * base4 = PS3 right trigger 2
        * thumb2 = PS3 right thumb
        * thumb = PS3 left thumb
        * circle = PS3 circrle => toggle recording
        * triangle = PS3 triangle => increase max throttle
        * cross = PS3 cross => decrease max throttle
        """

        #wait for joystick to be online
        while self.running and not self.init_js():
            time.sleep(5)

        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if axis == self.steering_axis:
                self.angle = self.steering_scale * axis_val
                print("angle", self.angle)

            if axis == self.throttle_axis:
                #this value is often reversed, with positive value when pulling down
                self.throttle = (self.throttle_scale * axis_val * self.max_throttle)
                print("throttle", self.throttle)
                self.on_throttle_changes()

            if button == 'trigger' and button_state == 1:
                """
                switch modes from:
                user: human controlled steer and throttle
                local_angle: ai steering, human throttle
                local: ai steering, ai throttle
                """
                if self.mode == 'user':
                    self.mode = 'local_angle'
                elif self.mode == 'local_angle':
                    self.mode = 'local'
                else:
                    self.mode = 'user'
                print('new mode:', self.mode)

            if button == 'circle' and button_state == 1:
                """
                toggle recording on/off
                """
                if self.auto_record_on_throttle:
                    print('auto record on throttle is enabled.')
                elif self.recording:
                    self.recording = False
                else:
                    self.recording = True

                print('recording:', self.recording)

            if button == 'triangle' and button_state == 1:
                """
                increase max throttle setting
                """
                self.max_throttle = round(min(1.0, self.max_throttle + 0.01), 2)
                if self.constant_throttle:
                    self.throttle = self.max_throttle
                    self.on_throttle_changes()

                print('max_throttle:', self.max_throttle)

            if button == 'cross' and button_state == 1:
                """
                decrease max throttle setting
                """
                self.max_throttle = round(max(0.0, self.max_throttle - 0.01), 2)
                if self.constant_throttle:
                    self.throttle = self.max_throttle
                    self.on_throttle_changes()

                print('max_throttle:', self.max_throttle)

            if button == 'base' and button_state == 1:
                """
                increase throttle scale
                """
                self.throttle_scale = round(min(0.0, self.throttle_scale + 0.05), 2)
                print('throttle_scale:', self.throttle_scale)

            if button == 'top2' and button_state == 1:
                """
                decrease throttle scale
                """
                self.throttle_scale = round(max(-1.0, self.throttle_scale - 0.05), 2)
                print('throttle_scale:', self.throttle_scale)

            if button == 'base2' and button_state == 1:
                """
                increase steering scale
                """
                self.steering_scale = round(min(1.0, self.steering_scale + 0.05), 2)
                print('steering_scale:', self.steering_scale)

            if button == 'pinkie' and button_state == 1:
                """
                decrease steering scale
                """
                self.steering_scale = round(max(0.0, self.steering_scale - 0.05), 2)
                print('steering_scale:', self.steering_scale)

            if button == 'top' and button_state == 1:
                """
                toggle constant throttle
                """
                if self.constant_throttle:
                    self.constant_throttle = False
                    self.throttle = 0
                    self.on_throttle_changes()
                else:
                    self.constant_throttle = True
                    self.throttle = self.max_throttle
                    self.on_throttle_changes()
                print('constant_throttle:', self.constant_throttle)

            time.sleep(self.poll_delay)

    def run_threaded(self, img_arr=None):
        self.img_arr = img_arr
        return self.angle, self.throttle, self.mode, self.recording

    def run(self, img_arr=None):
        raise Exception("We expect for this part to be run with the threaded=True argument.")
        return False

    def shutdown(self):
        self.running = False
        time.sleep(0.5)

