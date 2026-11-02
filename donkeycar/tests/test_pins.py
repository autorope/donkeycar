"""
Tests for the PCA9685 pin provider in pins.py.

These run anywhere: the CircuitPython driver and the I2C bus are both faked,
so no PCA9685, no I2C bus and no Blinka board support are needed.
"""
import sys
import types

import pytest

from donkeycar.parts import pins
from donkeycar.parts.pins import (
    PinProvider, PinState, output_pin_by_id, pwm_pin_by_id,
)


class FakePWMChannel:
    """Stands in for adafruit_pca9685.PWMChannel."""
    def __init__(self, driver, channel):
        self.driver = driver
        self.channel = channel
        self._duty = 0

    @property
    def duty_cycle(self):
        return self._duty

    @duty_cycle.setter
    def duty_cycle(self, value):
        self._duty = value
        self.driver.writes.append((self.channel, value))


class FakeDriver:
    """Stands in for adafruit_pca9685.PCA9685."""
    instances = []

    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.frequency = None
        self.writes = []
        FakeDriver.instances.append(self)


class FakeBus:
    def __init__(self, busnum):
        self.busnum = busnum


@pytest.fixture(autouse=True)
def fake_hardware(monkeypatch):
    """Fake the driver module and the I2C bus, and clear the singletons."""
    module = types.ModuleType("adafruit_pca9685")
    module.PCA9685 = FakeDriver
    module.PWMChannel = FakePWMChannel
    monkeypatch.setitem(sys.modules, "adafruit_pca9685", module)

    import donkeycar.parts.i2c_bus as i2c_bus
    monkeypatch.setattr(i2c_bus, "ExplicitBusI2C", FakeBus)

    FakeDriver.instances = []
    monkeypatch.setattr(pins, "_pca9685", {})
    monkeypatch.setattr(pins, "_pca9685pin", {})
    yield


#
# ----- pin id parsing -----
#
def test_pwm_pin_id_parses_bus_address_and_channel():
    """"PCA9685.1:40.7" is provider.busnum:address.channel."""
    pin = pwm_pin_by_id("PCA9685.1:40.7", frequency_hz=60)
    assert pin.pin_number == 7
    assert pin.pca_pin.channel == 7
    assert pin.pca_pin.board.busnum == 1
    assert pin.pca_pin.board.address == 0x40


def test_output_pin_id_parses_bus_address_and_channel():
    pin = output_pin_by_id("PCA9685.0:70.13")
    assert pin.pin_number == 13
    assert pin.pca_pin.board.busnum == 0
    assert pin.pca_pin.board.address == 0x70


def test_address_is_parsed_as_hex():
    """40 must mean 0x40, not decimal 40."""
    pin = pwm_pin_by_id("PCA9685.1:40.0")
    assert pin.pca_pin.board.address == 64


def test_bus_number_reaches_the_i2c_bus():
    """
    The whole point of ExplicitBusI2C: a pin id naming bus 2 must open bus 2.
    The previous board/busio approach had to ignore the bus number.
    """
    pin = pwm_pin_by_id("PCA9685.2:40.1")
    assert pin.pca_pin.board.i2c.busnum == 2


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        pwm_pin_by_id("NOSUCH.1:40.1")


#
# ----- frequency -----
#
def test_frequency_is_pushed_to_the_driver():
    pwm_pin_by_id("PCA9685.1:40.1", frequency_hz=120)
    assert FakeDriver.instances[0].frequency == 120


def test_second_pin_on_same_board_reuses_it():
    a = pwm_pin_by_id("PCA9685.1:40.1", frequency_hz=60)
    b = pwm_pin_by_id("PCA9685.1:40.2", frequency_hz=60)
    assert a.pca_pin.board is b.pca_pin.board
    assert len(FakeDriver.instances) == 1


def test_board_singleton_is_actually_cached():
    """
    Regression: the factory used not to write into _pca9685, so every call
    re-initialized the board and the conflict check below could never fire.
    """
    pins.pca9685(1, 0x40, 60)
    assert "1:0x40" in pins._pca9685
    pins.pca9685(1, 0x40, 60)
    assert len(FakeDriver.instances) == 1


def test_conflicting_frequency_on_same_board_raises():
    """A PCA9685 has one frequency for all 16 channels."""
    pwm_pin_by_id("PCA9685.1:40.1", frequency_hz=60)
    with pytest.raises(ValueError, match="conflicts"):
        pwm_pin_by_id("PCA9685.1:40.2", frequency_hz=120)


def test_different_boards_may_have_different_frequencies():
    pwm_pin_by_id("PCA9685.1:40.1", frequency_hz=60)
    pwm_pin_by_id("PCA9685.1:41.1", frequency_hz=120)
    assert [d.frequency for d in FakeDriver.instances] == [60, 120]


def test_pin_singleton_is_cached_per_channel():
    a = pins.pca9685pin(3, 1, 0x40, 60)
    b = pins.pca9685pin(3, 1, 0x40, 60)
    assert a is b
    assert pins.pca9685pin(4, 1, 0x40, 60) is not a


#
# ----- channel range -----
#
@pytest.mark.parametrize("channel", [-1, 16, 99])
def test_channel_outside_0_15_raises(channel):
    with pytest.raises(ValueError):
        pins.pca9685pin(channel, 1, 0x40, 60)


@pytest.mark.parametrize("channel", [0, 15])
def test_channel_bounds_are_inclusive(channel):
    assert pins.pca9685pin(channel, 1, 0x40, 60).channel == channel


#
# ----- duty cycle -----
#
def test_duty_cycle_uses_16_bit_resolution():
    """The driver takes 16-bit values; the old library took 12."""
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0.5)
    assert pin.pca_pin.board.driver.writes[-1] == (1, int(0x10000 * 0.5))


def test_duty_cycle_1_uses_the_fully_on_flag():
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0)
    pin.duty_cycle(1.0)
    assert pin.pca_pin.board.driver.writes[-1] == (1, 0xFFFF)


def test_duty_cycle_0_uses_the_fully_off_flag():
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0.5)
    pin.duty_cycle(0.0)
    assert pin.pca_pin.board.driver.writes[-1] == (1, 0x0000)


@pytest.mark.parametrize("duty", [-0.1, 1.1, 2.0])
def test_duty_cycle_outside_0_1_raises(duty):
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0)
    with pytest.raises(ValueError):
        pin.duty_cycle(duty)


def test_pwm_pin_reports_its_duty_cycle():
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0.25)
    assert pin.state() == 0.25


#
# ----- lifecycle -----
#
def test_pwm_pin_starts_not_started():
    assert pwm_pin_by_id("PCA9685.1:40.1").state() == PinState.NOT_STARTED


def test_pwm_pin_rejects_use_before_start():
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    with pytest.raises(RuntimeError):
        pin.duty_cycle(0.5)


def test_pwm_pin_rejects_double_start():
    pin = pwm_pin_by_id("PCA9685.1:40.1")
    pin.start(0)
    with pytest.raises(RuntimeError):
        pin.start(0)


def test_output_pin_high_low_round_trip():
    pin = output_pin_by_id("PCA9685.1:40.2")
    pin.start(PinState.LOW)
    pin.output(PinState.HIGH)
    assert pin.state() == PinState.HIGH
    assert pin.pca_pin.board.driver.writes[-1] == (2, 0xFFFF)
    pin.output(PinState.LOW)
    assert pin.state() == PinState.LOW
    assert pin.pca_pin.board.driver.writes[-1] == (2, 0x0000)


def test_output_pin_stop_returns_to_not_started():
    pin = output_pin_by_id("PCA9685.1:40.2")
    pin.start(PinState.HIGH)
    pin.stop()
    assert pin.state() == PinState.NOT_STARTED


def test_output_pin_is_an_output_pin():
    """Regression: OutputPinPCA9685 used to derive from ABC, not OutputPin."""
    assert isinstance(output_pin_by_id("PCA9685.1:40.2"), pins.OutputPin)


def test_pca9685_cannot_provide_an_input_pin():
    with pytest.raises(RuntimeError):
        pins.input_pin(PinProvider.PCA9685, 1)
