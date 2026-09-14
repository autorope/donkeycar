"""
Tests for ExplicitBusI2C, the bus-number-addressed busio.I2C stand-in.
These run anywhere: the backend is injected, so no I2C hardware or Blinka
board support is needed.
"""
import threading

import pytest

from donkeycar.parts.i2c_bus import ExplicitBusI2C


class FakeSMBus:
    """Stands in for Adafruit_PureIO.smbus.SMBus."""
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeBackend:
    """Stands in for Blinka's generic-Linux I2C, recording transfers."""
    def __init__(self, busnum, present=(0x40,)):
        self.busnum = busnum
        self.present = list(present)
        self.calls = []
        self._i2c_bus = FakeSMBus()

    def scan(self):
        self.calls.append(("scan",))
        return list(self.present)

    def writeto(self, address, buffer, **kwargs):
        self.calls.append(("writeto", address, bytes(buffer), kwargs))

    def readfrom_into(self, address, buffer, **kwargs):
        self.calls.append(("readfrom_into", address, len(buffer), kwargs))
        for i in range(len(buffer)):
            buffer[i] = 0xAB

    def writeto_then_readfrom(self, address, buffer_out, buffer_in, **kwargs):
        self.calls.append(("writeto_then_readfrom", address,
                           bytes(buffer_out), len(buffer_in), kwargs))
        for i in range(len(buffer_in)):
            buffer_in[i] = 0xCD


@pytest.fixture
def bus():
    backends = []

    def factory(busnum):
        backends.append(FakeBackend(busnum))
        return backends[-1]

    b = ExplicitBusI2C(2, backend=factory)
    b._fake = backends[0]
    return b


def test_opens_the_requested_bus_number(bus):
    assert bus.busnum == 2
    assert bus._fake.busnum == 2


@pytest.mark.parametrize("busnum", [None, -1])
def test_rejects_invalid_bus_numbers(busnum):
    with pytest.raises(ValueError):
        ExplicitBusI2C(busnum, backend=lambda n: FakeBackend(n))


def test_bus_zero_is_valid():
    """Bus 0 is a real bus; it must not be confused with a falsy busnum."""
    b = ExplicitBusI2C(0, backend=lambda n: FakeBackend(n))
    assert b.busnum == 0


#
# ----- the three methods the backend lacks -----
#
def test_try_lock_then_unlock_round_trips(bus):
    assert bus.try_lock() is True
    bus.unlock()
    assert bus.try_lock() is True
    bus.unlock()


def test_try_lock_is_not_reentrant(bus):
    """A driver holding the bus must see contention, not a second grant."""
    assert bus.try_lock() is True
    assert bus.try_lock() is False
    bus.unlock()


def test_try_lock_reports_contention_across_threads(bus):
    assert bus.try_lock() is True
    result = []
    t = threading.Thread(target=lambda: result.append(bus.try_lock()))
    t.start()
    t.join()
    assert result == [False]
    bus.unlock()
    result.clear()
    t = threading.Thread(target=lambda: result.append(bus.try_lock()))
    t.start()
    t.join()
    assert result == [True]


def test_unlock_when_not_held_is_harmless(bus):
    """The drivers unlock in a finally block, so this must not raise."""
    bus.unlock()
    bus.unlock()
    assert bus.try_lock() is True


def test_deinit_closes_the_underlying_bus(bus):
    fake = bus._fake
    bus.deinit()
    assert fake._i2c_bus.closed is True


def test_deinit_is_idempotent(bus):
    bus.deinit()
    bus.deinit()


def test_use_after_deinit_raises(bus):
    bus.deinit()
    with pytest.raises(RuntimeError):
        bus.scan()
    with pytest.raises(RuntimeError):
        bus.writeto(0x40, b"\x00")
    with pytest.raises(RuntimeError):
        bus.try_lock()


def test_deinit_survives_a_backend_that_cannot_close():
    class NoCloseBackend(FakeBackend):
        def __init__(self, busnum):
            super().__init__(busnum)
            self._i2c_bus = object()

    b = ExplicitBusI2C(1, backend=NoCloseBackend)
    b.deinit()


def test_context_manager_deinits():
    fakes = []

    def factory(busnum):
        fakes.append(FakeBackend(busnum))
        return fakes[-1]

    with ExplicitBusI2C(1, backend=factory) as b:
        assert b.scan() == [0x40]
    assert fakes[0]._i2c_bus.closed is True


#
# ----- delegation -----
#
def test_scan_delegates(bus):
    assert bus.scan() == [0x40]
    assert ("scan",) in bus._fake.calls


def test_writeto_delegates_with_kwargs(bus):
    bus.writeto(0x40, b"\x01\x02", start=0, end=2)
    assert bus._fake.calls[-1] == (
        "writeto", 0x40, b"\x01\x02", {"start": 0, "end": 2})


def test_readfrom_into_fills_the_caller_buffer(bus):
    buf = bytearray(3)
    bus.readfrom_into(0x40, buf)
    assert buf == bytearray([0xAB, 0xAB, 0xAB])


def test_writeto_then_readfrom_fills_the_caller_buffer(bus):
    buf = bytearray(2)
    bus.writeto_then_readfrom(0x40, b"\xfe", buf)
    assert buf == bytearray([0xCD, 0xCD])


def test_satisfies_the_busio_i2c_surface(bus):
    """
    The CircuitPython drivers duck-type against busio.I2C; if any of these
    goes missing the drivers break at runtime rather than at import.
    """
    for name in ("try_lock", "unlock", "deinit", "scan", "writeto",
                 "readfrom_into", "writeto_then_readfrom"):
        assert callable(getattr(bus, name)), name


def test_repr_reports_state(bus):
    assert "busnum=2" in repr(bus) and "open" in repr(bus)
    bus.deinit()
    assert "deinitialized" in repr(bus)
