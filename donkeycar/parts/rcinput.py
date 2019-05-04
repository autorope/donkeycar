# rcinput.py

import os
import array
import time
import struct


class RCController(JoystickController):
    '''
    A Controller object that maps inputs to actions
    '''

    def __init__(self, *args, **kwargs):
        super(RCController, self).__init__(*args, **kwargs)

    def init_js(self):
        '''
        attempt to init joystick / RC device
        '''
        try:
            self.js = 


class RoboHATJoystick(Joystick):
    '''
    An interface to a physical SeeSaw device available at 0x49
    Contains mapping that works with seesaw driver
    '''

   def __init__(self, *args, * 

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
        raise (Exception("Subclass needs to define init_js"))

    def init_trigger_maps(self):
        '''
        Creating mapping of buttons to functions.
        Should be definied by derived class
        '''
        raise (Exception("init_trigger_maps"))

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

        # wait for joystick to be online
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
        # print("angle", self.angle)

    def set_throttle(self, axis_val):
        # this value is often reversed, with positive value when pulling down
        self.throttle = (self.throttle_dir * axis_val * self.throttle_scale)
        # print("throttle", self.throttle)
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
        # set flag to exit polling thread, then wait a sec for it to leave
        self.running = False
        time.sleep(0.5)

