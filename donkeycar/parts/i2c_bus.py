"""
i2c_bus.py - an I2C bus addressed by bus number.

The Adafruit CircuitPython drivers expect a `busio.I2C`, which Blinka builds
from board pin objects: `busio.I2C(board.SCL, board.SDA)`.  That only works
when `adafruit-platformdetect` recognises the board, and it does not
recognise every Linux SBC.  On the Arduino Uno Q, for instance, it reports
both chip and board as None, so `import board` raises and no CircuitPython
driver can be constructed -- even though /dev/i2c-0..2 are perfectly usable.
Forcing GENERIC_LINUX_PC does not rescue it either; `busio.I2C` then fails
importing `i2cPorts` from `microcontroller.pin`.

ExplicitBusI2C skips board detection entirely and opens a bus by its number,
which is what donkeycar wants anyway: the bus number is already part of a pin
id ("PCA9685.1:40.7" is provider.busnum:address.channel) and of the
PCA9685_I2C_BUSNUM config value.

Blinka's generic-Linux backend already provides most of the `busio.I2C`
surface -- writeto(), readfrom_into(), writeto_then_readfrom() and scan() --
so this adds only the three methods it lacks: try_lock(), unlock() and
deinit().

Use it in place of a busio.I2C:

 from donkeycar.parts.i2c_bus import ExplicitBusI2C
 import adafruit_pca9685
 pca = adafruit_pca9685.PCA9685(ExplicitBusI2C(1), address=0x40)

"""
from typing import Any, Callable, List, Optional
import logging
import threading


logger = logging.getLogger(__name__)


def _default_backend(busnum: int) -> Any:
    """
    Open Blinka's generic-Linux I2C backend for the given bus number.
    Imported lazily so that importing this module does not require Blinka.
    :param busnum: I2C bus number, as in /dev/i2c-<busnum>
    :return: the backend bus object
    :except: ImportError if adafruit-blinka is not installed
    """
    from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
    return I2C(busnum)


class ExplicitBusI2C:
    """
    A busio.I2C-compatible bus opened by bus number rather than by board pins.

    This is duck-typed against busio.I2C rather than deriving from it,
    because deriving would drag in the board detection this exists to avoid.
    """

    def __init__(self, busnum: int,
                 backend: Optional[Callable[[int], Any]] = None) -> None:
        """
        :param busnum: I2C bus number, as in /dev/i2c-<busnum>
        :param backend: factory taking a bus number and returning a bus with
                        the Blinka generic-Linux I2C interface.  Defaults to
                        that backend; injectable so this can be tested
                        without hardware.
        :except: RuntimeError if the bus does not exist
        :except: PermissionError if the process may not open the bus; on
                 Debian /dev/i2c-* is root:i2c 0660, so the user must be in
                 the i2c group
        """
        if busnum is None or busnum < 0:
            raise ValueError(f"busnum must be a non-negative integer, got {busnum}")
        self.busnum = busnum
        # Non-reentrant by design: try_lock() must report contention, and a
        # reentrant lock would let a single thread acquire it twice.
        self._lock = threading.Lock()
        self._bus: Optional[Any] = (backend or _default_backend)(busnum)
        logger.info(f"Opened I2C bus {busnum}")

    def _require_bus(self) -> Any:
        if self._bus is None:
            raise RuntimeError(f"I2C bus {self.busnum} is deinitialized")
        return self._bus

    #
    # ----- the three methods the generic-Linux backend lacks -----
    #
    def try_lock(self) -> bool:
        """
        Attempt to take the bus without blocking.
        :return: True if the bus was acquired, False if another caller holds it
        """
        self._require_bus()
        return self._lock.acquire(blocking=False)

    def unlock(self) -> None:
        """
        Release the bus.  Safe to call when not held, which matches how the
        CircuitPython drivers unlock in a finally block.
        """
        if self._lock.locked():
            self._lock.release()

    def deinit(self) -> None:
        """
        Close the bus.  Idempotent.  Further transfers raise RuntimeError.
        """
        bus, self._bus = self._bus, None
        if bus is None:
            return
        # The backend has no deinit; close the underlying SMBus if it has one.
        closer = getattr(getattr(bus, "_i2c_bus", None), "close", None)
        if callable(closer):
            try:
                closer()
            except Exception as e:
                logger.warning(f"Error closing I2C bus {self.busnum}: {e}")
        logger.info(f"Closed I2C bus {self.busnum}")

    #
    # ----- delegated to the backend -----
    #
    def scan(self) -> List[int]:
        """
        :return: the addresses that responded on the bus
        """
        return self._require_bus().scan()

    def writeto(self, address: int, buffer: bytes, **kwargs: Any) -> None:
        return self._require_bus().writeto(address, buffer, **kwargs)

    def readfrom_into(self, address: int, buffer: bytearray, **kwargs: Any) -> None:
        return self._require_bus().readfrom_into(address, buffer, **kwargs)

    def writeto_then_readfrom(self, address: int, buffer_out: bytes,
                              buffer_in: bytearray, **kwargs: Any) -> None:
        return self._require_bus().writeto_then_readfrom(
            address, buffer_out, buffer_in, **kwargs)

    def __enter__(self) -> "ExplicitBusI2C":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.deinit()

    def __repr__(self) -> str:
        state = "deinitialized" if self._bus is None else "open"
        return f"ExplicitBusI2C(busnum={self.busnum}, {state})"
