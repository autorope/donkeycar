"""
pins.py - high level ttl an pwm pin abstraction.
This is designed to allow drivers that use ttl and pwm
pins to be reusable with different underlying libaries
and techologies.

The abstract classes InputPin, OutputPin and PwmPin
provide an interface for starting, using and cleaning up the pins.
The factory functions input_pin_by_id(), output_pin_by_id()
and pwm_pin_by_id() construct pins given a string id
that specifies the underlying pin provider and it's attributes.
There are implementations for the Rpi.GPIO library and
for the PCA9685.

Pin id allows pins to be selected using a single string to
select from different underlying providers, numbering schemes and settings.

Use Rpi.GPIO library, GPIO.BOARD pin numbering scheme, pin number 13
 pin = input_pin_by_id("RPI_GPIO.BOARD.13")

Use Rpi.GPIO library, GPIO.BCM broadcom pin numbering scheme, gpio pin number 33
 pin = output_pin_by_id("RPI_GPIO.BCM.33")

Use PCA9685 on bus 0 at address 0x40, channel 7
 pin = pwm_pin_by_id("PCA9685.0:40.7")

"""
from abc import ABC, abstractmethod
from typing import Any, Callable
import logging


logger = logging.getLogger(__name__)


class PinState:
    LOW: int = 0
    HIGH: int = 1
    NOT_STARTED: int = -1


class PinEdge:
    RISING: int = 1
    FALLING: int = 2
    BOTH: int = 3


class PinPull:
    PULL_NONE: int = 1
    PULL_UP: int = 2
    PULL_DOWN: int = 3


class PinProvider:
    RPI_GPIO = "RPI_GPIO"
    PCA9685 = "PCA9685"
    PIGPIO = "PIGPIO"


class PinScheme:
    BOARD = "BOARD"  # board numbering
    BCM = "BCM"      # broadcom gpio numbering


#
# #### Base interface for input/output/pwm pins
# #### Implementations derive from these abstact classes
#

class InputPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, on_input=None, edge: int = PinEdge.RISING) -> None:
        """
        Start the pin in input mode.
        :param on_input: no-arg function to call when an edge is detected, or None to ignore
        :param edge: type of edge(s) that trigger on_input; default is PinEdge.RISING
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
        :return: PinState.LOW/HIGH or PinState.NOT_STARTED if pin not started
        """
        return PinState.NOT_STARTED  # subclasses must override


class OutputPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, state: int = PinState.LOW) -> None:
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
        :return: most recent output state OR PinState.NOT_STARTED if pin not started.
        """
        return PinState.NOT_STARTED  # subclasses must override

    @abstractmethod
    def output(self, state: int) -> None:
        """
        Set the output state of the pin to either
        :param state: PinState.LOW or PinState.HIGH
        :except: RuntimeError if pin not stated.
        """
        pass  # subclasses must override


class PwmPin(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def start(self, duty: float = 0) -> None:
        """
        Start the pin in output mode and with given starting state.
        This raises and RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        :param duty: duty cycle in range 0 to 1
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
        :return: most recent output duty_cycle
        """
        return PinState.NOT_STARTED  # subclasses must override

    @abstractmethod
    def duty_cycle(self, duty: float) -> None:
        """
        Set the output duty cycle of the pin
        in range 0 to 1.0 (0% to 100%)
        :param duty: duty cycle in range 0 to 1
        :except: RuntimeError is pin is not started
        """
        pass  # subclasses must override


#
# ####### Factory Methods
#


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
def output_pin_by_id(pin_id: str, frequency_hz: int = 60) -> OutputPin:
    """
    Select a ttl output pin given a pin id.
    :param pin_id: pin specifier string
    :param frequency_hz: duty cycle frequency in hertz (only necessary for PCA9685)
    :return: OutputPin
    """
    parts = pin_id.split(".")
    if parts[0] == PinProvider.PCA9685:
        pin_provider = parts[0]
        i2c_bus, i2c_address = parts[1].split(":")
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

    if parts[0] == PinProvider.PIGPIO:
        pin_provider = parts[0]
        if PinScheme.BCM != parts[1]:
            raise ValueError("Pin scheme must be BCM for PIGPIO")
        pin_number = int(parts[2])
        return output_pin(pin_provider, pin_number, pin_scheme=PinScheme.BCM)

    raise ValueError(f"Unknown pin provider {parts[0]}")


def pwm_pin_by_id(pin_id: str, frequency_hz: int = 60) -> PwmPin:
    """
    Select a pwm output pin given a pin id.
    :param pin_id: pin specifier string
    :param frequency_hz: duty cycle frequency in hertz
    :return: PwmPin
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

    if parts[0] == PinProvider.PIGPIO:
        pin_provider = parts[0]
        if PinScheme.BCM != parts[1]:
            raise ValueError("Pin scheme must be BCM for PIGPIO")
        pin_number = int(parts[2])
        return pwm_pin(pin_provider, pin_number, pin_scheme=PinScheme.BCM, frequency_hz=frequency_hz)

    raise ValueError(f"Unknown pin provider {parts[0]}")


def input_pin_by_id(pin_id: str, pull: int = PinPull.PULL_NONE) -> InputPin:
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

    if parts[0] == PinProvider.PIGPIO:
        pin_provider = parts[0]
        if PinScheme.BCM != parts[1]:
            raise ValueError("Pin scheme must be BCM for PIGPIO")
        pin_number = int(parts[2])
        return input_pin(pin_provider, pin_number, pin_scheme=PinScheme.BCM, pull=pull)

    raise ValueError(f"Unknown pin provider {parts[0]}")


def input_pin(
        pin_provider: str,
        pin_number: int,
        pin_scheme: str = PinScheme.BOARD,
        pull: int = PinPull.PULL_NONE) -> InputPin:
    """
    construct an InputPin using the given pin provider.
    Note that PCA9685 can NOT provide an InputPin.
    :param pin_provider: PinProvider string
    :param pin_number: zero based pin number
    :param pin_scheme: PinScheme string
    :param pull: PinPull value
    :return: InputPin
    :except: RuntimeError if pin_provider is not valid.
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return InputPinGpio(pin_number, pin_scheme, pull)
    if pin_provider == PinProvider.PCA9685:
        raise RuntimeError("PinProvider.PCA9685 does not implement InputPin")
    if pin_provider == PinProvider.PIGPIO:
        if pin_scheme != PinScheme.BCM:
            raise ValueError("Pin scheme must be PinScheme.BCM for PIGPIO")
        return InputPinPigpio(pin_number, pull)
    raise RuntimeError(f"UnknownPinProvider ({pin_provider})")


def output_pin(
        pin_provider: str,
        pin_number: int,
        pin_scheme: str = PinScheme.BOARD,
        i2c_bus: int = 0,
        i2c_address: int = 40,
        frequency_hz: int = 60) -> OutputPin:
    """
    construct an OutputPin using the given pin provider
    Note that PCA9685 can NOT provide an InputPin.
    :param pin_provider: PinProvider string
    :param pin_number: zero based pin number
    :param pin_scheme: PinScheme string
    :param i2c_bus: I2C bus number for I2C devices
    :param i2c_address: I2C address for I2C devices
    :param frequency_hz: duty cycle frequence in hertz (for PCA9685)
    :return: InputPin
    :except: RuntimeError if pin_provider is not valid.
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return OutputPinGpio(pin_number, pin_scheme)
    if pin_provider == PinProvider.PCA9685:
        return OutputPinPCA9685(pin_number, pca9685(i2c_bus, i2c_address, frequency_hz))
    if pin_provider == PinProvider.PIGPIO:
        if pin_scheme != PinScheme.BCM:
            raise ValueError("Pin scheme must be PinScheme.BCM for PIGPIO")
        return OutputPinPigpio(pin_number)
    raise RuntimeError(f"UnknownPinProvider ({pin_provider})")


def pwm_pin(
        pin_provider: str,
        pin_number: int,
        pin_scheme: str = PinScheme.BOARD,
        frequency_hz: int = 60,
        i2c_bus: int = 0,
        i2c_address: int = 40) -> PwmPin:
    """
    construct a PwmPin using the given pin provider
    :param pin_provider: PinProvider string
    :param pin_number: zero based pin number
    :param pin_scheme: PinScheme string
    :param i2c_bus: I2C bus number for I2C devices
    :param i2c_address: I2C address for I2C devices
    :param frequency_hz: duty cycle frequence in hertz
    :return: PwmPin
    :except: RuntimeError if pin_provider is not valid.
    """
    if pin_provider == PinProvider.RPI_GPIO:
        return PwmPinGpio(pin_number, pin_scheme, frequency_hz)
    if pin_provider == PinProvider.PCA9685:
        return PwmPinPCA9685(pin_number, i2c_bus, i2c_address, frequency_hz)
    if pin_provider == PinProvider.PIGPIO:
        if pin_scheme != PinScheme.BCM:
            raise ValueError("Pin scheme must be PinScheme.BCM for PIGPIO")
        return PwmPinPigpio(pin_number, frequency_hz)
    raise RuntimeError(f"UnknownPinProvider ({pin_provider})")


#
# ----- RPi.GPIO/Jetson.GPIO implementations -----
#
try:
    import RPi.GPIO as GPIO
    # lookups to convert abstact api to GPIO values
    gpio_pin_edge = [None, GPIO.RISING, GPIO.FALLING, GPIO.BOTH]
    gpio_pin_pull = [None, GPIO.PUD_OFF, GPIO.PUD_DOWN, GPIO.PUD_UP]
    gpio_pin_scheme = {PinScheme.BOARD: GPIO.BOARD, PinScheme.BCM: GPIO.BCM}
except ImportError:
    logger.warning("RPi.GPIO was not imported.")
    globals()["GPIO"] = None


def gpio_fn(pin_scheme:int, fn:Callable[[], Any]):
    """
    Convenience method to enforce the desired GPIO pin scheme
    before calling a GPIO function.
    RPi.GPIO allows only a single scheme to be set at runtime.
    If the pin scheme is already set to a different scheme, then
    this will raise a RuntimeError to prevent erroneous pin outputs.

    :param pin_scheme:int GPIO.BOARD or GPIO.BCM
    :param fn:Callable[[], Any] no-arg function to call after setting pin scheme.
    :return:any return value from called function
    :exception:RuntimeError if pin scheme is already set to a different scheme.
    """
    prev_scheme = GPIO.getmode()
    if prev_scheme is None:
        GPIO.setmode(pin_scheme)
    elif prev_scheme != pin_scheme:
        raise RuntimeError(f"Attempt to change GPIO pin scheme from ({prev_scheme}) to ({pin_scheme})"
                           " after it has been set.  All RPi.GPIO pins must use the same pin scheme.")
    val = fn()
    return val


class InputPinGpio(InputPin):
    def __init__(self, pin_number: int, pin_scheme: str, pull: int = PinPull.PULL_NONE) -> None:
        """
        Input pin ttl HIGH/LOW using RPi.GPIO/Jetson.GPIO
        :param pin_number: GPIO.BOARD mode point number
        :param pull: enable a pull up or down resistor on pin.  Default is PinPull.PULL_NONE
        """
        self.pin_number = pin_number
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self.pin_scheme_str = pin_scheme
        self.pull = pull
        self.on_input = None
        self._state = PinState.NOT_STARTED
        super().__init__()

    def _callback(self, pin_number):
        if self.on_input is not None:
            self.on_input()

    def start(self, on_input=None, edge=PinEdge.RISING) -> None:
        """
        :param on_input: no-arg function to call when an edge is detected, or None to ignore
        :param edge: type of edge(s) that trigger on_input; default is
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start InputPinGpio({self.pin_number}) that is already started.")

        # stop the pin so it is not in use, then start it
        gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.IN, pull_up_down=gpio_pin_pull[self.pull]))
        if on_input is not None:
            self.on_input = on_input
            gpio_fn(
                self.pin_scheme,
                lambda: GPIO.add_event_detect(self.pin_number, gpio_pin_edge[edge], callback=self._callback))
        self.input()  # read first state
        logger.info(f"InputPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' started.")

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            self.on_input = None
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
            self._state = PinState.NOT_STARTED
            logger.info(f"InputPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' stopped.")

    def state(self) -> int:
        return self._state

    def input(self) -> int:
        self._state = gpio_fn(self.pin_scheme, lambda: GPIO.input(self.pin_number))
        return self._state


class OutputPinGpio(OutputPin):
    """
    Output pin ttl HIGH/LOW using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number: int, pin_scheme: str) -> None:
        self.pin_number = pin_number
        self.pin_scheme_str = pin_scheme
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self._state = PinState.NOT_STARTED

    def start(self, state: int = PinState.LOW) -> None:
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start OutputPinGpio({self.pin_number}) that is already started.")
        # first stop the pin so we know it is not in use, then start it.
        gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.OUT))
        self.output(state)
        logger.info(f"OutputPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' started.")

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
            self._state = PinState.NOT_STARTED
            logger.info(f"OutputPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' stopped.")

    def state(self) -> int:
        return self._state

    def output(self, state: int) -> None:
        gpio_fn(self.pin_scheme, lambda: GPIO.output(self.pin_number, state))
        self._state = state


class PwmPinGpio(PwmPin):
    """
    PWM output pin using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number: int, pin_scheme: str, frequency_hz: float = 50) -> None:
        self.pin_number = pin_number
        self.pin_scheme_str = pin_scheme
        self.pin_scheme = gpio_pin_scheme[pin_scheme]
        self.frequency = int(frequency_hz)
        self.pwm = None
        self._state = PinState.NOT_STARTED

    def start(self, duty: float = 0) -> None:
        if self.pwm is not None:
            raise RuntimeError("Attempt to start PwmPinGpio that is already started.")
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")

        # stop the pin so we know it is not in use, then start it
        gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
        gpio_fn(self.pin_scheme, lambda: GPIO.setup(self.pin_number, GPIO.OUT))
        self.pwm = gpio_fn(self.pin_scheme, lambda: GPIO.PWM(self.pin_number, self.frequency))
        self.pwm.start(duty * 100)  # takes duty in range 0 to 100
        self._state = duty
        logger.info(f"PwmPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' started.")

    def stop(self) -> None:
        if self.pwm is not None:
            self.pwm.stop()
            gpio_fn(self.pin_scheme, lambda: GPIO.cleanup(self.pin_number))
            logger.info(f"PwmPin 'RPI_GPIO.{self.pin_scheme_str}.{self.pin_number}' stopped.")
        self._state = PinState.NOT_STARTED


    def state(self) -> float:
        return self._state

    def duty_cycle(self, duty: float) -> None:
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pwm.ChangeDutyCycle(duty * 100)  # takes duty of 0 to 100
        self._state = duty


#
# ----- PCA9685 implementations -----
#
class PCA9685board:
    '''
    Adapter over PCA9685 driver.
    It initializes the PCA9685 board at the given busnum:address
    to produce pulses at the given frequency in hertz.
    >> NOTE: The busnum argument is now ignored.
    >>       The I2C bus device is auto detected using
    >>       Adafruit Blinka board interface, which is 
    >>       implemented for RaspberryPi, but may not be 
    >>       implemented for other SBCs.  
    >>       See [boards.py](https://github.com/adafruit/Adafruit_Blinka/blob/main/src/board.py)
    >>       and [busio.py](https://github.com/adafruit/Adafruit_Blinka/blob/b3beba7399bc4d5faa203ef705691ef79fc4e87f/src/busio.py#L29)
    '''
    def __init__(self, busnum: int = 1, address: int = 0x40, frequency: int = 60):
        import board
        import busio
        import adafruit_pca9685
        i2c = busio.I2C(board.SCL, board.SDA)
        self.pca9685driver = adafruit_pca9685.PCA9685(i2c, address=address)
        self.pca9685driver.frequency = frequency
        self.busnum = busnum
        self.address = address
        self._frequency = frequency

    def get_frequency(self) -> int:
        return self._frequency

class PCA9685Pin:
    '''
    Adapter over PCA9685 pin driver.
    This can output ttl HIGH or LOW or
    produce a duty cycle at the given frequency.
    '''
    def __init__(self, channel: int, busnum: int = 1, address: int = 0x40, frequency: int = 60):

        import adafruit_pca9685
        self.pca = pca9685(busnum, address, frequency)
        self.pca_pin = adafruit_pca9685.PWMChannel(self.pca.pca9685driver, channel)
        self.channel = channel

    def get_frequency(self) -> int:
        return self.pca.get_frequency()

    def set_high(self):
        # adafruit blinka uses 16bit values
        # where 0xFFFF is a flag that means fully high
        self.pca_pin.duty_cycle = 0xFFFF

    def set_low(self):
        # adafruit blinka uses 16bit values
        # where 0x0000 is a flag that means fully low
        self.pca_pin.duty_cycle = 0x0000

    def set_duty_cycle(self, duty_cycle: float):
        if duty_cycle < 0 or duty_cycle > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        if duty_cycle == 1:
            self.set_high()
        elif duty_cycle == 0:
            self.set_low()
        else:
            # adafruit blinka uses 16 bit values
            # for resolution of duty cycle.
            pulse = int(0x10000 * duty_cycle)
            try:
                self.pca_pin.duty_cycle = pulse
            except Exception as e:
                logger.error(f'Error on PCA9685 channel {self.channel}: {str(e)}')


#
# lookup map for PCA9685 singletons
# key is "busnum:address"
#
_pca9685 = {}
_pca9685pin = {}


def pca9685(busnum: int, address: int, frequency: int = 60) -> PCA9685board:
    """
    pca9685 factory allocates driver for pca9685
    at given bus number and i2c address.
    If we have already created one for that bus/addr
    pair then use that singleton.  If frequency is
    not the same, then error.
    :param busnum: I2C bus number of PCA9685
    :param address: address of PCA9685 on I2C bus
    :param frequency: frequency in hertz of duty cycle
    :except: PCA9685 has a single frequency for all channels,
             so attempts to allocate a controller at a
             given bus number and address with different
             frequencies will raise a ValueError
    """
    key = str(busnum) + ":" + hex(address)
    pca = _pca9685.get(key)
    if pca is None:
        pca = PCA9685board(busnum, address, frequency)
        _pca9685[key] = pca
    if pca.get_frequency() != frequency:
        raise ValueError(
            f"Frequency {frequency} conflicts with pca9685 at {key} "
            f"with frequency {pca.get_frequency()}")
    return pca


def pca9685pin(channel: int, busnum: int, address: int, frequency: int = 60) -> PCA9685Pin:
    """
    pca9685 pin factory allocates driver for pin on channel on pca9685
    at given bus number and i2c address.
    If we have already created one for that bus/addr/channel
    pair then use that singleton.  If frequency is
    not the same, then error.
    :param channel: PCA9685 channel 0..15 to control
    :param busnum: I2C bus number of PCA9685
    :param address: address of PCA9685 on I2C bus
    :param frequency: frequency in hertz of duty cycle
    :except: PCA9685 has a single frequency for all channels,
             so attempts to allocate a controller at a
             given bus number and address with different
             frequencies will raise a ValueError
    """
    key = str(busnum) + ":" + hex(address) + ":" + str(channel)
    pca_pin = _pca9685pin.get(key)
    if pca_pin is None:
        pca_pin = PCA9685Pin(channel, busnum, address, frequency)
        _pca9685pin[key] = pca_pin
    return pca_pin


class OutputPinPCA9685(OutputPin):
    """
    Output pin ttl HIGH/LOW using PCA9685
    """
    def __init__(self, pin_number: int, busnum: int, address: int, frequency: int = 60) -> None:
        self.pin_number = pin_number
        self.pca_pin = pca9685pin(pin_number, busnum, address, frequency)
        self._state = PinState.NOT_STARTED

    def start(self, state: int = PinState.LOW) -> None:
        """
        Start the pin in output mode.
        This raises a RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        :param state: PinState to start with
        :except: RuntimeError if pin is already started.
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start pin ({self.pin_number}) that is already started")
        self._state = 0  # hack to allow first output to work
        self.output(state)

    def stop(self) -> None:
        """
        Stop the pin and return it to PinState.NOT_STARTED
        """
        if self.state() != PinState.NOT_STARTED:
            self.output(PinState.LOW)
            self._state = PinState.NOT_STARTED

    def state(self) -> int:
        """
        Return most recent output state.
        If the pin is not started or has been stopped,
        this will return PinState:NOT_STARTED
        :return: PinState
        """
        return self._state

    def output(self, state: int) -> None:
        """
        Write output state to the pin.
        :param state: PinState.LOW or PinState.HIGH
        """
        if self.state() == PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to use pin ({self.pin_number}) that is not started")
        if state == PinState.HIGH:
            self.pca_pin.set_high()
        else:
            self.pca_pin.set_low()
        self._state = state


class PwmPinPCA9685(PwmPin):
    """
    PWM output pin using PCA9685
    """
    def __init__(self, pin_number: int, busnum: int, address: int, frequency: int = 60) -> None:
        self.pin_number = pin_number
        self.pca_pin = pca9685pin(pin_number, busnum, address, frequency)
        self._state = PinState.NOT_STARTED

    def start(self, duty: float = 0) -> None:
        """
        Start pin with given duty cycle
        :param duty: duty cycle in range 0 to 1
        :except: RuntimeError if pin is already started.
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start pin ({self.pin_number}) that is already started")
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self._state = 0  # hack to allow first duty_cycle to work
        self.duty_cycle(duty)
        self._state = duty

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            self.duty_cycle(0)
            self._state = PinState.NOT_STARTED

    def state(self) -> float:
        """
        This returns the last set duty cycle.
        :return: duty cycle in range 0 to 1 OR PinState.NOT_STARTED in not started
        """
        return self._state

    def duty_cycle(self, duty: float) -> None:
        """
        Write a duty cycle to the output pin
        :param duty: duty cycle in range 0 to 1
        :except: RuntimeError if not started
        """
        if self.state() == PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to use pin ({self.pin_number}) that is not started")
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pca_pin.set_duty_cycle(duty)
        self._state = duty


#
# ----- PIGPIO implementation -----
#

# pigpio is an optional install
try:
    import pigpio
    pigpio_pin_edge = [None, pigpio.RISING_EDGE, pigpio.FALLING_EDGE, pigpio.EITHER_EDGE]
    pigpio_pin_pull = [None, pigpio.PUD_OFF, pigpio.PUD_DOWN, pigpio.PUD_UP]
except ImportError:
    logger.warning("pigpio was not imported.")
    globals()["pigpio"] = None


class InputPinPigpio(InputPin):
    def __init__(self, pin_number: int, pull: int = PinPull.PULL_NONE, pgpio=None) -> None:
        """
        Input pin ttl HIGH/LOW using PiGPIO library
        :param pin_number: GPIO.BOARD mode pin number
        :param pull: enable a pull up or down resistor on pin.  Default is PinPull.PULL_NONE
        :param pgpio: instance of pgpio to use or None to allocate a new one
        """
        self.pgpio = pgpio
        self.pin_number = pin_number
        self.pull = pigpio_pin_pull[pull]
        self.on_input = None
        self._state = PinState.NOT_STARTED

    def __del__(self):
        self.stop()

    def _callback(self, gpio, level, tock):
        if self.on_input is not None:
            self.on_input()

    def start(self, on_input=None, edge=PinEdge.RISING) -> None:
        """
        Start the input pin and optionally set callback.
        :param on_input: no-arg function to call when an edge is detected, or None to ignore
        :param edge: type of edge(s) that trigger on_input; default is PinEdge.RISING
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start InputPinPigpio({self.pin_number}) that is already started.")

        self.pgpio = self.pgpio or pigpio.pi()
        self.pgpio.set_mode(self.pin_number, pigpio.INPUT)
        self.pgpio.set_pull_up_down(self.pin_number, self.pull)

        if on_input is not None:
            self.on_input = on_input
            self.pgpio.callback(self.pin_number, pigpio_pin_edge[edge], self._callback)
        self._state = self.pgpio.read(self.pin_number)  # read initial state

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            self.pgpio.stop()
            self.pgpio = None
            self.on_input = None
            self._state = PinState.NOT_STARTED

    def state(self) -> int:
        """
        Return last input() value.  This does NOT read the input again;
        it returns that last value that input() returned.
        :return: PinState.LOW/HIGH OR PinState.NOT_STARTED if not started
        """
        return self._state

    def input(self) -> int:
        """
        Read the input pins state.
        :return: PinState.LOW/HIGH OR PinState.NOT_STARTED if not started
        """
        if self.state() != PinState.NOT_STARTED:
            self._state = self.pgpio.read(self.pin_number)
        return self._state


class OutputPinPigpio(OutputPin):
    """
    Output pin ttl HIGH/LOW using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number: int, pgpio=None) -> None:
        self.pgpio = pgpio
        self.pin_number = pin_number
        self._state = PinState.NOT_STARTED

    def start(self, state: int = PinState.LOW) -> None:
        """
        Start the pin in output mode.
        This raises a RuntimeError if the pin is already started.
        You can check to see if the pin is started by calling
        state() and checking for PinState.NOT_STARTED
        :param state: PinState to start with
        :except: RuntimeError if pin is already started.
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError("Attempt to start OutputPin that is already started.")

        self.pgpio = self.pgpio or pigpio.pi()
        self.pgpio.set_mode(self.pin_number, pigpio.OUTPUT)
        self.pgpio.write(self.pin_number, state)  # set initial state
        self._state = state

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            self.pgpio.write(self.pin_number, PinState.LOW)
            self.pgpio.stop()
            self.pgpio = None
            self._state = PinState.NOT_STARTED

    def state(self) -> int:
        """
        Return last output state
        :return: PinState.LOW/HIGH or PinState.NOT_STARTED if pin not started.
        """
        return self._state

    def output(self, state: int) -> None:
        """
        Write output state to the pin.
        :param state: PinState.LOW or PinState.HIGH
        """
        if self.state() != PinState.NOT_STARTED:
            self.pgpio.write(self.pin_number, state)
            self._state = state


class PwmPinPigpio(PwmPin):
    """
    PWM output pin using Rpi.GPIO/Jetson.GPIO
    """
    def __init__(self, pin_number: int, frequency_hz: float = 50, pgpio=None) -> None:
        self.pgpio = pgpio
        self.pin_number: int = pin_number
        self.frequency: int = int(frequency_hz)
        self._state: int = PinState.NOT_STARTED

    def start(self, duty: float = 0) -> None:
        """
        Start pin with given duty cycle.
        :param duty: duty cycle in range 0 to 1
        :except: RuntimeError if pin is already started.
        """
        if self.state() != PinState.NOT_STARTED:
            raise RuntimeError(f"Attempt to start InputPinPigpio({self.pin_number}) that is already started.")
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        self.pgpio = self.pgpio or pigpio.pi()
        self.pgpio.set_mode(self.pin_number, pigpio.OUTPUT)
        self.pgpio.set_PWM_frequency(self.pin_number, self.frequency)
        self.pgpio.set_PWM_range(self.pin_number, 4095)  # 12 bits, same as PCA9685
        self.pgpio.set_PWM_dutycycle(self.pin_number, int(duty * 4095))  # set initial state
        self._state = duty

    def stop(self) -> None:
        if self.state() != PinState.NOT_STARTED:
            self.pgpio.write(self.pin_number, PinState.LOW)
            self.pgpio.stop()
            self.pgpio = None
        self._state = PinState.NOT_STARTED

    def state(self) -> float:
        """
        This returns the last set duty cycle.
        :return: duty cycle in range 0 to 1 OR PinState.NOT_STARTED in not started
        """
        return self._state

    def duty_cycle(self, duty: float) -> None:
        """
        Write a duty cycle to the output pin
        :param duty: duty cycle in range 0 to 1
        :except: RuntimeError if not started
        """
        if duty < 0 or duty > 1:
            raise ValueError("duty_cycle must be in range 0 to 1")
        if self.state() != PinState.NOT_STARTED:
            self.pgpio.set_PWM_dutycycle(self.pin_number, int(duty * 4095))
            self._state = duty


if __name__ == '__main__':
    import argparse
    import sys
    import time

    #
    # output 50% duty cycle on Rpi board pin 33 (equivalent to BCM.13) for 10 seconds
    # python pins.py --pwm-pin=RPI_GPIO.BOARD.33 --duty=0.5 --time=10
    #
    # input on Rpi board pin 35 (equivalend to BCM.19) for 10 seconds
    # python pins.py --in-pin=RPI_GPIO.BOARD.35 --time=10
    #
    # output 50% duty cycle on Rpi board pin 33, input on Rpi board pin 35 using interrupt handler
    # python pins.py --pwm-pin=RPI_GPIO.BOARD.33 --duty=0.5 --in-pin=RPI_GPIO.BOARD.35 -int=rising --time=10
    #
    # output on Rpi board pin 33, input on Rpi board pin 35 using interrupt handler
    # python pins.py --out-pin=RPI_GPIO.BOARD.33 --duty=0.5 --in-pin=RPI_GPIO.BOARD.35 -int=rising --time=10
    #
    #
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pwm-pin", type=str, default=None,
                        help="pwm pin id, like 'PCA9685:1:60.13' or 'RPI_GPIO.BCM.13")
    parser.add_argument("-hz", "--hertz", type=int, default=60,
                        help="PWM signal frequence in hertz.  Default is 60hz")
    parser.add_argument("-d", "--duty", type=float, default=0.5,
                        help="duty cycle in range 0 to 1.  Default is 0.5")

    parser.add_argument("-o", "--out-pin", type=str, default=None,
                        help="ttl output pin id, like 'PCA9685:1:60.13' or 'RPI_GPIO.BOARD.35' or 'RPI_GPIO.BCM.13'")

    parser.add_argument("-i", "--in-pin", type=str, default=None,
                        help="ttl input pin id, like 'RPI_GPIO.BOARD.35' or 'RPI_GPIO.BCM.19'")
    parser.add_argument("-pu", "--pull", type=str, choices=['up', 'down', 'none'], default='none',
                        help="input pin pullup, one of 'up', 'down', 'none'")
    parser.add_argument("-int", "--interrupt", type=str, choices=['falling', 'rising', 'both', 'none'], default='none',
                        help="use interrupt routine on in-pin with given edge; 'falling', 'rising' or 'both'")
    parser.add_argument("-tm", "--time", type=float, default=1, help="duration test in seconds")
    parser.add_argument("-db", "--debug", action='store_true', help="show debug output")
    parser.add_argument("-th", "--threaded", action='store_true', help="run in threaded mode")

    # Read arguments from command line
    args = parser.parse_args()

    help = []
    if args.hertz < 1:
        help.append("-hz/--hertz: must be >= 1.")

    if args.duty < 0 or args.duty > 1:
        help.append("-d/--duty: must be in range 0 to 1")

    if args.pwm_pin is None and args.out_pin is None and args.in_pin is None:
        help.append("must have one of -o/--out-pin or -p/--pwm-pin or -i/--in-pin")

    if args.pwm_pin is not None and args.out_pin is not None:
        help.append("must have only one of -o/--out-pin or -p/--pwn-pin")

    if args.time < 1:
        help.append("-tm/--time: must be > 0.")

    if len(help) > 0:
        parser.print_help()
        for h in help:
            print("  " + h)
        sys.exit(1)

    pin_pull = {
        'up': PinPull.PULL_UP,
        'down': PinPull.PULL_DOWN,
        'none': PinPull.PULL_NONE
    }
    pin_edge = {
        'none': None,
        'falling': PinEdge.FALLING,
        'rising': PinEdge.RISING,
        'both': PinEdge.BOTH
    }

    def on_input():
        state = ttl_in_pin.input()
        if state == PinState.HIGH:
            print("+", ttl_in_pin.pin_number, time.time()*1000)
        elif state == PinState.LOW:
            print("-", ttl_in_pin.pin_number, time.time()*1000)

    pwm_out_pin: PwmPin = None
    ttl_out_pin: OutputPin = None
    ttl_in_pin: InputPin = None
    try:
        #
        # construct a pin of the correct type
        #
        if args.in_pin is not None:
            ttl_in_pin = input_pin_by_id(args.in_pin, pin_pull[args.pull])
            if args.interrupt != 'none':
                ttl_in_pin.start(on_input=on_input, edge=pin_edge[args.interrupt])
            else:
                ttl_in_pin.start()

        if args.pwm_pin is not None:
            pwm_out_pin = pwm_pin_by_id(args.pwm_pin, args.hertz)
            pwm_out_pin.start(args.duty)

        if args.out_pin is not None:
            ttl_out_pin = output_pin_by_id(args.out_pin, args.hertz)
            ttl_out_pin.start(PinState.LOW)

        start_time = time.time()
        end_time = start_time + args.time
        while start_time < end_time:
            if ttl_out_pin is not None:
                if args.duty > 0:
                    ttl_out_pin.output(PinState.HIGH)
                    time.sleep(1 / args.hertz * args.duty)
                if args.duty < 1:
                    ttl_out_pin.output(PinState.LOW)
                    time.sleep(1 / args.hertz * (1 - args.duty))
            else:
                # yield time to background threads
                sleep_time = 1/args.hertz - (time.time() - start_time)
                if sleep_time > 0.0:
                    time.sleep(sleep_time)
                else:
                    time.sleep(0)  # yield time to other threads
            start_time = time.time()

    except KeyboardInterrupt:
        print('Stopping early.')
    except Exception as e:
        print(e)
        exit(1)
    finally:
        if pwm_out_pin is not None:
            pwm_out_pin.stop()
        if ttl_out_pin is not None:
            ttl_out_pin.stop()
        if ttl_in_pin is not None:
            ttl_in_pin.stop()
