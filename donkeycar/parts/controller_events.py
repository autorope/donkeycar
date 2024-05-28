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

BUTTON_DOWN = "press"                   # button changed to down state
BUTTON_UP = "release"                   # button changed to up state
BUTTON_CLICK = "click"                  # button completed one or more sequential down to up cycles

def format_button_click_event(button: str, click_count: int) -> str:
    return format_button_event(button, f'click/{click_count}')

BUTTON_EVENT = '/event/button/'
def format_button_event(button: str, event: str) -> str:
    return f'/event/button/{button}/{event}'

AXIS_EVENT = '/event/axis/'
def format_axis_event(axis) -> str:
    return f'/event/axis/{axis}'

BUTTON_STATE = '/button/'
def format_button_key(button: str) -> str:
    return f'/button/{button}'

AXIS_STATE = '/axis/'
def format_axis_key(axis: str) -> str:
    return f'/axis/{axis}'

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


    def poll(self) -> tuple[str | None, int | None, str | ModuleNotFoundError, float | None]:
        '''
        Query the input controller for a button or axis state change event.
        This must be threadsafe as it will generally be called on
        a separate thread.

        returns: tuple of 
        - button: string name of button if a button changed, otherwise None
        - button_state: int of 0 or 1 if a button changed, otherwise None
        - axis: string name of axis if an axis changed, otherwise None
        - button_state: float between -1 to 1 if an axis changed, otherwise None
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
        self.axis_names = axis_names
        self.button_names = button_names
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
        If the button_names or axis_names mappings passed to the contructor
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
            self.axis_names[axis] = axis_name # update the name map

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(self.jsdev, 0x80406a34, buf) # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = self.button_names.get(btn, 'button(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0
            self.button_names[btn] = btn_name # update the name map

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


class LogitechJoystick(LinuxGameController):
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


class InputControllerEvents(object):
    '''
    Poll a AbstractGameController() and convert to button and axis events.
    '''
    def __init__(self, memory: Memory, joystick: AbstractInputController, fast_click=0.2):
        self.memory = memory
        self.controller = joystick
        self.button_states = {} # most recent state for each button; int where 0 = up, 1 = down OR None on startup
        self.button_times = {}  # time of most recent state change for each button OR None on startup
        self.button_clicks = {} # number of sequential clicks for a button
        self.button_outputs = {}# state change to be written as persistent outputs
        self.previous_button_events = {} # collected button events to delete
        self.axis_states = {}   # most recent state for each axis; float in range -1 and 1 inclusive OR None on startup
        self.button_events = {} # collected button events to emit
        self.axis_events = {}   # collected axis events to emit
        self.axis_outputs = {}  # state changes to be written as persistent outputs
        self.previous_axis_events = {}   # collected axis events to delete
        self.lock = threading.Lock()
        self.fast_click_time = fast_click

        self.init_controller()
        self.running = True


    def init_controller(self):
        # wait for joystick to be online
        wait_until = time.time() + 5  # wait for 5 seconds for jstring representing sequential clicks as '.' for short and '-' for long, for example short followed by long would be ".-"oystick
        joystick_initialized = self.controller.init()
        while (wait_until > time.time()) and not joystick_initialized:
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
            try:
                # >> NOTE: this call blocks if no bytes are available
                button, button_state, axis, axis_val = self.controller.poll()

                if self.running and (button is not None or axis is not None):
                    with self.lock:
                        #
                        # check for axis change and turn it into an event
                        #
                        now = time.time()
                        if axis is not None:
                            if self.axis_states.get(axis, None) != axis_val:
                                self.axis_states[axis] = axis_val
                                # save state change as an event and as a persistent output
                                self.axis_events[format_axis_event(axis)] = axis_val
                                self.axis_outputs[format_axis_key(axis)] = axis_val

                        #
                        # check for button change and turn into press/release/click events
                        #
                        if button is not None:
                            if button_state != self.button_states.get(button, None):
                                # save state change as a persistent output
                                self.button_outputs[format_button_key(button)] = button_state
                                if button_state == 1:
                                    # transition to down event with time as value
                                    self.button_events[format_button_event(button, BUTTON_DOWN)] = now

                                    #
                                    # if this was a fast transtion from up to down, 
                                    # then count it as a sequential click,
                                    # otherwise clear the sequential click count
                                    #
                                    fast_click = (now - self.button_times.get(button, 0)) <= self.fast_click_time
                                    if fast_click:  # count sequential click
                                        self.button_clicks[button] = self.button_clicks.get(button, 0) + 1
                                    else:  # clear squential click counter
                                        self.button_clicks[button] = 0
                                elif button_state == 0:
                                    # transition from down to up event with time as value
                                    self.button_events[format_button_event(button, BUTTON_UP)] = now

                                    #
                                    # convert to sequential clicks with 1-based click count
                                    #
                                    click_count = self.button_clicks.get(button, 0) + 1
                                    self.button_events[format_button_click_event(button, click_count)] = now

                                # set the new button state and time
                                self.button_states[button] = button_state
                                self.button_times[button] = now
            except:
                self.running = False

    def update(self):
        '''
        Continually poll a joystick for input events.
        - This is meant to be run in a thread.
        - Use run_threaded() to move events into self.memory()
        '''
        try:
            while self.running:
                self.poll()
        except:
            self.running = False

    def run_threaded(self):
        '''
        emit the button and axis events into the memory
        '''
        if self.running:
            # do a quick check to see if aquiring the lock is necessary
            if self.axis_outputs or self.button_outputs or self.button_events or self.axis_events or self.previous_button_events or self.previous_axis_events:
                with self.lock:
                    # update persistent state with any changes
                    self.memory.update(self.axis_outputs)
                    self.axis_outputs = {}

                    self.memory.update(self.button_outputs)
                    self.button_outputs = {}

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


class TogglePilotMode:
    '''
    Part that toggles pilot modes: user -> local_angle -> local -> user
    - When added to the vehicle loop, the input should be 'user/mode' and 
      the output should be 'user/mode'.
    - When added to the vehicle loop, this should be configured with a 
      run_condition so it only toggles the mode when the run_condition is
      set.  The run_conditin should only live for a _single_ pass throught
      the vehicle event loop so that part only gets run once.
    - This is meant to be used with input controller events where the controller
      manages the event that is then used as the run_condition for this part.
    - For instance, if pressing 'button1' toggles the pilot mode, then
      the run condition should be 'run_condition="/event/button/button1/press"'
    - For instance, if double-click of 'button3' toggles the pilot mode, then
      the run condition should be 'run_condition="/event/button/button1/click/2"'
    '''

    def run(self, mode: str) -> str:
        '''
        toggle pilot mode in order: user -> local_angle -> local -> user
        '''
        if mode == 'user':
            mode = 'local_angle'
        elif mode == 'local_angle':
            mode = 'local'
        else:
            mode = 'user'
        logger.info(f'toggled to mode: {mode}')

        # output the new value
        return mode


class UserThrottle:
    def __init__(self, throttle_dir: int = 1, throttle_scale: float = 1.0) -> None:
        self.throttle_dir = throttle_dir
        self.throttle_scale = throttle_scale
        self.running = True

    def run(self, throttle_axis: float) -> float:
        throttle: float = 0.0
        if self.running:
            throttle = (self.throttle_dir * throttle_axis * self.throttle_scale)
            print(f"Throttle = {throttle}")

        return throttle

    def shutdown(self) -> None:
        self.running = False

class UserSteering:
    def __init__(self, steering_scale: float = 1.0) -> None:
        self.steering_scale = steering_scale
        self.running = True

    def run(self, steering_axis: float) -> float:
        steering = 0.0
        if self.running:
            steering = self.steering_scale * steering_axis
            print(f"Steering = {steering}")
        return steering

    def shutdown(self) -> None:
        self.running = False


class StopVehicle:
    from donkeycar.vehicle import Vehicle
    '''
    Part to stop vehicle with a keypress
    '''
    def __init__(self, vehicle: Vehicle) -> None:
        self.vehicle = vehicle
        self.running = True

    def run(self, key_state: int) -> None:
        if self.running and key_state:
            self.running = False
            self.vehicle.on = False

    def stop(self):
        self.running = False


# TODO: add __main__ that creates a vehicle and displays events from a game controller
if __name__ == "__main__":
    from donkeycar.vehicle import Vehicle
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-th", "--threaded", default="true", type=str, help = "run in threaded mode.")
    parser.add_argument("-ve", "--vehicle", default="true", type=str, help = "run using Vehicle loop.")

    args = parser.parse_args()


    #Initialize car
    loop_rate = 20                  # 20 interations per second for vehicle loop
    loop_duration = 1.0 / loop_rate # minium duration for each iteration of the vehicle loo
    update_thread = None
    if args.vehicle.lower() == "true":
        # use an actual Vehicle loop
        vehicle = Vehicle()
        vehicle.add(InputControllerEvents(memory=vehicle.mem, joystick=LogitechJoystick()), threaded=True)

        # toggle pilot mode when 'Y' button is pressed
        vehicle.add(TogglePilotMode(), inputs=['/user/mode'], outputs=['/user/mode'], run_condition=format_button_event("Y", "press"))

        # part to change user throttle when joystick axis changes
        # - throttle axis event is used as run_condition to part only runs when the throttle axis changes
        # - throttle axis event is used as the input so the part gets the changed throttle when it runs
        throttle_event = format_axis_event("right_stick_vert")
        vehicle.add(UserThrottle(throttle_dir=-1), inputs=[throttle_event], outputs=["user/throttle"], run_condition=throttle_event)

        # part to change user steering when joystick axis changes
        # - steering axis event is used as run_condition to part only runs when the steering axis changes
        # - steering axis event is used as the input so the part gets the changed steering when it runs
        steering_event = format_axis_event("left_stick_horz")
        vehicle.add(UserSteering(), inputs=[steering_event], outputs=["user/steering"], run_condition=steering_event)

        # part to quit the vehicle when a button gesture is done
        # - quit when 'B' button is double-clicked while holding down the 'X' button
        # - The 'B' button double-click event is used as the run condition so it only runs on a double-click of B
        # - The state of the 'X' button is taken as an input so it can test to see if it should quit when it runs
        vehicle.add(StopVehicle(vehicle), inputs=[format_button_key('X')], run_condition=format_button_click_event('B', 2))

        # Let's do this thing...
        vehicle.start(rate_hz=loop_rate)

    else:
        #
        # simulate the vehicle loop so we can easily introspect memory
        #
        #
        # step 1: collect button and axis names
        # - init must be called to initialize the 
        #
        # controller = LinuxGameController(button_names={}, axis_names={})
        controller = LogitechJoystick()
        

        #
        # step 2: start sending events
        # >> Note that poll_delay of zero is important because some drivers buffer
        #    axis changes and so delaying only delays sending stale values.
        #
        memory = Memory()
        controller_events = InputControllerEvents(memory=memory, joystick=controller)

        #
        # start the threaded part
        # and a threaded window to show plot
        #
        if args.threaded.lower() == "true":
            update_thread = threading.Thread(target=controller_events.update, args=())
            update_thread.daemon = True
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
                    if key.startswith(BUTTON_EVENT) or key.startswith(AXIS_EVENT):
                        print(f"'{key}' = '{memory[key]}'")

                # delay to achieve desired loop rate
                loop_delay = loop_end - time.time()
                if loop_delay > 0:
                    time.sleep(loop_delay)

        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            controller_events.shutdown()

