import os
import array
import time
import struct
import random
import threading
import logging

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

class AbstractController(object):
    def init(self) -> bool:
        '''
        Attempt to initialize the controller. Should be defined by derived class
        Should return true on successfully created joystick object
        '''
        raise(Exception("Subclass needs to define init()"))

    def poll(self):
        '''
        query the state of the joystick, returns button which was pressed, if any,
        and axis which was moved, if any. button_state will be None, 1, or 0 if no changes,
        pressed, or released. axis_val will be a float from -1 to +1. button and axis will
        be the string label determined by the axis map in init.
        '''
        raise(Exception("Subclass needs to define poll()"))



class GameController(AbstractController):
    '''
    An interface to a physical joystick.
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
        self.jsdev = None
        self.dev_fn = dev_fn


    def init(self) -> bool:
        """
        Query available buttons and axes given
        a path in the linux device tree.
        """
        try:
            from fcntl import ioctl
        except ModuleNotFoundError:
            self.num_axes = 0
            self.num_buttons = 0
            logger.warn("no support for fnctl module. joystick not enabled.")
            return False

        if not os.path.exists(self.dev_fn):
            logger.warn(f"{self.dev_fn} is missing")
            return False

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
                    logger.info("button: %s state: %d" % (button, value))

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue
                    logger.debug("axis: %s val: %f" % (axis, fvalue))

        return button, button_state, axis, axis_val


class ControllerEvents(object):
    '''
    Poll a GameController() and convert to button and axis events.
    '''
    def __init__(self, memory: Memory, joystick: GameController, poll_delay=0.0):
        self.memory = memory
        self.controller = joystick
        self.button_states = {} # most recent state for each button
        self.axis_states = {}   # most recent state for each axis
        self.button_events = {} # collected button events to emit
        self.axis_events = {}   # collected axis events to emit
        self.previous_button_events = {} # collected button events to delete
        self.previous_axis_events = {}   # collected axis events to delete
        self.lock = threading.Lock()
        self.running = True

    def update(self):
        '''
        poll a joystick for input events
        '''

        #wait for joystick to be online
        while self.running and self.controller is None and not self.init_js():
            time.sleep(3)

        while self.running:
            button, button_state, axis, axis_val = self.controller.poll()

            if button is not None or axis is not None:
                with self.lock:
                    #
                    # check for axis change and turn it into an event
                    #
                    if axis is not None:
                        if self.axis_states.get(axis, None) != axis_val:
                            self.axis_states[axis] = axis_val
                            self.axis_events[axis] = axis_val

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
                                self.button_states[button] = button_state
                                self.button_events[button] = BUTTON_CLICK

            time.sleep(self.poll_delay)

    def run_threaded(self):
        '''
        emit the button and axis events into the memory
        '''
        with self.lock:
            # clear prior one-shot events
            for button in self.previous_button_events:
                del self.memory[format_button_event(button)]

            for axis in self.previous_axis_events:
                del self.memory[format_axis_event(axis)]

            # emit new one-shot events
            for button in self.button_events:
                self.memory[format_button_event(button)] = self.button_events[button]

            for axis in self.axis_events:
                self.memory[format_axis_event(axis)] = self.axis_events[axis]

            self.previous_button_events = self.button_events
            self.previous_axis_events = self.axis_events
            self.button_events = {}
            self.axis_events = {}

    def shutdown(self):
        self.running = False


# TODO: add __main__ that creates a vehicle and displays events from a game controller
if __name__ == "__main__":
    #Initialize car

    #
    # step 1: collect button and axis names
    #
    controller = GameController(button_names=[], axis_names=[])
    controller.show_map()

    #
    # step 2: start sending events
    #
    memory = Memory()
    controller_events = ControllerEvents(memory=memory, joystick=controller, poll_delay=0.1)
    while controller_events.running:
        controller_events.update()
        controller_events.run_threaded()
        print( memory )
