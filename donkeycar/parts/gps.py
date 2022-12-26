import argparse
from functools import reduce
import logging
import operator
import threading
import time

import pynmea2
import serial
import utm

from donkeycar.parts.serial_port import SerialPort
from donkeycar.parts.text_writer import CsvLogger

logger = logging.getLogger(__name__)


class GpsNmeaPositions:
    """
    Donkeycar part to convert array of NMEA sentences into array of (x,y) positions
    """
    def __init__(self, debug=False):
        self.debug = debug

    def run(self, lines):
        positions = []
        if lines:
            for ts, nmea in lines:
                position = parseGpsPosition(nmea, self.debug)
                if position:
                    # output (ts,x,y) - so long is x, lat is y
                    positions.append((ts, position[0], position[1]))
        return positions

    def update(self):
        pass

    def run_threaded(self, lines):
        return self.run(lines)

class GpsLatestPosition:
    """
    Return most recent valid GPS position
    """
    def __init__(self, debug=False):
        self.debug = debug
        self.position = None

    def run(self, positions):
        if positions is not None and len(positions) > 0:
            self.position = positions[-1]
        return self.position

class GpsPosition:
    """
    Donkeycar part to read NMEA lines from serial port and convert a position
    """
    def __init__(self, serial:SerialPort, debug = False) -> None:
        self.line_reader = SerialLineReader(serial)
        self.debug = debug
        self.position_reader = GpsNmeaPositions()
        self.position = None
        self._start()

    def _start(self):
        # wait until we get at least one gps position
        while self.position is None:
            logger.info("Waiting for gps fix")
            self.position = self.run()

    def run_once(self, lines):
        positions = self.GpsNmeaPositions.run(lines)
        if positions is not None and len(positions) > 0:
            self.position = positions[-1]
            if self.debug:
                logger.info(f"UTM long = {self.position[0]}, UTM lat = {self.position[1]}")
        return self.position

    def run(self):
        lines = line_reader.run()
        return self.run_once(lines)

    def run_threaded(self):
        lines = line_reader.run_threaded()
        return self.run_once(lines)

    def update(self):
        self.line_reader.update()

    def shutdown(self):
        return self.line_reader.shutdown()


class GpsPlayer:
    """
    Part that plays back the NMEA sentences that have been recorded
    by the nmea logger that is passed to the constructor.
    """
    def __init__(self, nmea_logger:CsvLogger):
        self.nmea = nmea_logger
        self.index = -1
        self.starttime = None
        self.running = False

    def start(self):
        self.running = True
        self.starttime = None  # will get set on first call to run()
        self.index = -1
        return self

    def stop(self):
        self.running = False
        return self

    def run(self, playing, nmea_sentences):
        """
        Play NMEA if running and in autopilot mode.
        Collect NMEA sentences within the time limit,
        arguments:
        - playing:bool True if we are to play recorded nmea,
                       False if we pass through given nmea
        - nmea_sentences:[str] list of live nmea from gps module
                                to pass through if not playing
        returns:
        - playing:bool True if playing, False if not
        - nmea:[str] the resulting sentences as a list
        """
        if self.running and playing:
            # if playing, then return the recorded nmea
            nmea = self.run_once(time.time())
            return True, nmea

        # if not playing, pass through the given nmea
        return False, nmea_sentences

    def run_once(self, now):
        """
        Collect all nmea sentences up to and including the given time
        """
        nmea_sentences = []
        if self.running:
            # reset start time if None
            if self.starttime is None:
                print("Resetting gps player start time.")
                self.starttime = now

            # get first nmea sentence so we can get it's recorded time
            start_nmea = self.nmea.get(0)
            if start_nmea is not None:
                #
                # get next nmea sentence and play it if
                # it is within time.
                # if there is no next sentence, then wrap
                # around back to first sentence
                #
                start_nmea_time = float(start_nmea[0])
                offset_nmea_time = 0
                within_time = True
                while within_time:
                    next_nmea = None
                    if self.index >= self.nmea.length():
                        # wrap around from end to start
                        self.index = 0
                        self.starttime += offset_nmea_time
                        next_nmea = self.nmea.get(0)
                    else:
                        next_nmea = self.nmea.get(self.index + 1)

                    if next_nmea is None:
                        self.index += 1  # skip the invalid nmea sentence
                    else:
                        next_nmea_time = float(next_nmea[0])
                        offset_nmea_time = (next_nmea_time - start_nmea_time)
                        next_nmea_time = self.starttime + offset_nmea_time
                        within_time = next_nmea_time <= now
                        if within_time:
                            nmea_sentences.append((next_nmea_time, next_nmea[1]))
                            self.index += 1
        return nmea_sentences


def parseGpsPosition(line, debug=False):
    """
    Given a line emitted by a GPS module, 
    Parse out the position and return as a 
    return: tuple of float (longitude, latitude) as meters.
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
        logger.info("NMEA Missing line start")
        return None
        
    if '*' != line[-3]:
        logger.info("NMEA Missing checksum")
        return None
        
    nmea_checksum = parse_nmea_checksum(line) # ## checksum hex digits as int
    nmea_msg = line[1:-3]      # msg without $ and *## checksum
    nmea_parts = nmea_msg.split(",")
    message = nmea_parts[0]
    if (message == "GPRMC") or (message == "GNRMC"):   
        #     
        # like '$GPRMC,003918.00,A,3806.92281,N,12235.64362,W,0.090,,060322,,,D*67'
        # GPRMC = Recommended minimum specific GPS/Transit data
        #
        # make sure the checksum checks out
        #
        calculated_checksum = calculate_nmea_checksum(line)
        if nmea_checksum != calculated_checksum:
            logger.info(f"NMEA checksum does not match: {nmea_checksum} != {calculated_checksum}")
            return None

        #
        # parse against a known parser to check our parser
        # TODO: if we hit a lot of corner cases that cause our
        #       parser to fail, then switch over to the libarry.
        #       Conversely, if our parser works then use it as
        #       it is very lightweight.
        #
        if debug:
            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError as e:
                logger.error('NMEA parse error detected: {}'.format(e))
                return None

        # Reading the GPS fix data is an alternative approach that also works
        if nmea_parts[2] == 'V':
            # V = Warning, most likely, there are no satellites in view...
            logger.info("GPS receiver warning; position not valid. Ignore invalid position.")
        else:
            #
            # Convert the textual nmea position into degrees
            #
            longitude = nmea_to_degrees(nmea_parts[5], nmea_parts[6])
            latitude = nmea_to_degrees(nmea_parts[3], nmea_parts[4])

            if debug:
                if msg.longitude != longitude:
                    print(f"Longitude mismatch {msg.longitude} != {longitude}")
                if msg.latitude != latitude:
                    print(f"Latitude mismatch {msg.latitude} != {latitude}")

            #
            # convert position in degrees to local meters
            #
            utm_position = utm.from_latlon(latitude, longitude)
            if debug:
                logger.info(f"UTM easting = {utm_position[0]}, UTM northing = {utm_position[1]}")
            
            # return (longitude, latitude) as float degrees
            return float(utm_position[0]), float(utm_position[1])
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
    DDDMM.MMMMM, where DDD denotes the degrees (which may have zero to 3 digits)
    and MM.MMMMM denotes the minutes
    to a float in degrees.
    """
    if not gps_str or gps_str == "0":
        return 0
        
    #
    # pull out the degrees and minutes
    # and then combine the minutes
    #
    parts = gps_str.split(".")
    degrees_str = parts[0][:-2]        # results in zero to 3 digits
    minutes_str = parts[0][-2:]        # always results in 2 digits
    if 2 == len(parts):
        minutes_str += "." + parts[1]  # combine whole and fractional minutes
    
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
    

#
# The __main__ self test can log position or optionally record a set of waypoints
#
if __name__ == "__main__":
    import math
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse
    import sys
    import readchar
    from donkeycar.parts.serial_port import SerialPort, SerialLineReader


    def stats(data):
        """
        Calculate (min, max, mean, std_deviation) of a list of floats
        """
        if not data:
            return None
        count = len(data)
        min = None
        max = None
        sum = 0
        for x in data:
            if min is None or x < min:
                min = x
            if max is None or x > max:
                max = x
            sum += x
        mean = sum / count
        sum_errors_squared = 0
        for x in data:
            error = x - mean
            sum_errors_squared += (error * error)
        std_deviation = math.sqrt(sum_errors_squared / count)
        return Stats(count, sum, min, max, mean, std_deviation)

    class Stats:
        """
        Statistics for a set of data
        """
        def __init__(self, count, sum, min, max, mean, std_deviation):
            self.count = count
            self.sum = sum
            self.min = min
            self.max = max
            self.mean = mean
            self.std_deviation = std_deviation

    class Waypoint:
        """
        A waypoint created from multiple samples,
        modelled as a non-axis-aligned (rotated) ellipsoid.
        This models a waypoint based on a jittery source,
        like GPS, where x and y values may not be completely
        independent values.
        """
        def __init__(self, samples, nstd = 1.0):
            """
            Fit an ellipsoid to the given samples at the
            given multiple of the standard deviation of the samples.
            """
            
            # separate out the points by axis
            self.x = [w[1] for w in samples]
            self.y = [w[2] for w in samples]
            
            # calculate the stats for each axis
            self.x_stats = stats(self.x)
            self.y_stats = stats(self.y)

            #
            # calculate a rotated ellipse that best fits the samples.
            # We use a rotated ellipse because the x and y values 
            # of each point are not independent.  
            # 
            def eigsorted(cov):
                """
                Calculate eigenvalues and eigenvectors
                and return them sorted by eigenvalue.
                """
                eigenvalues, eigenvectors = np.linalg.eigh(cov)
                order = eigenvalues.argsort()[::-1]
                return eigenvalues[order], eigenvectors[:, order]

            # calculate covariance matrix between x and y values
            self.cov = np.cov(self.x, self.y)

            # get eigenvalues and vectors from covariance matrix
            self.eigenvalues, self.eigenvectors = eigsorted(self.cov)

            # calculate the ellipsoid at the given multiple of the standard deviation.
            self.theta = np.degrees(np.arctan2(*self.eigenvectors[:, 0][::-1]))
            self.width, self.height = 2 * nstd * np.sqrt(self.eigenvalues)

        def is_inside(self, x, y):
            """
            Determine if the given (x,y) point is within the waypoint's
            fitted ellipsoid
            """
            # if (x >= self.x_stats.min) and (x <= self.x_stats.max):
            #     if (y >= self.y_stats.min) and (y <= self.y_stats.max):
            #         return True
            # return False
            # if (x >= (self.x_stats.mean - self.x_stats.std_deviation)) and (x <= (self.x_stats.mean + self.x_stats.std_deviation)):
            #     if (y >= (self.y_stats.mean - self.y_stats.std_deviation)) and (y <= (self.y_stats.mean + self.y_stats.std_deviation)):
            #         return True
            # return False
            cos_theta = math.cos(self.theta)
            sin_theta = math.sin(self.theta)
            x_translated = x - self.x_stats.mean
            y_translated = y - self.y_stats.mean
            #
            # basically translate the test point into the
            # coordinate system of the ellipse (it's center)
            # and then rotate the point and do a normal ellipse test
            #
            part1 = ((cos_theta * x_translated + sin_theta * y_translated) / self.width)**2
            part2 = ((sin_theta * x_translated - cos_theta * y_translated) / self.height)**2
            return (part1 + part2) <= 1

        def is_in_range(self, x, y):
            """
            Determine if the given (x,y) point is within the
            range of the collected waypoint samples
            """
            return (x >= self.x_stats.min) and \
                   (x <= self.x_stats.max) and \
                   (y >= self.y_stats.min) and \
                   (y <= self.y_stats.max)
            
        def is_in_std(self, x, y, std_multiple=1.0):
            """
            Determine if the given (x, y) point is within a given
            multiple of the standard deviation of the samples
            on each axis.
            """
            x_std = self.x_stats.std_deviation * std_multiple
            y_std = self.y_stats.std_deviation * std_multiple
            return (x >= (self.x_stats.mean - x_std)) and \
                   (x <= (self.x_stats.mean + x_std)) and \
                   (y >= (self.y_stats.mean - y_std)) and \
                   (y <= (self.y_stats.mean + y_std))

        def show(self):
            """
            Draw the waypoint ellipsoid
            """
            from matplotlib.patches import Ellipse
            import matplotlib.pyplot as plt
            ax = plt.subplot(111, aspect='equal')
            self.plot()
            plt.show()
            
        def plot(self):
            """
            Draw the waypoint ellipsoid
            """
            from matplotlib.patches import Ellipse, Rectangle
            import matplotlib.pyplot as plt
            #define Matplotlib figure and axis
            ax = plt.subplot(111, aspect='equal')
            
            # plot the collected readings
            plt.scatter(self.x, self.y)
            
            # plot the centroid
            plt.plot(self.x_stats.mean, self.y_stats.mean, marker="+", markeredgecolor="green", markerfacecolor="green")
            
            # plot the range
            bounds = Rectangle(
                (self.x_stats.min, self.y_stats.min), 
                self.x_stats.max - self.x_stats.min, 
                self.y_stats.max - self.y_stats.min,
                alpha=0.5,
                edgecolor='red',
                fill=False,
                visible=True)
            ax.add_artist(bounds)

            # plot the ellipsoid 
            ellipse = Ellipse(xy=(self.x_stats.mean, self.y_stats.mean),
                          width=self.width, height=self.height,
                          angle=self.theta)
            ellipse.set_alpha(0.25)
            ellipse.set_facecolor('green')
            ax.add_artist(ellipse)

    def is_in_waypoint_range(waypoints, x, y):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_in_range(x, y):
                return True, i
            i += 1
        return False, -1

    def is_in_waypoint_std(waypoints, x, y, std):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_in_std(x, y, std):
                return True, i
            i += 1
        return False, -1

    def is_in_waypoint(waypoints, x, y):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_inside(x, y):
                return True, i
            i += 1
        return False, -1


    def plot(waypoints):
        """
        Draw the waypoint ellipsoid
        """
        from matplotlib.patches import Ellipse
        import matplotlib.pyplot as plt
        ax = plt.subplot(111, aspect='equal')
        for waypoint in waypoints:
            waypoint.plot()
        plt.show()


    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--serial", type=str, required=True, help="Serial port address, like '/dev/tty.usbmodem1411'")
    parser.add_argument("-b", "--baudrate", type=int, default=9600, help="Serial port baud rate.")
    parser.add_argument("-t", "--timeout", type=float, default=0.5, help="Serial port timeout in seconds.")
    parser.add_argument("-sp", '--samples', type=int, default = 5, help = "Number of samples per waypoint.")
    parser.add_argument("-wp", "--waypoints", type=int, default = 0, help = "Number of waypoints to collect; > 0 to collect waypoints, 0 to just log position")
    parser.add_argument("-nstd", "--nstd", type=float, default=1.0, help="multiple of standard deviation for ellipse.")
    parser.add_argument("-th", "--threaded", action='store_true', help = "run in threaded mode.")
    parser.add_argument("-db", "--debug", action='store_true', help = "Enable extra logging")
    args = parser.parse_args()

    if args.waypoints < 0:
        print("Use waypoints > 0 to collect waypoints, use 0 waypoints to just log position")
        parser.print_help()
        sys.exit(0)

    if args.samples <= 0:
        print("Samples per waypoint must be greater than zero")
        parser.print_help()
        sys.exit(0)

    if args.nstd <= 0:
        print("Waypoint multiplier must be greater than zero")
        parser.print_help()
        sys.exit(0)

    if args.timeout <= 0:
        print("Timeout must be greater than zero")
        parser.print_help()
        sys.exit(0)

    update_thread = None
    line_reader = None

    waypoint_count = args.waypoints      # number of paypoints in the path
    samples_per_waypoint = args.samples  # number of readings per waypoint
    waypoints = []
    waypoint_samples = []

    try:
        serial_port = SerialPort(args.serial, baudrate=args.baudrate, timeout=args.timeout)
        line_reader = SerialLineReader(serial_port, max_lines=args.samples, debug=args.debug)
        position_reader = GpsNmeaPositions(args.debug)

        #
        # start the threaded part
        # and a threaded window to show plot
        #
        if args.threaded:
            update_thread = threading.Thread(target=line_reader.update, args=())
            update_thread.start()

        def read_gps():
            lines = line_reader.run_threaded() if args.threaded else line_reader.run()
            positions = position_reader.run(lines)
            return positions

        ts = time.time()
        state = "prompt" if waypoint_count > 0 else ""
        while line_reader.running:
            readings = read_gps()
            if readings:
                print("")
                if state == "prompt":
                    print(f"Move to waypoint #{len(waypoints)+1} and press the space bar and enter to start sampling or any other key to just start logging.")
                    state = "move"
                elif state == "move":
                    key_press = readchar.readchar()  # sys.stdin.read(1)
                    if key_press == ' ':
                        waypoint_samples = []
                        line_reader.clear()  # throw away buffered readings
                        state = "sampling"
                    else:
                        state = ""  # just start logging
                elif state == "sampling":
                    waypoint_samples += readings
                    count = len(waypoint_samples)
                    print(f"Collected {count} so far...")
                    if count > samples_per_waypoint:
                        print(f"...done.  Collected {count} samples for waypoint #{len(waypoints)+1}")
                        #
                        # model a waypoint as a rotated ellipsoid
                        # that represents a 95% confidence interval 
                        # around the points measured at the waypoint.
                        #
                        waypoint = Waypoint(waypoint_samples, nstd=args.nstd)
                        waypoints.append(waypoint)
                        if len(waypoints) < waypoint_count:
                            state = "prompt"
                        else:
                            state = "test_prompt"
                            if args.debug:
                                plot(waypoints)
                elif state == "test_prompt":
                    print("Waypoints are recorded.  Now walk around and see when you are in a waypoint.")
                    state = "test"
                elif state == "test":
                    for ts, x, y in readings:
                        print(f"Your position is ({x}, {y})")
                        hit, index = is_in_waypoint_range(waypoints, x, y)
                        if hit:
                            print(f"You are within the sample range of waypoint #{index + 1}")
                        std_deviation = 1.0
                        hit, index = is_in_waypoint_std(waypoints, x, y, std_deviation)
                        if hit:
                            print(f"You are within {std_deviation} standard deviations of the center of waypoint #{index + 1}")
                        hit, index = is_in_waypoint(waypoints, x, y)
                        if hit:
                            print(f"You are at waypoint's ellipse #{index + 1}")
                else:
                    # just log the readings
                    for position in readings:
                        ts, x, y = position
                        print(f"You are at ({x}, {y})")
            else:
                if time.time() > (ts + 0.5):
                    print(".", end="")
                    ts = time.time()
    finally:
        if line_reader:
            line_reader.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end

