import logging
import time
from typing import Tuple

from numpy import float32

from donkeycar.utilities.circular_buffer import CircularBuffer

logger = logging.getLogger("donkeycar.parts.tachometer")

def sign(value) -> int:
    if value > 0: return 1
    if value < 0: return -1
    return 0


class Tachometer:
    """
    Base class for encoders
    config is ticks per revolution
    input is throttle value, used to set direction
    output is current number of revolutions and timestamp
    """

    # how to process ticks
    FORWARD_ONLY = 1          # only sum ticks (ticks may be signed)
    FORWARD_REVERSE = 2       # subtract ticks if direction is negative
    FORWARD_REVERSE_STOP = 3  # ignore ticks if throttle is zero

    def __init__(self, ticks_per_revolution:float, direction_mode=FORWARD_ONLY):
        self.ticks_per_revolution:float = ticks_per_revolution
        self.direction_mode = direction_mode
        self.ticks:int = 0
        self.direction:int = 1  # default to forward ticks
        self.timestamp:float = 0
        self.start_ticks()

    def start_ticks(self):
        # override in subclass to add your intialization code
        # can call super-class (to set running to True)
        self.running:bool = True

    def poll_ticks(self) -> int:
        # override in subclass to add your code to read ticks
        return 0

    def poll(self, throttle:float=1, timestamp:float=None):
        """
        throttle:  positive means forward
                   negative means backward
                   zero means stopped
        timestamp: the timestamp to apply to the tick reading
                   or None to use the current time
        """
        if self.running:
            # if a timestamp if provided, use it
            self.timestamp = timestamp if timestamp is not None else time.time()

            # set direction flag based on direction mode
            if Tachometer.FORWARD_REVERSE == self.direction_mode:
                # if throttle is zero, leave direction alone
                if throttle != 0:
                    self.direction = sign(throttle)
            elif Tachometer.FORWARD_REVERSE_STOP == self.direction_mode:
                self.direction = sign(throttle)

            self.ticks = self.poll_ticks()

    def update(self, throttle:float=1, timestamp:float=None):
        """
        throttle: sign of throttle is use used to determine direction.
        timestamp: timestamp for update or None to use current time.
                   This is useful for creating deterministic tests.
        """
        while(self.running):
            self.poll(throttle, timestamp)

    def run_threaded(self) -> Tuple[float, float]:
        if self.running:
            # (revolutions, timestamp)
            return (self.ticks / self.ticks_per_revolution, self.timestamp)
        return 0

    def run(self, throttle:float=1, timestamp:float=None) -> Tuple[float, float]:
        self.poll(throttle, timestamp)
        return self.run_threaded()

    def shutdown(self):
        self.running = False


class SerialPort:
    """
    Wrapper for serial port connect/read/write.
    Use this rather than raw pyserial api, so that
    we can mock this for testing.
    """
    def __init__(self, port:str='/dev/ttyACM0', baudrate:int=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def start(self):
        import serial
        import serial.tools.list_ports
        for item in serial.tools.list_ports.comports():
            logger.info(item)  # list all the serial ports
        self.ser = serial.Serial(self.port, self.baudrate, 8, 'N', 1, timeout=0.1)

    def stop(self):
        pass

    def buffered(self) -> int:
        """
        return: the number of buffered characters
        """
        return self.ser.in_waiting

    def read(self, count:int=0) -> Tuple[bool, str]:
        """
        if there are characters waiting, 
        then read them from the serial port
        bytes: number of bytes to read 
        return: tuple of
                bool: True if count bytes were available to read, 
                      false if not enough bytes were avaiable
                str: ascii string if count bytes read (may be blank), 
                     blank if count bytes are not available
        """
        input = ''
        waiting = self.buffered()
        if (waiting >= count):   # read the serial port and see if there's any data there
            buffer = self.ser.read(count)
            input = buffer.decode('ascii')
        return ((waiting > 0), input)


    def readln(self) -> Tuple[bool, str]:
        """
        if there are characters waiting, 
        then read a line from the serial port.
        This will block until end-of-line can be read.
        The end-of-line is included in the return value.
        return: tuple of
                bool: True if line was read, false if not
                str: line if read (may be blank), 
                     blank if not read
        """
        #
        #
        input = ''
        waiting = self.buffered()
        if (waiting > 0):   # read the serial port and see if there's any data there
            buffer = self.ser.readline()
            input = buffer.decode('ascii')
        return ((waiting > 0), input)
        
    def write(self, value:str):
        """
        write string to serial port
        """
        self.ser.write(str.encode(value))  

    def writeln(self, value:str):
        """
        write line to serial port
        """
        self.ser.write(str.encode(value + '\n'))  



class SerialTachometer(Tachometer):
    """
    Encoder that requests tick count over serial port.
    The other end is typically a microcontroller that 
    is reading an encoder, which may be a single-channel
    encoder (so ticks only increase) or a quarature encoder
    (so ticks may increment or decrement).

    Quadrature encoders can detect when the 
    encoder is going forward, backward or stopped.
    For such encoders, use the default direction mode, 
    FORWARD_ONLY, and changes in tick count will correctly 
    be summed to the current tick count.

    Single channel encoders cannot encode direction;
    their count will only ever increase.  So this part
    can take the signed throttle value as direction and
    use it to decide if the ticks should be incremented
    or decremented. 
    For vehicles that 'coast' at zero throttle, choose
    FORWARD_BACKWARD direction mode so we continue to 
    integrate ticks while coasting.
    For vehicles with brakes or that otherwise stop quickly, 
    choose FORWARD_BACKWARD_STOP direction mode 
    so encoder noise is not integrated while stopped.

    This part assumes a microcontroller connected via
    serial port that implements the following 
    'r/p/c' protocol:

    Commands are sent to the microcontroller 
    one per line (ending in '\n'):
    'r' command resets position to zero
    'p' command sends position immediately
    'c' command starts/stops continuous mode
        - if it is followed by an integer,
          then use this as the delay in ms
          between readings.
        - if it is not followed by an integer
          then stop continuous mode
    
    The microcontroller sends one reading per line.
    Each reading includes the tick count and the time
    that the reading was taken, separated by a comma
    and ending in a newline.
    
        {ticks},{milliseconds}\n

    There is an example arduino sketch that implements the
    'r/p/c' protocol using the teensy encoder library at 
    donkeycar/arduino/encoder/encoder.ino  The sketch
    presumes a quadrature encoder connect to pins 2 & 3
    of an arduino.  If you have a different microcontroller
    or want to use different pins or if you want to
    use a single-channel encoder, then modify that sketch.

    """
    def __init__(self, ticks_per_revolution:float, direction_mode:int=Tachometer.FORWARD_ONLY, poll_delay_secs:float=0.01, serial_port:SerialPort=None):
        self.ser = serial_port
        self.lasttick = 0
        self.poll_delay_secs = poll_delay_secs
        Tachometer.__init__(self, ticks_per_revolution, direction_mode)
    
    def shutdown(self):
        if self.ser is not None:
            self.ser.stop()
        return super().shutdown()

    def start_ticks(self):
        self.ser.start()
        self.ser.writeln('r')  # restart the encoder to zero
        if self.poll_delay_secs > 0:
            # start continuous mode if given non-zero delay
            self.ser.writeln("c" + str(int(self.poll_delay_secs * 1000)))
        self.ser.writeln('p')  # ask for the first ticks
        Tachometer.start_ticks(self)       # set running to True

    def poll_ticks(self) -> int:
        #
        # If there are characters waiting, 
        # then read from the serial port.
        # Read all lines and use the last one
        # because it has the most recent reading
        #
        input = ''
        while (self.ser.buffered() > 0):
            _, input = self.ser.readln()

        #
        # queue up another reading by sending the "p" command to the Arduino
        #
        self.ser.writeln('p')  

        #
        # if we got data, update the  ticks
        # if we got no data, then use last ticks we read
        #
        # data is "ticks,ticksMs"
        #
        if input != '':
            try:
                values = [int(s.strip()) for s in input.split(',')]
            except ValueError:
                logger.error("failure parsing encoder values from serial")
            else:
                if len(values) > 0:
                    total_ticks = values[0]
                    delta_ticks = total_ticks - self.lasttick
                    self.lasttick = total_ticks
                    self.ticks += delta_ticks * self.direction
        return self.ticks  # no change


class GpioTachometer(Tachometer):

    def __init__(self, gpio_pin, ticks_per_revolution:float, direction_mode=Tachometer.FORWARD_ONLY, debounce_ns:int=0):
        self.counter = 0
        self.pin = gpio_pin
        self.pi = None
        self.cb = None
        self.debounce_ns:int = debounce_ns
        self.debounce_time:int = 0
        Tachometer.__init__(self, ticks_per_revolution, direction_mode)

    def _cb(self, pin, level, tick):
        """
        Callback routine called by pigpio when a tick is detected
        """
        now = time.time_ns()
        if now > self.debounce_time:
            self.counter += self.direction
            self.debounce_time = now + self.debounce_ns
            
    def start_ticks(self):
        # initialize io
        import pigpio
        self.pi = pigpio.pi()
        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_DOWN)
        self.cb = self.pi.callback(self.pin, pigpio.FALLING_EDGE, self._cb)
        Tachometer.start_ticks(self)     # set runnng to True

    def poll_ticks(self) -> int:                
        return self.counter

    def shutdown(self):
        if self.cb is not None:
            self.cb.cancel()
            self.cb = None
        if self.pi is not None:
            self.pi.stop()
            self.pi = None
        Tachometer.shutdown(self)


if __name__ == "__main__":
    import argparse
    from threading import Thread
    import sys
    import time
    
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rate", type=float, default=20,
                        help = "Number of readings per second")
    parser.add_argument("-n", "--number", type=int, default=40,
                        help = "Number of readings to collect")
    parser.add_argument("-ppr", "--pulses-per-revolution", type=int, required=True, 
                        help="Pulses per revolution of output shaft")
    parser.add_argument("-d", "--direction-mode", type=int, default=1, 
                        help="1=FORWARD_ONLY, 2=FORWARD_REVERSE, 3=FORWARD_REVERSE_STOP")
    parser.add_argument("-s", "--serial-port", type=str, default=None,
                        help="serial-port to open, like '/dev/ttyACM0'")
    parser.add_argument("-b", "--baud-rate", type=int, default=115200, 
                        help="Serial port baud rate")
    parser.add_argument("-p", "--pin", type=int, default=None,
                        help="gpio pin that encoder is connected to")  # noqa
    parser.add_argument("-db", "--debounce-ns", type=int, default=100,
                        help="debounce delay in nanoseconds for reading gpio pin")  # noqa
    parser.add_argument("-t", "--threaded", action='store_true', help = "run in threaded mode")

    # Read arguments from command line
    args = parser.parse_args()
    
    help = []
    if args.rate < 1:
        help.append("-r/--rate: must be >= 1.")
        
    if args.number < 1:
        help.append("-n/--number: must be >= 1.")
        
    if args.direction_mode < 1 and args.direction_mode > 3:
        help.append("-d/--direction-mode must be 1, 2, or")

    if args.pulses_per_revolution <= 0:
        help.append("-ppr/--pulses-per-revolution must be > 0")
        
    if args.serial_port is None and args.pin is None:
        help.append("either -s/--serial_port or -p/--pin must be passed")

    if args.serial_port is not None and args.pin is not None:
        help.append("only one of -s/--serial_port or -p/--pin must be passed")

    if args.serial_port is not None and len(args.serial_port) == 0:
        help.append("-s/--serial-port not be empty if passed")
      
    if args.baud_rate <= 0:
        help.append("-b/--baud-rate must be > 0")
        
    if args.pin is not None and args.pin <= 0:
        help.append("-p/--pint must be > 0 if passed")

    if args.debounce_ns < 0:
        help.append("-db/--debounce-ns must be greater than zero")
                
    if len(help) > 0:
        parser.print_help()
        for h in help:
            print("  " + h)
        sys.exit(1)
        
    update_thread = None
    serial_port = None
    tachometer = None
    
    try:
        scan_count = 0
        seconds_per_scan = 1.0 / args.rate
        scan_time = time.time() + seconds_per_scan

        #
        # construct a tachometer part of the correct type
        #
        if args.serial_port is not None:
            serial_port = SerialPort(args.serial_port, args.baud_rate)
            tachometer = SerialTachometer(
                ticks_per_revolution=args.pulses_per_revolution, 
                direction_mode=args.direction_mode, 
                poll_delay_secs=1/(args.rate*2), 
                serial_port=serial_port)
        if args.pin is not None:
            tachometer = GpioTachometer(
                gpio_pin=args.pin,
                ticks_per_revolution=args.pulses_per_revolution, 
                direction_mode=args.direction_mode,
                debounce_ns=args.debounce_ns)
        
        #
        # start the threaded part
        # and a threaded window to show plot
        #
        if args.threaded:
            update_thread = Thread(target=tachometer.update, args=())
            update_thread.start()
        
        while scan_count < args.number:
            start_time = time.time()

            # emit the scan
            scan_count += 1

            # get most recent scan and plot it
            if args.threaded:
                measurements = tachometer.run_threaded()
            else:
                measurements = tachometer.run()

            print(measurements)
                                    
            # yield time to background threads
            sleep_time = seconds_per_scan - (time.time() - start_time)
            if sleep_time > 0.0:
                time.sleep(sleep_time)
            else:
                time.sleep(0)  # yield time to other threads

    except KeyboardInterrupt:
        print('Stopping early.')
    except Exception as e:
        print(e)
        exit(1)
    finally:
        if tachometer is not None:
            tachometer.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end
