
import os
import array
import time
import struct
import random
from threading import Thread

#import for syntactical ease
from donkeycar.parts.web_controller.web import LocalWebController

class Joystick(object):
    '''
    An interface to a physical joystick
    '''
    def __init__(self, dev_fn='/dev/input/js0'):
        self.axis_states = {}
        self.button_states = {}
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
            return            
            
        if not os.path.exists(self.dev_fn):
            print(self.dev_fn, "is missing")
            return

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

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue

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


class PS3Joystick(Joystick):
    '''
    An interface to a physical PS3 joystick available at /dev/input/js0
    '''
    def __init__(self, *args, **kwargs):
        super(PS3Joystick, self).__init__(*args, **kwargs)

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

class PS3JoystickNew(Joystick):
    '''
    An interface to a physical PS3 joystick available at /dev/input/js0
    '''
    def __init__(self, *args, **kwargs):
        super(PS3JoystickNew, self).__init__(*args, **kwargs)

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
    set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0
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
        
        self.button_down_trigger_map = {}
        self.button_up_trigger_map = {}
        self.axis_trigger_map = {}
        self.init_trigger_maps()

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

    def print_controls(self):
        '''
        print the mapping of buttons and axis to functions
        '''
        print("Joystick Controls:")
        print("On Button Down:")
        print(self.button_down_trigger_map)
        print("On Button Up:")
        print(self.button_up_trigger_map)
        print("On Axis Move:")
        print(self.axis_trigger_map)

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
            self.recording = (self.throttle != 0.0 and self.mode == 'user')

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
            time.sleep(5)

        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if axis is not None and axis in self.axis_trigger_map:
                '''
                then invoke the function attached to that axis
                '''
                self.axis_trigger_map[axis](axis_val)

            if button and button_state == 1 and button in self.button_down_trigger_map:
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

    def set_steering(self, axis_val):
        self.angle = self.steering_scale * axis_val
        #print("angle", self.angle)

    def set_throttle(self, axis_val):
        #this value is often reversed, with positive value when pulling down
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

        print('throttle_scale:', self.throttle_scale)

    def decrease_max_throttle(self):
        '''
        decrease throttle scale setting
        '''
        self.throttle_scale = round(max(0.0, self.throttle_scale - 0.01), 2)
        if self.constant_throttle:
            self.throttle = self.throttle_scale
            self.on_throttle_changes()

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
            self.js.init()
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
            self.js.init()
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


if __name__ == "__main__":
    '''
    publish ps3 controller
    when running from ubuntu 16.04, it will interfere w mouse until:
    xinput set-prop "Sony PLAYSTATION(R)3 Controller" "Device Enabled" 0
    '''
    p = JoyStickPub()
    p.run()