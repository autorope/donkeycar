import logging
from typing import Tuple
import serial
import serial.tools.list_ports
import threading
import time
import donkeycar.utilities.dk_platform as dk_platform


logger = logging.getLogger(__name__)


class SerialPort:
    """
    Wrapper for serial port connect/read/write.
    Use this rather than raw pyserial api.
    It provides a layer that automatically 
    catches exceptions and encodes/decodes
    between bytes and str.  
    It also provides a layer of indirection 
    so that we can mock this for testing.
    """
    def __init__(self, port:str='/dev/ttyACM0', baudrate:int=115200, bits:int=8, parity:str='N', stop_bits:int=1, charset:str='ascii', timeout:float=0.1):
        self.port = port
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.charset = charset
        self.timeout = timeout
        self.ser = None

    def start(self):
        for item in serial.tools.list_ports.comports():
            logger.info(item)  # list all the serial ports
        self.ser = serial.Serial(self.port, self.baudrate, self.bits, self.parity, self.stop_bits, timeout=self.timeout)
        logger.debug("Opened serial port " + self.ser.name)
        return self

    def stop(self):
        if self.ser is not None:
            sp = self.ser
            self.ser = None
            sp.close()
        return self

    def buffered(self) -> int:
        """
        return: the number of buffered characters
        """
        if self.ser is None or not self.ser.is_open:
            return 0

        # ser.in_waiting is always zero on mac, so act like we are buffered
        if dk_platform.is_mac():
            return 1

        try:
            return self.ser.in_waiting
        except serial.serialutil.SerialException:
            return 0

    def clear(self):
        """
        Clear the serial read buffer
        """
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.reset_input_buffer()
        except serial.serialutil.SerialException:
            pass
        return self

    def readBytes(self, count:int=0) -> Tuple[bool, bytes]:
        """
        if there are characters waiting, 
        then read them from the serial port
        bytes: number of bytes to read 
        return: tuple of
                bool: True if count bytes were available to read, 
                      false if not enough bytes were avaiable
                bytes: string string if count bytes read (may be blank), 
                       blank if count bytes are not available
        """
        if self.ser is None or not self.ser.is_open:
            return (False, b'')

        try:
            input = ''
            waiting = self.buffered() >= count
            if waiting:   # read the serial port and see if there's any data there
                input = self.ser.read(count)
            return (waiting, input)
        except (serial.serialutil.SerialException, TypeError):
            logger.warn("failed reading bytes from serial port")
            return (False, b'')

    def read(self, count:int=0) -> Tuple[bool, str]:
        """
        if there are characters waiting, 
        then read them from the serial port
        bytes: number of bytes to read 
        return: tuple of
                bool: True if count bytes were available to read, 
                      false if not enough bytes were available
                str: ascii string if count bytes read (may be blank), 
                     blank if count bytes are not available
        """
        ok, bytestring = self.readBytes(count)
        try:
            return (ok, bytestring.decode(self.charset))
        except UnicodeDecodeError:
            # the first read often includes mis-framed garbase
            return (False, "")

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
        if self.ser is None or not self.ser.is_open:
            return (False, "")

        try:
            input = ''
            waiting = self.buffered() > 0
            if waiting:   # read the serial port and see if there's any data there
                buffer = self.ser.readline()
                input = buffer.decode(self.charset)
            return (waiting, input)
        except (serial.serialutil.SerialException, TypeError):
            logger.warn("failed reading line from serial port")
            return (False, "")
        except UnicodeDecodeError:
            # the first read often includes mis-framed garbase
            logger.warn("failed decoding unicode line from serial port")
            return (False, "")

    def writeBytes(self, value:bytes):
        """
        write byte string to serial port
        """
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.write(value)  
            except (serial.serialutil.SerialException, TypeError):
                logger.warn("Can't write to serial port")

    def write(self, value:str):
        """
        write string to serial port
        """
        self.writeBytes(value.encode())

    def writeln(self, value:str):
        """
        write line to serial port
        """
        self.write(value + '\n')


class SerialLineReader:
    """
    Donkeycar part for reading lines from a serial port
    """
    def __init__(self, serial:SerialPort, max_lines:int = 0, debug:bool = False):
        self.serial = serial
        self.max_lines = max_lines  # max number of lines per read cycle
        self.debug = debug
        self.lines = []
        self.lock = threading.Lock()
        self.running = True
        self._open()
        self.clear()

    def _open(self):
        with self.lock:
            self.serial.start().clear()

    def _close(self):
        with self.lock:
            self.serial.stop()

    def clear(self):
        """
        Clear the lines buffer and serial port input buffer
        """
        with self.lock:
            self.lines = []
            self.serial.clear()

    def _readline(self) -> str:
        """
        Read a line from the serial port in a threadsafe manner
        returns line if read and None if no line was read
        """
        if self.lock.acquire(blocking=False):
            try:
                # TODO: Serial.in_waiting _always_ returns 0 in Macintosh
                if dk_platform.is_mac() or (self.serial.buffered() > 0):
                    success, buffer = self.serial.readln()
                    if success:
                        return buffer
            finally:
                self.lock.release()
        return None

    def run(self):
        if self.running:
            #
            # in non-threaded mode, just max_lines and return them
            #
            lines = []
            line = self._readline()
            while line is not None:
                lines.append((time.time(), line))
                line = None
                if self.max_lines is None or self.max_lines == 0 or len(lines) < self.max_lines:
                    line = self._readline()
            return lines
        return []

    def run_threaded(self):
        if not self.running:
            return []

        #
        # return the accumulated readings
        #
        with self.lock:
            lines = self.lines
            self.lines = []
            return lines


    def update(self):
        #
        # open serial port and run an infinite loop.
        # NOTE: this is NOT compatible with non-threaded run()
        #
        buffered_lines = []  # local read buffer
        while self.running:
            line = self._readline()
            if line:
                buffered_lines.append((time.time(), line))
            if buffered_lines:
                #
                # make sure we access self.positions in
                # a threadsafe manner.
                # This will NOT block:
                # - If it can't write then it will leave
                #   readings in buffered_lines.
                # - If it can write then it will moved the
                #   buffered_lines into self.positions
                #   and clear the buffer.
                #
                if self.lock.acquire(blocking=False):
                    try:
                        self.lines += buffered_lines
                        buffered_lines = []
                    finally:
                        self.lock.release()
            time.sleep(0)  # give other threads time

    def shutdown(self):
        self.running = False
        self._close()


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--serial", type=str, required=True,
                        help="Serial port address, like '/dev/tty.usbmodem1411'")
    parser.add_argument("-b", "--baudrate", type=int, default=9600, help="Serial port baud rate.")
    parser.add_argument("-t", "--timeout", type=float, default=0.5, help="Serial port timeout in seconds.")
    parser.add_argument("-sp", '--samples', type=int, default=5, help="Number of samples per read cycle; 0 for unlimited.")
    parser.add_argument("-th", "--threaded", action='store_true', help="run in threaded mode.")
    parser.add_argument("-db", "--debug", action='store_true', help="Enable extra logging")
    args = parser.parse_args()

    if args.samples < 0:
        print("Samples per read cycle, greater than zero OR zero for unlimited")
        parser.print_help()
        sys.exit(0)

    if args.timeout <= 0:
        print("Timeout must be greater than zero")
        parser.print_help()
        sys.exit(0)

    update_thread = None
    reader = None

    try:
        serial_port = SerialPort(args.serial, baudrate=args.baudrate, timeout=args.timeout)
        line_reader = SerialLineReader(serial_port, max_lines=args.samples, debug=args.debug)

        #
        # start the threaded part
        # and a threaded window to show plot
        #
        if args.threaded:
            update_thread = threading.Thread(target=line_reader.update, args=())
            update_thread.start()


        def read_lines():
            return line_reader.run_threaded() if args.threaded else line_reader.run()

        while line_reader.running:
            readings = read_lines()
            if readings:
                # just log the readings
                for line in readings:
                    print(line)
    finally:
        if line_reader:
            line_reader.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end

