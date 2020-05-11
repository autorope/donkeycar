# Donkey Car Driver for Robotics Masters Robo HAT MM1
#
# Notes:
#   This is to be run using CircuitPython 5.3
#   Date: 15/05/2019
#   Updated: 20/02/2020
#   Updated: 8/03/2020 (sctse999)
#   Updated: 11/05/2020 (wallarug)
#
#

import time
import board
import busio

from digitalio import DigitalInOut, Direction
from pulseio import PWMOut, PulseIn, PulseOut

import adafruit_logging as logging
logger = logging.getLogger('code')
logger.setLevel(logging.INFO)

# Customisation these variables
DEBUG = False
USB_SERIAL = False
SMOOTHING_INTERVAL_IN_S = 0.025
ACCEL_RATE = 10

## cannot have DEBUG and USB_SERIAL
if USB_SERIAL:
    DEBUG = False

## functions
def servo_duty_cycle(pulse_ms, frequency = 60):
    """
    Formula for working out the servo duty_cycle at 16 bit input
    """
    period_ms = 1.0 / frequency * 1000.0
    duty_cycle = int(pulse_ms / 1000 / (period_ms / 65535.0))
    return duty_cycle


def state_changed(control):
    """
    Reads the RC channel and smooths value
    """
    control.channel.pause()
    for i in range(0, len(control.channel)):
        val = control.channel[i]
        # prevent ranges outside of control space
        if(val < 1000 or val > 2000):
            continue
        # set new value
        control.value = (control.value + val) / 2

    if DEBUG:
        logger.debug("%f\t%s (%i): %i (%i)" % (time.monotonic(), control.name, len(
            control.channel), control.value, servo_duty_cycle(control.value)))
    control.channel.clear()
    control.channel.resume()


class Control:
    """
    Class for a RC Control Channel
    """

    def __init__(self, name, servo, channel, value):
        self.name = name
        self.servo = servo
        self.channel = channel
        self.value = value
        self.servo.duty_cycle = servo_duty_cycle(value)


# set up on-board LED
led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT

# set up serial UART to Raspberry Pi
# note UART(TX, RX, baudrate)
uart = busio.UART(board.TX1, board.RX1, baudrate=115200, timeout=0.001)

# set up servos
steering_pwm = PWMOut(board.SERVO2, duty_cycle=2 ** 15, frequency=60)
throttle_pwm = PWMOut(board.SERVO1, duty_cycle=2 ** 15, frequency=60)

# set up RC channels.  NOTE: input channels are RCC3 & RCC4 (not RCC1 & RCC2)
steering_channel = PulseIn(board.RCC4, maxlen=64, idle_state=0)
throttle_channel = PulseIn(board.RCC3, maxlen=64, idle_state=0)

# setup Control objects.  1500 pulse is off and center steering
steering = Control("Steering", steering_pwm, steering_channel, 1500)
throttle = Control("Throttle", throttle_pwm, throttle_channel, 1500)

# Hardware Notification: starting
logger.info("preparing to start...")
for i in range(0, 2):
    led.value = True
    time.sleep(0.5)
    led.value = False
    time.sleep(0.5)

last_update = time.monotonic()

# GOTO: main()
def main():
    global last_update

    data = bytearray('')
    datastr = ''
    last_input = 0
    steering_val = steering.value
    throttle_val = throttle.value

    while True:
        # only update every smoothing interval (to avoid jumping)
        if(last_update + SMOOTHING_INTERVAL_IN_S > time.monotonic()):
            continue
        last_update = time.monotonic()

        # check for new RC values (channel will contain data)
        if(len(throttle.channel) != 0):
            state_changed(throttle)

        if(len(steering.channel) != 0):
            state_changed(steering)

        if DEBUG:
            logger.info("Get: steering=%i, throttle=%i" % (int(steering.value), int(throttle.value)))
        
        if(USB_SERIAL):
            # simulator USB
            print("%i, %i" % (int(steering.value), int(throttle.value)))
        else:
            # write the RC values to the RPi Serial
            uart.write(b"%i, %i\r\n" % (int(steering.value), int(throttle.value)))

        while True:
            # wait for data on the serial port and read 1 byte
            byte = uart.read(1)

            # if no data, break and continue with RC control
            if(byte == None):
                break
            last_input = time.monotonic()

            if (DEBUG):
                logger.debug("Read from UART: %s" % (byte))

            # if data is recieved, check if it is the end of a stream
            if(byte == b'\r'):
                data = bytearray('')
                break

            data[len(data):len(data)] = byte

            # convert bytearray to string
            datastr = ''.join([chr(c) for c in data]).strip()

        # if we make it here, there is serial data from the previous step
        if(len(datastr) >= 10):
            steering_val = steering.value
            throttle_val = throttle.value
            try:
                steering_val = int(datastr[:4])
                throttle_val = int(datastr[-4:])
            except ValueError:
                None

            data = bytearray('')
            datastr = ''
            last_input = time.monotonic()
            logger.info("Set: steering=%i, throttle=%i" % (steering_val, throttle_val))

        if(last_input + 10 < time.monotonic()):
            # set the servo for RC control
            steering.servo.duty_cycle = servo_duty_cycle(steering.value)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle.value)
        else:
            # set the servo for serial data (recieved)
            steering.servo.duty_cycle = servo_duty_cycle(steering_val)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle_val)


# Run
logger.info("Run!")
main()
