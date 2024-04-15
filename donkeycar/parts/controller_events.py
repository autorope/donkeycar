import os
import array
import time
import struct
import random
import threading
import logging
from typing import Any
from typing_extensions import Self

from prettytable import PrettyTable

#import for syntactical ease
from donkeycar.parts.web_controller.web import LocalWebController
from donkeycar.parts.web_controller.web import WebFpv
from donkeycar import Memory

logger = logging.getLogger(__name__)

BUTTON_CLICK = "click"

def format_button_event(button) -> str:
    return f'/event/button/{button}'

def format_axis_event(axis) -> str:
    return f'/event/axis/{axis}'

class AbstractInputController(object):
    '''
    A threadsafe object that can be polled to return 
    button and axis change events from an input device.
    ''' 
    def init(self) -> Self:
        '''
        Attempt to initialize the controller. Should be defined by derived class.
        - on success returns self so it can be fluently chained
        - on failure return false
        '''
        raise(Exception("Subclass needs to define init()"))

    def show_map(self) -> bool:
        '''
        Print the names of the buttons and axes found on this input controller
        - returns True if input controller is initialized
        - returns False if input controller is not initialized
        '''
        raise(Exception("Subclass needs to define show_map()"))


    def poll(self):
        '''
        Query the input controller for a button or axis state change event.
        This must be threadsafe.

        returns: tuple of 
        - button: string name of button if a button changed, otherwise None
        - button_state: number 0 or 1 if a button changed, otherwise None
        - axis: string name of axis if an axis changed, otherwise None
        - button_state: number -1 to 1 if an axis changed, otherwise None
        '''
        raise(Exception("Subclass needs to define poll()"))



class LinuxGameController(AbstractInputController):
    '''
    An interface to a physical joystick with a linux driver that
    supports fnctl and a mapping into the linux input device tree.

    The
    The joystick holds available buttons
    and axis; both their names and values
    and can be polled to state changes.

    button_names is a map of the driver's button name to a readable name for each button
    - if button_names is not provided then the driver's button names are used.
    axis_names is a map of the driver's axis name to a readable name for each axis
    - if the axis_names is not provided then the driver's axis names are used.
    dev_fn is the mounted device path for the controller
    '''
    def __init__(self, button_names = {}, axis_names = {}, dev_fn='/dev/input/js0'):
        self.axis_states = {}
        self.button_states = {}
        self.axis_names = button_names
        self.button_names = axis_names
        self.axis_map = []
        self.button_map = []
        self.num_axes = 0
        self.num_buttons = 0
        self.jsdev = None
        self.dev_fn = dev_fn
        self.initialized = False


    def init(self) -> bool:
        """
        Attempt to initialize the controller.
        In Linux, query available buttons and axes using fnctl and
        a path in the linux device tree.  
        If the button_names or axis_names mappings passed to the contruct
        maps to a discovered input control, then use that name when emitting
        events for that input control, otherwise emit using a default name.
        - on success returns self so it can be fluently chained
        - on failure it raises an exception

        """
        try:
            from fcntl import ioctl
        except ModuleNotFoundError:
            self.num_axes = 0
            self.num_buttons = 0
            logger.warn("No support for fnctl module. LinuxGameController not initialized.")
            raise Exception("No support for fnctl module. LinuxGameController not initialized.")

        if not os.path.exists(self.dev_fn):
            logger.warn(f"No device {self.dev_fn}. LinuxGameController not initialized.")
            raise Exception(f"No device {self.dev_fn}. LinuxGameController not initialized.")

        #
        # only initialize once
        #
        if self.initialized:
            return True

        '''
        call once to setup connection to device and map buttons
        '''
        # Open the joystick device.
        logger.info(f'Opening %s... {self.dev_fn}')
        self.jsdev = open(self.dev_fn, 'rb')

        # Get the device name.
        buf = array.array('B', [0] * 64)
        ioctl(self.jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
        self.js_name = buf.tobytes().decode('utf-8')
        logger.info('Device name: %s' % self.js_name)

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
            axis_name = self.axis_names.get(axis, 'axis(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            self.axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(self.jsdev, 0x80406a34, buf) # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = self.button_names.get(btn, 'button(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0
            #print('btn', '0x%03x' % btn, 'name', btn_name)

        self.initialized = True
        return True


    def show_map(self) -> bool:
        '''
        Print the names of the buttons and axes found on this input controller
        '''
        if self.initialized:
            print ('%d axes found: %s' % (self.num_axes, ', '.join(self.axis_map)))
            print ('%d buttons found: %s' % (self.num_buttons, ', '.join(self.button_map)))
            return True
        return False


    def poll(self):
        '''
        Query the the input controller for a button or axis state change event.
        If the button_names or axis_names mappings passed to the contruct
        maps to a discovered input control, then use that name when emitting
        events for that input control, otherwise emit using a default name.

        returns: tuple of 
        - button: string name of button if a button changed, otherwise None
        - button_state: number 0 or 1 if a button changed, otherwise None
        - axis: string name of axis if an axis changed, otherwise None
        - button_state: number -1 to 1 if an axis changed, otherwise None
        '''
        button = None
        button_state = None
        axis = None
        axis_val = None

        # just return None until the joystick device is online
        if self.jsdev is None:
            return button, button_state, axis, axis_val

        # make sure there is enough data to read
        # >> NOTE: this call blocks if no bytes are available
        if len(self.jsdev.peek(8)) < 8:
            return button, button_state, axis, axis_val

        # Main event loop
        # >> NOTE: this call blocks until 8 bytes are available
        evbuf = self.jsdev.read(8) 

        if evbuf:
            # 'IhBB' = unsigned int 32bits, signed int 16 bits, unsigned int 8 bits, unsigned int 8 bits
            tval, value, typev, number = struct.unpack('IhBB', evbuf)

            if typev & 0x80:
                #ignore initialization event
                return button, button_state, axis, axis_val

            if typev & 0x01:
                button = self.button_map[number]
                if button:
                    self.button_states[button] = value
                    button_state = value
                    logger.debug("button: %s state: %d" % (button, value))

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue
                    logger.debug("axis: %s val: %f" % (axis, fvalue))

        return button, button_state, axis, axis_val


class InputControllerEvents(object):
    '''
    Poll a AbstractGameController() and convert to button and axis events.
    '''
    def __init__(self, memory: Memory, joystick: AbstractInputController, poll_delay=0.0):
        self.memory = memory
        self.controller = joystick
        self.button_states = {} # most recent state for each button
        self.axis_states = {}   # most recent state for each axis
        self.button_events = {} # collected button events to emit
        self.axis_events = {}   # collected axis events to emit
        self.previous_button_events = {} # collected button events to delete
        self.previous_axis_events = {}   # collected axis events to delete
        self.lock = threading.Lock()
        self.poll_delay = poll_delay
        self.running = True

    def init_controller(self):
        # wait for joystick to be online
        wait_until = time.time() + 5  # wait for 5 seconds for joystick
        joystick_initialized = self.controller.init()
        while self.running and (wait_until > time.time()) and not joystick_initialized:
            if not joystick_initialized:
                time.sleep(1)
            joystick_initialized = self.controller.init()
        if not joystick_initialized:
            raise Exception("Unabled to initialize joystick after 5 seconds.")
        self.controller.show_map()


    def poll(self):
        '''
        poll a joystick once for input events
        '''
        if self.running:

            # >> NOTE: this call blocks if no bytes are available
            button, button_state, axis, axis_val = self.controller.poll()

            if button is not None or axis is not None:
                with self.lock:
                    #
                    # check for axis change and turn it into an event
                    #
                    if axis is not None:
                        if self.axis_states.get(axis, None) != axis_val:
                            self.axis_states[axis] = axis_val
                            self.axis_events[format_axis_event(axis)] = axis_val

                    #
                    # check for button change and turn it into an event
                    #
                    if button is not None:
                        if button_state != self.button_states.get(button, None):
                            self.button_states[button] = button_state
                            if button_state == 0:
                                #
                                # turn button up into click
                                #
                                self.button_events[format_button_event(button)] = BUTTON_CLICK
                            
                            


    def update(self):
        '''
        Continually poll a joystick for input events.
        - This is meant to be run in a thread.
        - Use run_threaded() to move events into self.memory()
        '''

        # wait for joystick to be online
        wait_until = time.time() + 5  # wait for 5 seconds for joystick
        joystick_initialized = self.controller.init()
        while self.running and (wait_until > time.time()) and not joystick_initialized:
            if not joystick_initialized:
                time.sleep(1)
            joystick_initialized = self.controller.init()
        if not joystick_initialized:
            raise Exception("Unabled to initialize joystick after 5 seconds.")
        self.controller.show_map()

        while self.running:
            self.poll()
            time.sleep(self.poll_delay)

    def run_threaded(self):
        '''
        emit the button and axis events into the memory
        '''
        if self.running:
            # do a quick check to see if aquiring the lock is necessary
            if self.button_events or self.axis_events or self.previous_button_events or self.previous_axis_events:
                with self.lock:
                    # clear prior one-shot events
                    self.memory.remove(self.previous_button_events.keys())
                    self.memory.remove(self.previous_axis_events.keys())

                    # emit new one-shot events
                    self.memory.update(self.button_events)
                    self.memory.update(self.axis_events)

                    # remember the new events so we can remove them later
                    self.previous_button_events = self.button_events
                    self.previous_axis_events = self.axis_events
                    self.button_events = {}
                    self.axis_events = {}

    def shutdown(self):
        self.running = False


# TODO: add __main__ that creates a vehicle and displays events from a game controller
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-th", "--threaded", default="true", type=str, help = "run in threaded mode.")
    args = parser.parse_args()


    #Initialize car
    loop_rate = 20                  # 20 interations per second for vehicle loop
    loop_duration = 1.0 / loop_rate # minium duration for each iteration of the vehicle loop

    #
    # step 1: collect button and axis names
    # - init must be called to initialize the 
    #
    controller = LinuxGameController(button_names={}, axis_names={})

    #
    # step 2: start sending events
    # >> Note that poll_delay of zero is important because some drivers buffer
    #    axis changes and so delaying only delays sending stale values.
    #
    memory = Memory()
    controller_events = InputControllerEvents(memory=memory, joystick=controller, poll_delay=0.0001)
    controller_events.init_controller()


    #
    # start the threaded part
    # and a threaded window to show plot
    #
    update_thread = None
    if args.threaded.lower() == "true":
        update_thread = threading.Thread(target=controller_events.update, args=())
        update_thread.start()

    try:
        while controller_events.running:
            loop_end = time.time() + loop_duration

            # fake running on a background thread
            if update_thread is None:
                while controller_events.running and (time.time() < loop_end):
                    controller_events.poll()

            # move collected events into memory and remove the prior events
            controller_events.run_threaded()

            # print button and axis events
            for key in memory.keys():
                if key.startswith(format_button_event("")) or key.startswith(format_axis_event("")):
                    print(f"'{key}' = '{memory[key]}'")

            # delay to achieve desired loop rate
            loop_delay = loop_end - time.time()
            if loop_delay > 0:
                time.sleep(loop_delay)

    except KeyboardInterrupt:
        controller_events.shutdown()
    finally:
        controller_events.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end

