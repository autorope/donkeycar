import argparse
from functools import reduce
import operator
import threading
import time

# import pynmea2
import serial
import utm

class gps:
    def __init__(self, serial:str, baudrate:int = 9600, timeout:float = 0.5):
        self.serial = serial
        self.baudrate = baudrate
        self.timeout = timeout
        self.positions = []  # tuple of (timestamp, longitude, latitude)
        self.threaded = None
        self.gps = None
        self.lock = threading.Lock()
        self.running = True

    def clear(self):
        """
        Clear the positions buffer
        """
        with self.lock:
            self.positions = []

    def poll(self, gps, timestamp=None):
        #
        # read a line and convert to a position
        #
        if self.running and gps is not None:
            try:
                if timestamp is None:
                    timestamp = time.time()
                line = gps.readline().decode()
                position = getGpsPosition(line)
                if position:
                    # (timestamp, longitude latitude)
                    return (timestamp, position[0], position[1])
            except KeyboardInterrupt as e:
                self.running = False
                print("User shutdown, gps closed!")
                raise e
            except pynmea2.ParseError as e:
                print('Ignoring NMEA parse error: {}'.format(e))
            except Exception as e:
                print("Application error:" + str(e))
                self.running = False
        return None

    def run(self):
        if self.running:
            if self.threaded:
                return self.run_threaded()

            #
            # open the serial port in main thread
            #
            if not self.gps:
                self.gps = serial.Serial(self.serial, baudrate=self.baudrate, timeout=self.timeout)

            #
            # in non-threaded mode, just read a single reading and return it
            #
            if self.gps:
                position = self.poll(self.gps, time.time())
                if position:
                    # [(timestamp, longitude, latitude)]
                    return [position]

        return []


    def run_threaded(self):
        if not self.running:
            return []

        #
        # return the accumulated readings
        #
        with self.lock:
            positions = self.positions
            self.positions = []
            return positions


    def update(self):
        #
        # open serial port and run an infinite loop.
        # NOTE: this is NOT compatible with non-threaded run()
        #
        if self.running:
            if self.gps is not None:
                raise RuntimeError("Attempt to start threaded mode when non-threaded mode is in use.")
            self.threaded = True

            #
            # open the serial port in the thread
            # and read it continuously, moving
            # readings into self.positions list.
            # The last position in the list is the
            # most recent reading
            #
            with serial.Serial(self.serial, baudrate=self.baudrate, timeout=self.timeout) as gps:
                buffered_positions = []  # local read buffer
                while self.running:
                    position = self.poll(gps, time.time())
                    if position:
                        buffered_positions.append(position)
                    if buffered_positions:
                        #
                        # make sure we access self.positions in
                        # a threadsafe manner.
                        # This will NOT block:
                        # - If it can't write then it will leave
                        #   readings in buffered_positions.
                        # - If it can write then it will moved the
                        #   buffered_positions into self.positions
                        #   and clear the buffer.
                        #
                        if self.lock.acquire(blocking=False):
                            try:
                                self.positions += buffered_positions
                                buffered_positions = []
                            finally:
                                self.lock.release()
            self.threaded = False

    def shutdown(self):
        self.running = False
        if self.gps:
            self.gps.close()
            self.gps = None


def getGpsPosition(line):
    """
    Given a line emitted by a GPS module, 
    Parse out the position and return as a 
    tuple of float (longitude, latitude) as meters.
    If it cannot be parsed or is not a position message, 
    then return None.
    """
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
        
    #
    # must start with $ and end with checksum
    #
    if '$' != line[0]:
        print("Missing line start")
        return None
        
    if '*' != line[-3]:
        print("Missing checksum")
        return None
        
    nmea_checksum = parse_nmea_checksum(line) # ## checksum hex digits as int
    nmea_msg = line[1:-3]      # msg without $ and *## checksum
    nmea_parts = nmea_msg.split(",")
    message = nmea_parts[0]
    if (message == "GPRMC"):   
        #     
        # like '$GPRMC,003918.00,A,3806.92281,N,12235.64362,W,0.090,,060322,,,D*67'
        # GPRMC = Recommended minimum specific GPS/Transit data
        #
        # make sure the checksum checks out
        #
        calculated_checksum = calculate_nmea_checksum(line)
        if nmea_checksum != calculated_checksum:
            print(f"checksum does not match: {nmea_checksum} != {calculated_checksum}")
        
        #
        # parse against a known parser to check our parser
        # TODO: if we hit a lot of corner cases that cause our
        #       parser to fail, then switch over to the libarry.
        #       Conversely, if our parser works then use it as
        #       it is very lightweight.
        #
        # msg = pynmea2.parse(line)
        # print(f"nmea.longitude({msg.longitude}, nmea.latitude({msg.latitude})")
        
        # Reading the GPS fix data is an alternative approach that also works
        if nmea_parts[2] == 'V':
            # V = Warning, most likely, there are no satellites in view...
            print("GPS receiver warning")
        else:
            #
            # Convert the textual nmea position into degrees
            #
            longitude = nmea_to_degrees(nmea_parts[5], nmea_parts[6])
            latitude = nmea_to_degrees(nmea_parts[3], nmea_parts[4])
            # print(f"Your position: lon = ({longitude}), lat = ({latitude})")
            
            #
            # convert position in degrees to local meters
            #
            utm_position = utm.from_latlon(latitude, longitude)
            # print(f"Your utm position: lon - ({utm_position[1]:.6f}), lat = ({utm_position[0]:.6f})")
            
            # return (longitude, latitude) as float degrees
            return(utm_position[1], utm_position[0])
    else:
        # Non-position message OR invalid string
        # print(f"Ignoring line {line}")
        pass
    return None


def parse_nmea_checksum(nmea_line):
    """
    Given the complete nmea line (including starting '$' and ending checksum '*##')
    calculate the checksum from the body of the line.
    NOTE: this does not check for structural correctness, so you
          should check that '$' and '*##' checksum are present before
          calling this function.
    """
    return int(nmea_line[-2:], 16) # checksum hex digits as int
    
    
def calculate_nmea_checksum(nmea_line):
    """
    Given the complete nmea line (including starting '$' and ending checksum '*##')
    calculate the checksum from the body of the line.
    NOTE: this does not check for structural correctness, so you
          should check that '$' and '*##' checksum are present
          and that the checksum matches before calling this function.
    """
    # 
    # xor all characters in the message to get a one byte checksum.
    # don't include starting '$' or trailing checksum '*##'
    #
    return reduce(operator.xor, map(ord, nmea_line[1:-3]), 0)


def nmea_to_degrees(gps_str, direction):
    """
    Convert a gps coordinate string formatted as:
    DDMM.MMMMM, where DD denotes the degrees and MM.MMMMM denotes the minutes
    to a float in degrees.
    """
    if not gps_str or gps_str == "0":
        return 0
        
    #
    # pull out the degrees and minutes
    # and then combine the minutes
    #
    parts = gps_str.split(".")
    degrees_str = parts[0][:-2]
    minutes_str = parts[0][-2:]
    if 2 == len(parts):
        minutes_str += "." + parts[1]
    
    #
    # convert degrees to a float
    #
    degrees = 0.0
    if len(degrees_str) > 0:
        degrees = float(degrees_str)
    
    #
    # convert minutes a float in degrees
    #
    minutes = 0.0
    if len(minutes_str) > 0:
        minutes = float(minutes_str) / 60
        
    #
    # sum up the degrees and apply the direction as a sign
    #
    return (degrees + minutes) * (-1 if direction in ['W', 'S'] else 1)
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--serial", type=str, required=True, help="Serial port address, like '/dev/tty.usbmodem1411'")
    parser.add_argument("--baudrate", type=int, default=9600, help="Serial port baud rate")
    parser.add_argument("--timeout", type=float, default=0.5, help="Serial port timeout in seconds")
    parser.add_argument("-t", "--threaded", default=False, action='store_true', help = "run in threaded mode")
    args = parser.parse_args()

    update_thread = None
    gps_reader = None

    try:
        gps_reader = gps(args.serial, args.baudrate, args.timeout)

        #
        # start the threaded part
        # and a threaded window to show plot
        #
        if args.threaded:
            update_thread = threading.Thread(target=gps_reader.update, args=())
            update_thread.start()

        while gps_reader.running:
            readings = gps_reader.run_threaded() if args.threaded else gps_reader.run()
            if readings:
                print(readings)
    finally:
        if gps_reader:
            gps_reader.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end

