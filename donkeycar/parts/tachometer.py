from abc import (ABC, abstractmethod)
import logging
import time
from typing import Tuple

from donkeycar.utilities.platform import is_jetson
from donkeycar.utilities.serial_port import SerialPort
from donkeycar.parts.pins import InputPin, PinEdge


logger = logging.getLogger("donkeycar.parts.tachometer")


class AbstractEncoder(ABC):
    """
    Interface for an encoder.
    To create a new encoder class, subclass from
    AbstractEncoder and implement
    start_ticks(), stop_ticks() and poll_ticks().
    Tachometer() takes an encoder in it's contructor.
    """
    @abstractmethod
    def start_ticks(self):
        """Initialize the encoder"""
        pass

    @abstractmethod
    def stop_ticks(self):
        """release the encoder resources"""
        pass

    @abstractmethod
    def poll_ticks(self, direction:int):
        """
        Update the encoder ticks
        direction: 1 if forward, -1 if reverse, 0 if stopped.

        This will request a new value from the encoder.
        """
        pass

    @abstractmethod
    def get_ticks(self, encoder_index:int=0) -> int:
        """
        Get last polled encoder ticks
        encoder_index: zero based index of encoder.
        return: Most recently polled encoder ticks

        This will return the value from the
        most recent call to poll_ticks().  It 
        will not request new values from the encoder.
        """
        return 0

class SerialEncoder(AbstractEncoder):
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
    and ending in a newline.  Readings for multiple
    encoders are separated by colons.

        {ticks},{milliseconds};{ticks},{milliseconds}\n

    There is an example arduino sketch that implements the
    'r/p/c' protocol using the teensy encoder library at 
    donkeycar/arduino/encoder/encoder.ino  The sketch
    presumes a quadrature encoder connect to pins 2 & 3
    of an arduino.  If you have a different microcontroller
    or want to use different pins or if you want to
    use a single-channel encoder, then modify that sketch.

    """
    def __init__(self, serial_port:SerialPort=None, debug=False):
        if serial_port is None:
            raise ValueError("serial_port must be an instance of SerialPort")
        self.ser = serial_port
        self.ticks = [0,0]
        self.lasttick = [0,0]
        self.running = False
    
    def start_ticks(self):
        self.ser.start()
        self.ser.writeln('r')  # restart the encoder to zero
        # if self.poll_delay_secs > 0:
        #     # start continuous mode if given non-zero delay
        #     self.ser.writeln("c" + str(int(self.poll_delay_secs * 1000)))
        self.ser.writeln('p')  # ask for the first ticks
        self.running = True

    def stop_ticks(self):
        self.running = False
        if self.ser is not None:
            self.ser.stop()

    def poll_ticks(self, direction:int):
        """
        read the encoder ticks
        direction: 1 if forward, -1 if reverse, 0 if stopped.
        return: updated encoder ticks
        """
        #
        # If there are characters waiting, 
        # then read from the serial port.
        # Read all lines and use the last one
        # because it has the most recent reading
        #
        input = ''
        while (self.running and (self.ser.buffered() > 0)):
            _, input = self.ser.readln()

        #
        # queue up another reading by sending the "p" command to the Arduino
        #
        self.ser.writeln('p')  

        #
        # if we got data, update the  ticks
        # if we got no data, then use last ticks we read
        #
        # data for encoders is separated by semicolon
        # and ticks and time for single encoder
        # is comma separated.
        # 
        #  "ticks,ticksMs;ticks,ticksMs"
        #
        if input != '':
            try:
                # 
                # split separate encoder outputs
                # "ticks,time;ticks,time" -> ["ticks,time", "ticks,time"]
                #
                values = [s.strip() for s in input.split(';')]

                #
                # split tick/time pairs for each encoder
                # ["ticks,time", "ticks,time"] -> [["ticks", "time"], ["ticks", "time"]]
                #
                values = [v.split(',') for v in values]
                for i in range(len(values)):
                    total_ticks = int((values[i][0]).strip())
                    delta_ticks = total_ticks - self.lasttick[i]
                    self.lasttick[i] = total_ticks
                    self.ticks[i] += delta_ticks * direction
                
            except ValueError:
                logger.error("failure parsing encoder values from serial")

    def get_ticks(self, encoder_index:int=0) -> int:
        """
        Get last polled encoder ticks
        encoder_index: zero based index of encoder.
        return: Most recently polled encoder ticks

        This will return the same value as the
        most recent call to poll_ticks().  It 
        will not request new values from the encoder.
        """
        return self.ticks[encoder_index] if encoder_index < len(self.ticks) else 0


class EncoderChannel(AbstractEncoder):
    """
    Wrapper around SerialEncoder to pull 
    out channel 2 as separate encoder.

    This MUST be added AFTER the parent SerialEncoder,
    so that the parent encodere gets polled before 
    we attempt to call get_ticks() for this encoder channel.
    """
    def __init__(self, encoder:SerialEncoder, channel:int) -> None:
        self.encoder = encoder
        self.channel = channel
        super().__init__()

    def start_ticks(self):
        pass

    def stop_ticks(self):
        pass

    def poll_ticks(self, direction:int):
        pass

    def get_ticks(self, encoder_index:int=0) -> int:
        return self.encoder.get_ticks(encoder_index=self.channel)


class GpioEncoder(AbstractEncoder):
    """
    An single-channel encoder read using an InputPin
    :gpio_pin: InputPin that will get the signal
    :debounce_ns: int number of nano seconds before accepting another 
                  encoder signal.  This is used to ignore bounces.
    :debug: bool True to output extra logging
    """
    def __init__(self, gpio_pin: InputPin, debounce_ns:int=0, debug=False):
        # validate gpio_pin
        if gpio_pin is None:
            raise ValueError('The encoder input pin must be a valid InputPin.')

        self.debug = debug
        self.counter = 0
        self.direction = 0
        self.pin = gpio_pin
        self.debounce_ns:int = debounce_ns
        self.debounce_time:int = 0
        if self.debounce_ns > 0:
            logger.warn("GpioEncoder debounce_ns will be ignored.")

    def _cb(self, _):
        """
        Callback routine called by GPIO when a tick is detected
        :pin_number: int the pin number that generated the interrupt.
        :pin_state: int the state of the pin
        """
        self.counter += self.direction

            
    def start_ticks(self):
        # configure GPIO pin
        self.pin.start(on_input=self._cb, edge=PinEdge.RISING)
        logger.info(f'GpioEncoder on InputPin "RPI_GPIO.{self.pin.pin_scheme_str}.{self.pin.pin_number}" started.')


    def poll_ticks(self, direction:int):  
        """
        read the encoder ticks
        direction: 1 if forward, -1 if reverse, 0 if stopped.
        return: updated encoder ticks
        """
        self.direction = direction

    def stop_ticks(self):
        self.pin.stop()
        logger.info(f'GpioEncoder on InputPin "RPI_GPIO.{self.pin.pin_scheme_str}.{self.pin.pin_number}" stopped.')

    def get_ticks(self, encoder_index:int=0) -> int:
        """
        Get last polled encoder ticks
        encoder_index: zero based index of encoder.
        return: Most recently polled encoder ticks

        This will return the same value as the
        most recent call to poll_ticks().  It 
        will not request new values from the encoder.
        """
        return self.counter if encoder_index == 0 else 0


def sign(value) -> int:
    if value > 0: return 1
    if value < 0: return -1
    return 0


class TachometerMode:
    FORWARD_ONLY = 1          # only sum ticks (ticks may be signed)
    FORWARD_REVERSE = 2       # subtract ticks if throttle is negative
    FORWARD_REVERSE_STOP = 3  # ignore ticks if throttle is zero
    

class Tachometer:
    """
    Tachometer converts encoder ticks to revolutions
    and supports modifying direction based on
    throttle input.
    encoder is an instance of an encoder class
    derived from AbstactEncoder.  
    config is ticks per revolution,
    input is throttle value (used to set direction),
    output is current number of revolutions and timestamp
    note: if you just want raw encoder output, use 
          ticks_per_revolution=1
    """

    def __init__(self, 
        encoder:AbstractEncoder, 
        ticks_per_revolution:float=1, 
        direction_mode=TachometerMode.FORWARD_ONLY, 
        poll_delay_secs:float=0.01, 
        debug=False):
        
        if encoder is None:
            raise ValueError("encoder must be an instance of AbstractEncoder")
        self.encoder = encoder
        self.running:bool = False
        self.ticks_per_revolution:float = ticks_per_revolution
        self.direction_mode = direction_mode
        self.ticks:int = 0
        self.direction:int = 1  # default to forward ticks
        self.timestamp:float = 0
        self.throttle = 0.0
        self.debug = debug
        self.poll_delay_secs = poll_delay_secs
        self.encoder.start_ticks()
        self.running = True

    def poll(self, throttle, timestamp):
        """
        throttle:  positive means forward
                   negative means backward
                   zero means stopped
        timestamp: the timestamp to apply to the tick reading
                   or None to use the current time
        """
        if self.running:
            # if a timestamp if provided, use it
            if timestamp is None:
                timestamp = time.time()

            # set direction flag based on direction mode
            if throttle is not None:
                if TachometerMode.FORWARD_REVERSE == self.direction_mode:
                    # if throttle is zero, leave direction alone to model 'coasting'
                    if throttle != 0:
                        self.direction = sign(throttle)
                elif TachometerMode.FORWARD_REVERSE_STOP == self.direction_mode:
                    self.direction = sign(throttle)

            lastTicks = self.ticks
            self.timestamp = timestamp
            self.encoder.poll_ticks(self.direction)
            self.ticks = self.encoder.get_ticks()
            if self.debug and self.ticks != lastTicks:
                logger.info("tachometer: t = {}, r = {}, ts = {}".format(self.ticks, self.ticks / self.ticks_per_revolution, timestamp))

    def update(self):
        """
        throttle: sign of throttle is use used to determine direction.
        timestamp: timestamp for update or None to use current time.
                   This is useful for creating deterministic tests.
        """
        while(self.running):
            self.poll(self.throttle, self.timestamp)
            time.sleep(self.poll_delay_secs)  # give other threads time

    def run_threaded(self, throttle:float=0.0, timestamp:float=None) -> Tuple[float, float]:
        if self.running:
            thisTimestamp = self.timestamp
            thisRevolutions = self.ticks / self.ticks_per_revolution

            # update throttle for next poll()
            self.throttle = throttle
            self.timestamp = timestamp

            # return (revolutions, timestamp)
            return (thisRevolutions, thisTimestamp)
        return (0, self.timestamp)

    def run(self, throttle:float=1.0, timestamp:float=None) -> Tuple[float, float]:
        if self.running:
            # update throttle for next poll()
            self.throttle = throttle
            self.timestamp = timestamp
            self.poll(throttle, timestamp)

            # return (revolutions, timestamp)
            return (self.ticks / self.ticks_per_revolution, self.timestamp)
        return (0, self.timestamp)

    def shutdown(self):
        self.running = False
        self.encoder.stop_ticks()


if __name__ == "__main__":
    import argparse
    from threading import Thread
    import sys
    import time
    from donkeycar.parts.pins import input_pin_by_id

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
    parser.add_argument("-p", "--pin", type=str, default=None,
                        help="pin specifier for encoder InputPin, like 'RPI_GPIO.BCM.22'")  # noqa
    parser.add_argument("-dbc", "--debounce-ns", type=int, default=100,
                        help="debounce delay in nanoseconds for reading gpio pin")  # noqa
    parser.add_argument("-db", "--debug", action='store_true', help = "show debug output")
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
        
    if args.pin is not None and args.pin == "":
        help.append("-p/--pin must be non-empty if passed")

    if args.debounce_ns < 0:
        help.append("-dbc/--debounce-ns must be greater than zero")
                
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
            tachometer = Tachometer(
                encoder=SerialEncoder(serial_port=serial_port, debug=args.debug),
                ticks_per_revolution=args.pulses_per_revolution, 
                direction_mode=args.direction_mode, 
                poll_delay_secs=1/(args.rate*2), 
                debug=args.debug)
        if args.pin is not None:
            tachometer = Tachometer(
                encoder=GpioEncoder(gpio_pin=input_pin_by_id(args.pin), debounce_ns=args.debounce_ns, debug=args.debug),
                ticks_per_revolution=args.pulses_per_revolution, 
                direction_mode=args.direction_mode,
                debug=args.debug)
        
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
