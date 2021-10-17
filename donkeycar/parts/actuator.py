"""
actuators.py
Classes to control the motors and servos. These classes 
are wrapped in a mixer class before being used in the drive loop.
"""

from abc import ABC, abstractmethod
from os import P_NOWAIT
import time

from Adafruit_GPIO.GPIO import FALLING

import donkeycar as dk
import RPi.GPIO as GPIO
import Adafruit_PCA9685
from Adafruit_GPIO import I2C



# 
##### Base interface for input/output/pwm pins
##### Implementations derive from these abstact classes
#
class PinState:
    LOW:int = 0
    HIGH:int = 1
    NOT_STARTED:int = -1


class PinEdge:
    RISING:int = 1
    FALLING:int = 2
    BOTH:int = 3


class PinPull:
    PULL_NONE:int = 1
    PULL_UP:int = 2
    PULL_DOWN:int = 3


class PinProvider:
    RPI_GPIO = "RPI_GPIO"
    PCA9685 = "PCA9685"
    # PIGPIO = "PIGPIO"


class PinScheme:
    BOARD = "BOARD"  # board numbering
    BCM = "BCM"      # broadcom gpio numbering



class InputPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, on_input=None, edge=PinEdge.RISING) -> None:
        """
        Start the pin in input mode.
        on_input: function to call when an edge is detected, or None to ignore
        edge: type of edge(s) that trigger on_input; default is PinEdge.RISING
        This raises a RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the pin and return it to PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def state(self) -> int:
        """
        Return most recent input state.  This does not re-read the input pin,
        it just returns that last value read by the input() method.
        If the pin is not started or has been stopped, 
        this will return PinState:NOT_STARTED
        """
        return PinState.NOT_STARTED  # subclasses must override

    @abstractmethod
    def input(self) -> int:
        """
        Read the input state from the pin.
        """
        return PinState.NOT_STARTED  # subclasses must override


class OutputPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, state:int=PinState.LOW) -> None:
        """
        Start the pin in output mode and with given starting state.
        This raises and RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the pin and return it to PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def state(self) -> int:
        """
        Return most recent output state.  This does not re-read the pin,
        It just returns that last value set by the output() method.
        If the pin is not started or has been stopped, 
        this will return PinState:NOT_STARTED
        """
        return PinState.NOT_STARTED  # subclasses must override

    @abstractmethod
    def output(self, state:int) -> None:
        """
        Set the output state of the pin to either
        PinState.LOW or PinState.HIGH
        """
        pass  # subclasses must override
        

class PwmPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, state:float=0) -> None:
        """
        Start the pin in output mode and with given starting state.
        This raises and RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the pin and return it to PinState.NOT_STARTED
        """
        pass  # subclasses should override this

    @abstractmethod
    def state(self) -> float:
        """
        Return most recent output state.  This does not re-read the pin,
        It just returns that last value set by the output() method.
        If the pin is not started or has been stopped, 
        this will return PinState:NOT_STARTED
        """
        return PinState.NOT_STARTED  # subclasses must override

    @abstractmethod
    def dutyCycle(self, state:float) -> None:
        """
        Set the output duty cycle of the pin 
        in range 0 to 1.0 (0% to 100%)
        """
        pass  # subclasses must override



#
# Pin id allows pins to be selected using a single string to
# select from different underlying providers, numbering schemes and settings.
#
# Use Rpi.GPIO library, GPIO.BOARD pin numbering scheme, pin number 13
# "RPI_GPIO.BOARD.13"
#
# Use Rpi.GPIO library, GPIO.BCM broadcom pin numbering scheme, gpio pin number 33
# "RPI_GPIO.BCM.33"
#
# Use PCA9685 on bus 0 at address 0x40, channel 7
# "PCA9685.0:40.7"
#
def output_pin_by_id(pin_id:str) -> OutputPin:
    """
    Select a ttl output pin given a pin id.
    """
    parts = pin_id.split(".")
    if parts[0] == PinProvider.PCA9685:
        pin_provider = parts[0]
        i2c_bus, i2c_address, frequency_hz = parts[1].split(":")
        i2c_bus = int(i2c_bus)
        i2c_address = int(i2c_address, base=16)
        frequency_hz = int(frequency_hz)
        pin_number = int(parts[2])
        return output_pin(pin_provider, pin_number, i2c_bus=i2c_bus, i2c_address=i2c_address, frequency_hz=frequency_hz)

    if parts[0] == PinProvider.RPI_GPIO:
        pin_provider = parts[0]
        pin_scheme = parts[1]
        pin_number = int(parts[2])
        return output_pin(pin_provider, pin_number, pin_scheme=pin_scheme)


def pwm_pin_by_id(pin_id:str, frequency_hz:int=60) -> OutputPin:
    """
    Select a pwm output pin given a pin id.
    """
    parts = pin_id.split(".")
    if parts[0] == PinProvider.PCA9685:
        pin_provider = parts[0]
        i2c_bus, i2c_address = parts[1].split(":")
        i2c_bus = int(i2c_bus)
        i2c_address = int(i2c_address, base=16)
        pin_number = int(parts[2])
        return pwm_pin(pin_provider, pin_number, i2c_bus=i2c_bus, i2c_address=i2c_address, frequency_hz=frequency_hz)

    if parts[0] == PinProvider.RPI_GPIO:
        pin_provider = parts[0]
        pin_scheme = parts[1]
        pin_number = int(parts[2])
        return pwm_pin(pin_provider, pin_number, pin_scheme=pin_scheme, frequency_hz=frequency_hz)


def input_pin_by_id(pin_id:str, pull:int=PinPull.PULL_NONE) -> OutputPin:
    """
    Select a ttl input pin given a pin id.
    """
    parts = pin_id.split(".")
    if parts[0] == PinProvider.PCA9685:
        raise RuntimeError("PinProvider.PCA9685 does not implement InputPin")

    if parts[0] == PinProvider.RPI_GPIO:
        pin_provider = parts[0]
        pin_scheme = parts[1]
        pin_number = int(parts[2])
        return input_pin(pin_provider, pin_number, pin_scheme=pin_scheme, pull=pull)


def input_pin(pin_provider:str, pin_number:int, pin_scheme:str=PinScheme.BOARD, pull:int=PinPull.PULL_NONE) -> InputPin:
    """
    construct an InputPin using the given pin provider
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return InputPinGpio(pin_number, pin_scheme, pull)
    if pin_provider == PinProvider.PCA9685:
        raise RuntimeError("PinProvider.PCA9685 does not implement InputPin")
    raise RuntimeError("UnknownPinProvider ({})".format(pin_provider))


def output_pin(pin_provider:str, pin_number:int, pin_scheme:str=PinScheme.BOARD, i2c_bus:int=0, i2c_address:int=40, frequency_hz:int=60) -> OutputPin:
    """
    construct an output pin using the given pin provider
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return OutputPinGpio(pin_number, pin_scheme)
    if pin_provider == PinProvider.PCA9685:
        return OutputPinPCA9685(pin_number, frequency_hz, i2c_bus, i2c_address)
    raise RuntimeError("UnknownPinProvider ({})".format(pin_provider))


def pwm_pin(pin_provider:str, pin_number:int, pin_scheme:str=PinScheme.BOARD, frequency_hz:int=60, i2c_bus:int=0, i2c_address:int=40) -> PwmPin:
    """
    construct a PwmPin using the given pin provider
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return PwmPinGpio(pin_number, pin_scheme, frequency_hz)
    if pin_provider == PinProvider.PCA9685:
        return PwmPinPCA9685(pin_number, frequency_hz, i2c_bus, i2c_address)
    raise RuntimeError("UnknownPinProvider ({})".format(pin_provider))


#
# RPi.GPIO/Jetson.GPIO implementations
#
def gpio_fn(pin_scheme, fn):
    """
    Convenience method to call GPIO function
    using desired pin scheme.  This restores
    the previous pin scheme, so it is safe to 
    mix pin schemes.
    """
    prev_scheme = GPIO.getmode() or pin_scheme
    GPIO.setmode(pin_scheme)
    val = fn()
    GPIO.setmode(prev_scheme)
    return val


# lookups to convert abstact api to GPIO values
gpio_pin_edge = [GPIO.RISING, GPIO.FALLING, GPIO.BOTH]
gpio_pin_pull = [GPIO.PUD_OFF, GPIO.PUD_DOWN, GPIO.PUD_UP]
gpio_pin_scheme = {PinScheme.BOARD: GPIO.BOARD, PinScheme.BCM: GPIO.BCM}


class InputPinGpio(InputPin):
    def __init__(self, pin_number:int, pin_scheme:str, pull=PinPull.PULL_NONE) -> None:
        """
        Input pin ttl HIGH/LOW using RPi.GPIO/Jetson.GPIO
        pin_number: GPIO.BOARD mode point number
        pull: enable a pull up or down resistor on pin.  Default is PinPull.PULL_NONE
        """
        self.pin_number = pin_number
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self.pull = pull
        self._state = PinState.NOT_STARTED
        super().__init__()

    def start(self, on_input=None, edge=PinEdge.RISING) -> None:
        """
        on_input: function to call when an edge is detected, or None to ignore
        edge: type of edge(s) that trigger on_input; default is 
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError("Attempt to start InputPin that is already started.")
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.IN, pull_up_down=gpio_pin_pull(self.pull)))
        if on_input is not None:
            gpio_fn(self.pin_scheme, lambda: GPIO.add_event_detect(self.pin_number, gpio_pin_edge(edge), callback=on_input))
        self.input()  # read first state

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
            self._state = PinState.NOT_STARTED

    def state(self) -> int:
        return self._state

    def input(self) -> int:
        self._state = gpio_fn(self.pin_scheme, lambda: GPIO.input(self.pin_number))
        return self._state


class OutputPinGpio(OutputPin):
    """
    Output pin ttl HIGH/LOW using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number:int, pin_scheme:str) -> None:
        self.pin_number = pin_number
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self._state = PinState.NOT_STARTED

    def start(self, state:int=PinState.LOW) -> None:
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError("Attempt to start OutputPin that is already started.")
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.OUT))
        self.output(state)

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
            self._state = PinState.NOT_STARTED

    def state(self) -> int:
        return self._state

    def output(self, state: int) -> None:
        gpio_fn(self.pin_scheme, lambda: GPIO.output(self.pin_number, state))
        self._state = state


class PwmPinGpio(PwmPin):
    """
    PWM output pin using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number:int, pin_scheme:str, frequency_hz = 50) -> None:
        self.pin_number = pin_number
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self.frequency = frequency_hz
        self.pwm = None
        self._state = PinState.NOT_STARTED

    def start(self, duty_cycle:float=0) -> None:
        if self.pwm is not None:
            raise RuntimeError("Attempt to start PwmPinGpio that is already started.")
        if duty_cycle < 0 or duty_cycle > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.OUT))
        self.pwm = gpio_fn(self.pin_scheme, lambda: GPIO.PWM(self.pin_number, self.frequency))
        self.dutyCycle(duty_cycle)
        self._state = duty_cycle

    def stop(self) -> None:
        if self.pwm is not None:
            self.pwm.stop()
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
        self._state = PinState.NOT_STARTED

    def state(self) -> float:
        return self._state

    def dutyCycle(self, duty_cycle: float) -> None:
        if duty_cycle < 0 or duty_cycle > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pwm.ChangeDutyCycle(duty_cycle * 100)
        self._state = duty_cycle


#
# PCA9685 implementations
# 
class OutputPinPCA9685(ABC):
    """
    Output pin ttl HIGH/LOW using PCA9685
    """
    def __init__(self, pin_number:int, frequency_hz:int, i2c_bus:int, i2c_address:int) -> None:
        self.pin_number = pin_number
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.frequency_hz = frequency_hz
        self.pca9685 = None
        self._state = PinState.NOT_STARTED

    def start(self, state:int=PinState.LOW) -> None:
        """
        Start the pin in output mode.
        This raises and RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        """
        if self.pca9685 is not None:
            raise RuntimeError("Attempt to start pin ({}) that is already started".format(self.pin_number))
        self.pca9685 = PCA9685(self.pin_number, self.i2c_address, self.frequency_hz, self.i2c_bus)
        self.output(state)

    def stop(self) -> None:
        """
        Stop the pin and return it to PinState.NOT_STARTED
        """
        if self.pca9685 is not None:
            self.output(PinState.LOW)
            self.pca9685 = None
        self._state = PinState.NOT_STARTED

    def state(self) -> int:
        """
        Return most recent output state.  
        If the pin is not started or has been stopped, 
        this will return PinState:NOT_STARTED
        """
        return self._state

    def output(self, state: int) -> None:
        self.pca9685.set_pulse(1 if state == PinState.HIGH else 0)
        self._state = state


class PwmPinPCA9685(PwmPin):
    """
    PWM output pin using PCA9685
    """
    def __init__(self, pin_number:int, frequency_hz:int, i2c_bus:int, i2c_address:int) -> None:
        self.pin_number = pin_number
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.frequency_hz = frequency_hz
        self.pca9685 = None
        self._state = PinState.NOT_STARTED

    def start(self, duty_cycle:float=0) -> None:
        if self.pca9685 is not None:
            raise RuntimeError("Attempt to start pin ({}) that is already started".format(self.pin_number))
        if duty_cycle < 0 or duty_cycle > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pca9685 = PCA9685(self.pin_number, self.i2c_address, self.frequency_hz, self.i2c_bus)
        self.duty_cycle(duty_cycle)
        self._state = duty_cycle

    def stop(self) -> None:
        if self.pca9685 is not None:
            self.duty_cycle(0)
            self.pca9685 = None
        self._state = PinState.NOT_STARTED

    def state(self) -> float:
        return self._state

    def duty_cycle(self, duty: float) -> None:
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pca9685.set_duty_cycle(duty)
        self._state = duty


class L298N_HBridge_3pin(object):
    '''
    Motor controlled with an L298N hbridge
    Uses two OutputPins and a PwmPin to control the L298N.
    See https://www.etechnophiles.com/l298n-motor-driver-pin-diagram/

    pin_forward:OutputPin when this is enabled the motor will turn clockwise 
                          using the output of the pwm_pin as a duty_cycle
    pin_backward:OutputPin when this is enabled the motor will turn counter-clockwise
                          using the output of the pwm_pin as a duty_cycle
    pwm_pin:PwmPin takes a duty cycle in the range of 0 to 1, 
                   where 0 is fully off and 1 is fully on.
    zero_throttle: values at or below zero_throttle are treated as zero.
    max_duty: the maximum duty cycle that will be send to the motors

    NOTE: if pin_forward and pin_backward are both LOW, then the motor is
          'detached' and will glide to a stop.
          if pin_forward and pin_backward are both HIGH, then the motor 
          will be forcibly stopped (can be used for braking)
        
    '''
    def __init__(self, pin_forward:OutputPin, pin_backward:OutputPin, pwm_pin:PwmPin, zero_throttle:float=0, max_duty=0.9):
        import RPi.GPIO as GPIO
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.pwm_pin = pwm_pin
        self.zero_throttle = zero_throttle
        self.max_duty = max_duty
        self.pin_forward.start(PinState.LOW)
        self.pin_backward.start(PinState.LOW)
        self.pwm_pin.start(0)

    def run(self, speed):
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed > 1 or speed < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")
        
        self.speed = speed
        self.throttle = int(dk.utils.map_range(speed, -1, 1, -self.max_duty, self.max_duty))
        if self.throttle > self.zero_throttle:
            self.pwm_pin.dutyCycle(self.throttle)
            self.pin_backward.output(PinState.LOW)
            self.pin_forward.output(PinState.HIGH)
        elif self.throttle < -self.zero_throttle:
            self.pwm_pin.dutyCycle(-self.throttle)
            self.pin_forward.output(PinState.LOW)
            self.pin_backward.output(PinState.HIGH)
        else:
            self.pwm_pin.dutyCycle(0)
            self.pin_forward.output(PinState.LOW)
            self.pin_backward.output(PinState.LOW)


    def shutdown(self):
        self.pwm_pin.stop()
        self.pin_forward.stop()
        self.pin_backward.stop()


class L298N_HBridge_2pin(object):
    '''
    Motor controlled with an 'mini' L298N hbridge using 2 PwmPins.
    See https://www.instructables.com/Tutorial-for-Dual-Channel-DC-Motor-Driver-Board-PW/

    pin_forward:PwmPin Takes a duty cycle in the range of 0 to 1, 
                       where 0 is fully off and 1 is fully on.
                       When the duty_cycle > 0 the motor will turn clockwise 
                       proportial to the duty_cycle
    pin_backward:PwmPin Takes a duty cycle in the range of 0 to 1, 
                        where 0 is fully off and 1 is fully on.
                        When the duty_cycle > 0 the motor will turn counter-clockwise 
                        proportial to the duty_cycle
    zero_throttle: values at or below zero_throttle are treated as zero.
    max_duty: the maximum duty cycle that will be send to the motors

    NOTE: if pin_forward and pin_backward are both at duty_cycle == 0, 
          then the motor is 'detached' and will glide to a stop.
          if pin_forward and pin_backward are both at duty_cycle == 1, 
          then the motor will be forcibly stopped (can be used for braking)
    '''
    def __init__(self, pin_forward:PwmPin, pin_backward:PwmPin, zero_throttle:float=0, max_duty = 0.9):
        '''
        max_duty is from 0 to 1 (fully off to fully on). I've read 0.9 is a good max.
        '''
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.zero_throttle = zero_throttle
        self.max_duty = max_duty

        self.throttle=0
        self.speed=0
        
        self.pin_forward.start(0)
        self.pin_backward.start(0)

    def run(self, throttle):
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if throttle is None:
            return
        
        if throttle > 1 or throttle < -1:
            raise ValueError( "Throttle must be between 1(forward) and -1(reverse)")
        
        self.speed = throttle
        self.throttle = int(dk.utils.map_range(throttle, -1, 1, -self.max_duty, self.max_duty))
        
        if self.throttle > self.zero_throttle:
            self.pin_backward.dutyCycle(0)
            self.pin_forward.dutyCycle(self.throttle)
        elif self.throttle < -self.zero_throttle:
            self.pin_forward.dutyCycle(0)
            self.pin_backward.dutyCycle(-self.throttle)
        else:
            self.pin_forward.dutyCycle(0)
            self.pin_backward.dutyCycle(0)

    def shutdown(self):
        self.pin_forward.stop()
        self.pin_backward.stop()


class PCA9685:
    ''' 
    PWM motor controler using PCA9685 boards. 
    This is used for most RC Cars
    '''
    def __init__(self, channel, address=0x40, frequency=60, busnum=None, init_delay=0.1):

        self.default_freq = 60
        self.pwm_scale = frequency / self.default_freq

        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        if busnum is not None:
            from Adafruit_GPIO import I2C
            # replace the get_bus function with our own
            def get_bus():
                return busnum
            I2C.get_default_bus = get_bus
        self.pwm = Adafruit_PCA9685.PCA9685(address=address)
        self.pwm.set_pwm_freq(frequency)
        self.channel = channel
        time.sleep(init_delay) # "Tamiya TBLE-02" makes a little leap otherwise

    def set_duty_cycle(self, duty_cycle):
        if duty_cycle < 0 or duty_cycle > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        # duty cycle is fraction of the 12 bits
        self.pwm.set_pwm(self.channel, 0, int(4096 * duty_cycle))

    def set_pulse(self, pulse):
        try:
            self.pwm.set_pwm(self.channel, 0, int(pulse * self.pwm_scale))
        except:
            self.pwm.set_pwm(self.channel, 0, int(pulse * self.pwm_scale))

    def run(self, pulse):
        self.set_pulse(pulse)


class PiGPIO_PWM():
    '''
    # Use the pigpio python module and daemon to get hardware pwm controls from
    # a raspberrypi gpio pins and no additional hardware. Can serve as a replacement
    # for PCA9685.
    #
    # Install and setup:
    # sudo apt update && sudo apt install pigpio python3-pigpio
    # sudo systemctl start pigpiod
    #
    # Note: the range of pulses will differ from those required for PCA9685
    # and can range from 12K to 170K
    #
    # If you use a control circuit that inverts the steering signal, set inverted to True
    # Default multipler for pulses from config etc is 100
    '''

    def __init__(self, pin, pgio=None, freq=75, inverted=False):
        import pigpio
        self.pin = pin
        self.pgio = pgio or pigpio.pi()
        self.freq = freq
        self.inverted = inverted
        self.pgio.set_mode(self.pin, pigpio.OUTPUT)
        self.dead_zone = 37000

    def __del__(self):
        self.pgio.stop()

    def set_pulse(self, pulse):
#
        self.output = pulse * 200
        if self.output > 0:
            self.pgio.hardware_PWM(self.pin, self.freq, int(self.output if self.inverted == False else 1e6 - self.output))


    def run(self, pulse):
        self.set_pulse(pulse)

class PWMSteering:
    """
    Wrapper over a PWM motor controller to convert angles to PWM pulses.
    """
    LEFT_ANGLE = -1
    RIGHT_ANGLE = 1

    def __init__(self,
                 controller=None,
                 left_pulse=290,
                 right_pulse=490):

        if controller is None:
            raise ValueError("PWMSteering requires a set_pulse controller to be passed")
        set_pulse = getattr(controller, "set_pulse", None)
        if set_pulse is None or not callable(set_pulse):
            raise ValueError("controller must have a set_pulse method")

        self.controller = controller
        self.left_pulse = left_pulse
        self.right_pulse = right_pulse
        self.pulse = dk.utils.map_range(0, self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                        self.left_pulse, self.right_pulse)
        self.running = True
        print('PWM Steering created')

    def update(self):
        while self.running:
            self.controller.set_pulse(self.pulse)

    def run_threaded(self, angle):
        # map absolute angle to angle that vehicle can implement.
        self.pulse = dk.utils.map_range(angle,
                                        self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                        self.left_pulse, self.right_pulse)

    def run(self, angle):
        self.run_threaded(angle)
        self.controller.set_pulse(self.pulse)

    def shutdown(self):
        # set steering straight
        self.pulse = 0
        time.sleep(0.3)
        self.running = False


class PWMThrottle:
    """
    Wrapper over a PWM motor controller to convert -1 to 1 throttle
    values to PWM pulses.
    """
    MIN_THROTTLE = -1
    MAX_THROTTLE = 1

    def __init__(self,
                 controller=None,
                 max_pulse=300,
                 min_pulse=490,
                 zero_pulse=350):

        if controller is None:
            raise ValueError("PWMThrottle requires a set_pulse controller to be passed")
        set_pulse = getattr(controller, "set_pulse", None)
        if set_pulse is None or not callable(set_pulse):
            raise ValueError("controller must have a set_pulse method")

        self.controller = controller
        self.max_pulse = max_pulse
        self.min_pulse = min_pulse
        self.zero_pulse = zero_pulse
        self.pulse = zero_pulse

        # send zero pulse to calibrate ESC
        print("Init ESC")
        self.controller.set_pulse(self.max_pulse)
        time.sleep(0.01)
        self.controller.set_pulse(self.min_pulse)
        time.sleep(0.01)
        self.controller.set_pulse(self.zero_pulse)
        time.sleep(1)
        self.running = True
        print('PWM Throttle created')

    def update(self):
        while self.running:
            self.controller.set_pulse(self.pulse)

    def run_threaded(self, throttle):
        if throttle > 0:
            self.pulse = dk.utils.map_range(throttle, 0, self.MAX_THROTTLE,
                                            self.zero_pulse, self.max_pulse)
        else:
            self.pulse = dk.utils.map_range(throttle, self.MIN_THROTTLE, 0,
                                            self.min_pulse, self.zero_pulse)

    def run(self, throttle):
        self.run_threaded(throttle)
        self.controller.set_pulse(self.pulse)

    def shutdown(self):
        # stop vehicle
        self.run(0)
        self.running = False

class JHat:
    ''' 
    PWM motor controller using Teensy emulating PCA9685. 
    '''
    def __init__(self, channel, address=0x40, frequency=60, busnum=None):
        print("Firing up the Hat")
        import Adafruit_PCA9685
        LED0_OFF_L = 0x08
        # Initialise the PCA9685 using the default address (0x40).
        if busnum is not None:
            from Adafruit_GPIO import I2C
            # replace the get_bus function with our own
            def get_bus():
                return busnum
            I2C.get_default_bus = get_bus
        self.pwm = Adafruit_PCA9685.PCA9685(address=address)
        self.pwm.set_pwm_freq(frequency)
        self.channel = channel
        self.register = LED0_OFF_L+4*channel

        # we install our own write that is more efficient use of interrupts
        self.pwm.set_pwm = self.set_pwm
        
    def set_pulse(self, pulse):
        self.set_pwm(self.channel, 0, pulse) 

    def set_pwm(self, channel, on, off):
        # sets a single PWM channel
        self.pwm._device.writeList(self.register, [off & 0xFF, off >> 8])
        
    def run(self, pulse):
        self.set_pulse(pulse)

class JHatReader:
    ''' 
    Read RC controls from teensy 
    '''
    def __init__(self, channel, address=0x40, frequency=60, busnum=None):
        import Adafruit_PCA9685
        self.pwm = Adafruit_PCA9685.PCA9685(address=address)
        self.pwm.set_pwm_freq(frequency)
        self.register = 0 #i2c read doesn't take an address
        self.steering = 0
        self.throttle = 0
        self.running = True
        #send a reset
        self.pwm._device.writeRaw8(0x06)

    def read_pwm(self):
        '''
        send read requests via i2c bus to Teensy to get
        pwm control values from last RC input  
        '''
        h1 = self.pwm._device.readU8(self.register)
        # first byte of header must be 100, otherwize we might be reading
        # in the wrong byte offset
        while h1 != 100:
            print("skipping to start of header")
            h1 = self.pwm._device.readU8(self.register)
        
        h2 = self.pwm._device.readU8(self.register)
        # h2 ignored now

        val_a = self.pwm._device.readU8(self.register)
        val_b = self.pwm._device.readU8(self.register)
        self.steering = (val_b << 8) + val_a
        
        val_c = self.pwm._device.readU8(self.register)
        val_d = self.pwm._device.readU8(self.register)
        self.throttle = (val_d << 8) + val_c

        # scale the values from -1 to 1
        self.steering = (self.steering - 1500.0) / 500.0  + 0.158
        self.throttle = (self.throttle - 1500.0) / 500.0  + 0.136

    def update(self):
        while(self.running):
            self.read_pwm()
        
    def run_threaded(self):
        return self.steering, self.throttle

    def shutdown(self):
        self.running = False
        time.sleep(0.1)


class Adafruit_DCMotor_Hat:
    ''' 
    Adafruit DC Motor Controller 
    Used for each motor on a differential drive car.
    '''
    def __init__(self, motor_num):
        from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor
        import atexit
        
        self.FORWARD = Adafruit_MotorHAT.FORWARD
        self.BACKWARD = Adafruit_MotorHAT.BACKWARD
        self.mh = Adafruit_MotorHAT(addr=0x60) 
        
        self.motor = self.mh.getMotor(motor_num)
        self.motor_num = motor_num
        
        atexit.register(self.turn_off_motors)
        self.speed = 0
        self.throttle = 0
    
        
    def run(self, speed):
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed > 1 or speed < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")
        
        self.speed = speed
        self.throttle = int(dk.utils.map_range(abs(speed), -1, 1, -255, 255))
        
        if speed > 0:            
            self.motor.run(self.FORWARD)
        else:
            self.motor.run(self.BACKWARD)
            
        self.motor.setSpeed(self.throttle)
        

    def shutdown(self):
        self.mh.getMotor(self.motor_num).run(Adafruit_MotorHAT.RELEASE)


class Maestro:
    '''
    Pololu Maestro Servo controller
    Use the MaestroControlCenter to set the speed & acceleration values to 0!
    See https://www.pololu.com/docs/0J40/all
    '''
    import threading

    maestro_device = None
    astar_device = None
    maestro_lock = threading.Lock()
    astar_lock = threading.Lock()

    def __init__(self, channel, frequency = 60):
        import serial

        if Maestro.maestro_device == None:
            Maestro.maestro_device = serial.Serial('/dev/ttyACM0', 115200)

        self.channel = channel
        self.frequency = frequency
        self.lturn = False
        self.rturn = False
        self.headlights = False
        self.brakelights = False

        if Maestro.astar_device == None:
            Maestro.astar_device = serial.Serial('/dev/ttyACM2', 115200, timeout= 0.01)

    def set_pulse(self, pulse):
        # Recalculate pulse width from the Adafruit values
        w = pulse * (1 / (self.frequency * 4096)) # in seconds
        w *= 1000 * 1000  # in microseconds
        w *= 4  # in quarter microsenconds the maestro wants
        w = int(w)

        with Maestro.maestro_lock:
            Maestro.maestro_device.write(bytearray([ 0x84,
                                                     self.channel,
                                                     (w & 0x7F),
                                                     ((w >> 7) & 0x7F)]))

    def set_turn_left(self, v):
        if self.lturn != v:
            self.lturn = v
            b = bytearray('L' if v else 'l', 'ascii')
            with Maestro.astar_lock:
                Maestro.astar_device.write(b)

    def set_turn_right(self, v):
        if self.rturn != v:
            self.rturn = v
            b = bytearray('R' if v else 'r', 'ascii')
            with Maestro.astar_lock:
                Maestro.astar_device.write(b)

    def set_headlight(self, v):
        if self.headlights != v:
            self.headlights = v
            b = bytearray('H' if v else 'h', 'ascii')
            with Maestro.astar_lock:
                Maestro.astar_device.write(b)

    def set_brake(self, v):
        if self.brakelights != v:
            self.brakelights = v
            b = bytearray('B' if v else 'b', 'ascii')
            with Maestro.astar_lock:
                Maestro.astar_device.write(b)

    def readline(self):
        ret = None
        with Maestro.astar_lock:
            # expecting lines like
            # E n nnn n
            if Maestro.astar_device.inWaiting() > 8:
                ret = Maestro.astar_device.readline()

        if ret is not None:
            ret = ret.rstrip()

        return ret


class Teensy:
    '''
    Teensy Servo controller
    '''
    import threading

    teensy_device = None
    astar_device = None
    teensy_lock = threading.Lock()
    astar_lock = threading.Lock()

    def __init__(self, channel, frequency = 60):
        import serial

        if Teensy.teensy_device == None:
            Teensy.teensy_device = serial.Serial('/dev/teensy', 115200, timeout = 0.01)

        self.channel = channel
        self.frequency = frequency
        self.lturn = False
        self.rturn = False
        self.headlights = False
        self.brakelights = False

        if Teensy.astar_device == None:
            Teensy.astar_device = serial.Serial('/dev/astar', 115200, timeout = 0.01)

    def set_pulse(self, pulse):
        # Recalculate pulse width from the Adafruit values
        w = pulse * (1 / (self.frequency * 4096)) # in seconds
        w *= 1000 * 1000  # in microseconds

        with Teensy.teensy_lock:
            Teensy.teensy_device.write(("%c %.1f\n" % (self.channel, w)).encode('ascii'))

    def set_turn_left(self, v):
        if self.lturn != v:
            self.lturn = v
            b = bytearray('L' if v else 'l', 'ascii')
            with Teensy.astar_lock:
                Teensy.astar_device.write(b)

    def set_turn_right(self, v):
        if self.rturn != v:
            self.rturn = v
            b = bytearray('R' if v else 'r', 'ascii')
            with Teensy.astar_lock:
                Teensy.astar_device.write(b)

    def set_headlight(self, v):
        if self.headlights != v:
            self.headlights = v
            b = bytearray('H' if v else 'h', 'ascii')
            with Teensy.astar_lock:
                Teensy.astar_device.write(b)

    def set_brake(self, v):
        if self.brakelights != v:
            self.brakelights = v
            b = bytearray('B' if v else 'b', 'ascii')
            with Teensy.astar_lock:
                Teensy.astar_device.write(b)

    def teensy_readline(self):
        ret = None
        with Teensy.teensy_lock:
            # expecting lines like
            # E n nnn n
            if Teensy.teensy_device.inWaiting() > 8:
                ret = Teensy.teensy_device.readline()

        if ret != None:
            ret = ret.rstrip()

        return ret

    def astar_readline(self):
        ret = None
        with Teensy.astar_lock:
            # expecting lines like
            # E n nnn n
            if Teensy.astar_device.inWaiting() > 8:
                ret = Teensy.astar_device.readline()

        if ret != None:
            ret = ret.rstrip()

        return ret

class MockController(object):
    def __init__(self):
        pass

    def run(self, pulse):
        pass

    def shutdown(self):
        pass


class L298N_HBridge_DC_Motor(object):
    '''
    Motor controlled with an L298N hbridge from the gpio pins on Rpi
    '''
    def __init__(self, pin_forward, pin_backward, pwm_pin, freq = 50):
        import RPi.GPIO as GPIO
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.pwm_pin = pwm_pin

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_forward, GPIO.OUT)
        GPIO.setup(self.pin_backward, GPIO.OUT)
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pwm_pin, freq)
        self.pwm.start(0)

    def run(self, speed):
        import RPi.GPIO as GPIO
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed > 1 or speed < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")
        
        self.speed = speed
        max_duty = 90 #I've read 90 is a good max
        self.throttle = int(dk.utils.map_range(speed, -1, 1, -max_duty, max_duty))
        
        if self.throttle > 0:
            self.pwm.ChangeDutyCycle(self.throttle)
            GPIO.output(self.pin_forward, GPIO.HIGH)
            GPIO.output(self.pin_backward, GPIO.LOW)
        elif self.throttle < 0:
            self.pwm.ChangeDutyCycle(-self.throttle)
            GPIO.output(self.pin_forward, GPIO.LOW)
            GPIO.output(self.pin_backward, GPIO.HIGH)
        else:
            self.pwm.ChangeDutyCycle(self.throttle)
            GPIO.output(self.pin_forward, GPIO.LOW)
            GPIO.output(self.pin_backward, GPIO.LOW)


    def shutdown(self):
        import RPi.GPIO as GPIO
        self.pwm.stop()
        GPIO.cleanup()



class TwoWheelSteeringThrottle(object):

    def run(self, throttle, steering):
        if throttle > 1 or throttle < -1:
            raise ValueError( "throttle must be between 1(forward) and -1(reverse)")
 
        if steering > 1 or steering < -1:
            raise ValueError( "steering must be between 1(right) and -1(left)")

        left_motor_speed = throttle
        right_motor_speed = throttle
 
        if steering < 0:
            left_motor_speed *= (1.0 - (-steering))
        elif steering > 0:
            right_motor_speed *= (1.0 - steering)

        return left_motor_speed, right_motor_speed

    def shutdown(self):
        pass


class Mini_HBridge_DC_Motor_PWM(object):
    '''
    Motor controlled with an mini hbridge from the gpio pins on Rpi
    This can be using the L298N as above, but wired differently with only
    two inputs and no enable line.
    https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Dtoys-and-games&field-keywords=Mini+Dual+DC+Motor+H-Bridge+Driver
    https://www.aliexpress.com/item/5-pc-2-DC-Motor-Drive-Module-Reversing-PWM-Speed-Dual-H-Bridge-Stepper-Motor-Mini
    '''
    def __init__(self, pin_forward, pin_backward, freq = 50, max_duty = 90):
        '''
        max_duy is from 0 to 100. I've read 90 is a good max.
        '''
        import RPi.GPIO as GPIO
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.max_duty = max_duty
        
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_forward, GPIO.OUT)
        GPIO.setup(self.pin_backward, GPIO.OUT)
        
        self.pwm_f = GPIO.PWM(self.pin_forward, freq)
        self.pwm_f.start(0)
        self.pwm_b = GPIO.PWM(self.pin_backward, freq)
        self.pwm_b.start(0)

    def run(self, speed):
        import RPi.GPIO as GPIO
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed is None:
            return
        
        if speed > 1 or speed < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")
        
        self.speed = speed
        self.throttle = int(dk.utils.map_range(speed, -1, 1, -self.max_duty, self.max_duty))
        
        if self.throttle > 0:
            self.pwm_f.ChangeDutyCycle(self.throttle)
            self.pwm_b.ChangeDutyCycle(0)
        elif self.throttle < 0:
            self.pwm_f.ChangeDutyCycle(0)
            self.pwm_b.ChangeDutyCycle(-self.throttle)
        else:
            self.pwm_f.ChangeDutyCycle(0)
            self.pwm_b.ChangeDutyCycle(0)


    def shutdown(self):
        import RPi.GPIO as GPIO
        self.pwm_f.ChangeDutyCycle(0)
        self.pwm_b.ChangeDutyCycle(0)
        self.pwm_f.stop()
        self.pwm_b.stop()
        GPIO.cleanup()

    
class RPi_GPIO_Servo(object):
    '''
    Servo controlled from the gpio pins on Rpi
    '''
    def __init__(self, pin, freq = 50, min=5.0, max=7.8):
        import RPi.GPIO as GPIO
        self.pin = pin
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pin, freq)
        self.pwm.start(0)
        self.min = min
        self.max = max

    def run(self, pulse):
        import RPi.GPIO as GPIO
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        #I've read 90 is a good max
        self.throttle = dk.map_frange(pulse, -1.0, 1.0, self.min, self.max)
        #print(pulse, self.throttle)
        self.pwm.ChangeDutyCycle(self.throttle)


    def shutdown(self):
        import RPi.GPIO as GPIO
        self.pwm.stop()
        GPIO.cleanup()


class ServoBlaster(object):
    '''
    Servo controlled from the gpio pins on Rpi
    This uses a user space service to generate more efficient PWM via DMA control blocks.
    Check readme and install here:
    https://github.com/richardghirst/PiBits/tree/master/ServoBlaster
    cd PiBits/ServoBlaster/user
    make
    sudo ./servod
    will start the daemon and create the needed device file:
    /dev/servoblaster

    to test this from the command line:
    echo P1-16=120 > /dev/servoblaster

    will send 1200us PWM pulse to physical pin 16 on the pi.

    If you want it to start on boot:
    sudo make install
    '''
    def __init__(self, pin):
        self.pin = pin
        self.servoblaster = open('/dev/servoblaster', 'w')
        self.min = min
        self.max = max

    def set_pulse(self, pulse):
        s = 'P1-%d=%d\n' % (self.pin, pulse)
        self.servoblaster.write(s)
        self.servoblaster.flush()

    def run(self, pulse):
        self.set_pulse(pulse)

    def shutdown(self):
        self.run((self.max + self.min) / 2)
        self.servoblaster.close()


class ArduinoFirmata:
    '''
    PWM controller using Arduino board.
    This is particularly useful for boards like Latte Panda with built it Arduino.
    Standard Firmata sketch needs to be loaded on Arduino side.
    Refer to docs/parts/actuators.md for more details
    '''

    def __init__(self, servo_pin = 6, esc_pin = 5):
        from pymata_aio.pymata3 import PyMata3
        self.board = PyMata3()
        self.board.sleep(0.015)
        self.servo_pin = servo_pin
        self.esc_pin = esc_pin
        self.board.servo_config(servo_pin)
        self.board.servo_config(esc_pin)

    def set_pulse(self, pin, angle):
        try:
            self.board.analog_write(pin, int(angle))
        except:
            self.board.analog_write(pin, int(angle))

    def set_servo_pulse(self, angle):
        self.set_pulse(self.servo_pin, int(angle))

    def set_esc_pulse(self, angle):
        self.set_pulse(self.esc_pin, int(angle))



class ArdPWMSteering:
    """
    Wrapper over a Arduino Firmata controller to convert angles to PWM pulses.
    """
    LEFT_ANGLE = -1
    RIGHT_ANGLE = 1

    def __init__(self,
                 controller=None,
                 left_pulse=60,
                 right_pulse=120):

        self.controller = controller
        self.left_pulse = left_pulse
        self.right_pulse = right_pulse
        self.pulse = dk.utils.map_range(0, self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                        self.left_pulse, self.right_pulse)
        self.running = True
        print('Arduino PWM Steering created')

    def run(self, angle):
        # map absolute angle to angle that vehicle can implement.
        self.pulse = dk.utils.map_range(angle,
                                        self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                        self.left_pulse, self.right_pulse)
        self.controller.set_servo_pulse(self.pulse)

    def shutdown(self):
        # set steering straight
        self.pulse = dk.utils.map_range(0, self.LEFT_ANGLE, self.RIGHT_ANGLE,
                                        self.left_pulse, self.right_pulse)
        time.sleep(0.3)
        self.running = False


class ArdPWMThrottle:

    """
    Wrapper over Arduino Firmata controller to convert -1 to 1 throttle
    values to PWM pulses.
    """
    MIN_THROTTLE = -1
    MAX_THROTTLE = 1

    def __init__(self,
                 controller=None,
                 max_pulse=105,
                 min_pulse=75,
                 zero_pulse=90):

        self.controller = controller
        self.max_pulse = max_pulse
        self.min_pulse = min_pulse
        self.zero_pulse = zero_pulse
        self.pulse = zero_pulse

        # send zero pulse to calibrate ESC
        print("Init ESC")
        self.controller.set_esc_pulse(self.max_pulse)
        time.sleep(0.01)
        self.controller.set_esc_pulse(self.min_pulse)
        time.sleep(0.01)
        self.controller.set_esc_pulse(self.zero_pulse)
        time.sleep(1)
        self.running = True
        print('Arduino PWM Throttle created')

    def run(self, throttle):
        if throttle > 0:
            self.pulse = dk.utils.map_range(throttle, 0, self.MAX_THROTTLE,
                                            self.zero_pulse, self.max_pulse)
        else:
            self.pulse = dk.utils.map_range(throttle, self.MIN_THROTTLE, 0,
                                            self.min_pulse, self.zero_pulse)
        self.controller.set_esc_pulse(self.pulse)

    def shutdown(self):
        # stop vehicle
        self.run(0)
        self.running = False
