#!/usr/bin/env python3
"""
Scripts to record a path by driving a donkey car
and using an autopilot to drive the recoded path.
Works with wheel encoders and/or Intel T265

Usage:
    manage.py (drive) [--js] [--log=INFO] [--camera=(single|stereo)]
 

Options:
    -h --help          Show this screen.
    --js               Use physical joystick.
    -f --file=<file>   A text file containing paths to tub files, one per line. Option may be used more than once.
    --meta=<key:value> Key/Value strings describing describing a piece of meta data about this drive. Option may be used more than once.

Starts in user mode.
- The user flow to 'train' a path.   
  - start "python manage.py drive" 
  - This starts in user mode; so user is in manual drive mode 
    driving records path waypoints.
  - drive to record a path; make the start and end close to each other.
  - if you don't like path, select the reset button and it will
    reset the origin _AND_ erase the path from memory.  MOve the
    vehicle back to where the physical origin is and start driving
    again to record a new path.
  - if you like the path, select the save button to save it. 
- The user flow for autopilot:  
  - record or load a path (select load button) 
  - select auto-pilot mode using joystick or web ui.  The
    vehicle will start trying to follow the recorded path.
  - switch back user model to stop autopilot.
  - to restart using the saved path; 
    - select reset button; this will erase path and reset origin 
    - select load button to load path
    - put the car back at the physical origin.


"""
from distutils.log import debug
import os
import logging

#
# import cv2 early to avoid issue with importing after tensorflow
# see https://github.com/opencv/opencv/issues/14884#issuecomment-599852128
#
import time

try:
    import cv2
except:
    pass


from docopt import docopt

import donkeycar as dk
from donkeycar.parts.controller import JoystickController
from donkeycar.parts.path import CsvThrottlePath, PathPlot, CTE, PID_Pilot, \
    PlotCircle, PImage, OriginOffset
from donkeycar.parts.transform import PIDController
from donkeycar.parts.kinematics import TwoWheelSteeringThrottle
from donkeycar.templates.complete import add_odometry, add_camera, \
    add_user_controller, add_drivetrain, add_simulator, add_imu, DriveMode, \
    UserPilotCondition, ToggleRecording
from donkeycar.parts.logger import LoggerPart
from donkeycar.parts.transform import Lambda
from donkeycar.parts.explode import ExplodeDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def drive(cfg, use_joystick=False, camera_type='single'):
    '''
    Construct a working robotic vehicle from many parts.
    Each part runs as a job in the Vehicle loop, calling either
    it's run or run_threaded method depending on the constructor flag
    `threaded`.  All parts are updated one after another at the framerate given
    in cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely
    manner. Parts may have named outputs and inputs. The framework handles
    passing named outputs to parts requesting the same named input.
    '''

    is_differential_drive = cfg.DRIVE_TRAIN_TYPE.startswith("DC_TWO_WHEEL")

    #Initialize car
    V = dk.vehicle.Vehicle()

    if cfg.HAVE_SOMBRERO:
        from donkeycar.utils import Sombrero
        s = Sombrero()
   
    #Initialize logging before anything else to allow console logging
    if cfg.HAVE_CONSOLE_LOGGING:
        logger.setLevel(logging.getLevelName(cfg.LOGGING_LEVEL))
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(cfg.LOGGING_FORMAT))
        logger.addHandler(ch)

    if cfg.HAVE_MQTT_TELEMETRY:
        from donkeycar.parts.telemetry import MqttTelemetry
        tel = MqttTelemetry(cfg)

    #
    # if we are using the simulator, set it up
    #
    add_simulator(V, cfg)

    #
    # IMU
    #
    add_imu(V, cfg)

    #
    # odometry/tachometer/speed control
    #
    if cfg.HAVE_ODOM:
        #
        # setup encoders, odometry and pose estimation
        #
        add_odometry(V, cfg)
    else:
        # we give the T265 no calib to indicated we don't have odom
        cfg.WHEEL_ODOM_CALIB = None

        #This dummy part to satisfy input needs of RS_T265 part.
        class NoOdom():
            def run(self):
                return 0.0

        V.add(NoOdom(), outputs=['enc/vel_m_s'])

    if cfg.HAVE_T265:
        from donkeycar.parts.realsense2 import RS_T265
        if cfg.HAVE_ODOM and not os.path.exists(cfg.WHEEL_ODOM_CALIB):
            print("You must supply a json file when using odom with T265. "
                  "There is a sample file in templates.")
            print("cp donkeycar/donkeycar/templates/calibration_odometry.json .")
            exit(1)

        #
        # NOTE: image output on the T265 is broken in the python API and
        #       will never get fixed, so not image output from T265
        #
        rs = RS_T265(image_output=False, calib_filename=cfg.WHEEL_ODOM_CALIB, device_id=cfg.REALSENSE_T265_ID)
        V.add(rs, inputs=['enc/vel_m_s'], outputs=['rs/pos', 'rs/vel', 'rs/acc'], threaded=True)

        #
        # Pull out the realsense T265 position stream, output 2d coordinates we can use to map.
        # Transform the T265 augmented reality coordinate system into a traditional
        # top-down POSE coordinate system where east is positive-x and north is positive-y.
        #
        class PosStream:
            def run(self, pos):
                #y is up, x is right, z is backwards/forwards (negative going forwards)
                return -pos.z, -pos.x

        V.add(PosStream(), inputs=['rs/pos'], outputs=['pos/x', 'pos/y'])

    #
    # gps outputs ['pos/x', 'pos/y']
    #
    gps_player = add_gps(V, cfg)

    #
    # setup primary camera
    #
    add_camera(V, cfg, camera_type)

    #
    # add the user input controller(s)
    # - this will add the web controller
    # - it will optionally add any configured 'joystick' controller
    #
    has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
    ctr = add_user_controller(V, cfg, use_joystick, input_image = 'map/image')

    #
    # explode the web buttons into their own key/values in memory
    #
    V.add(ExplodeDict(V.mem, "web/"), inputs=['web/buttons'])

    #
    # This part will reset the car back to the origin. You must put the car in the known origin
    # and push the cfg.RESET_ORIGIN_BTN on your controller. This will allow you to induce an offset
    # in the mapping.
    #
    origin_reset = OriginOffset(cfg.PATH_DEBUG)
    V.add(origin_reset, inputs=['pos/x', 'pos/y', 'cte/closest_pt'], outputs=['pos/x', 'pos/y', 'cte/closest_pt'])


    #
    # maintain run conditions for user mode and autopilot mode parts.
    #
    V.add(UserPilotCondition(),
          inputs=['user/mode', "cam/image_array", "cam/image_array"],
          outputs=['run_user', "run_pilot", "ui/image_array"])


    # This is the path object. It will record a path when distance changes and it travels
    # at least cfg.PATH_MIN_DIST meters. Except when we are in follow mode, see below...
    path = CsvThrottlePath(min_dist=cfg.PATH_MIN_DIST)
    V.add(path, inputs=['recording', 'pos/x', 'pos/y', 'user/throttle'], outputs=['path', 'throttles'])

    #
    # log pose
    #
    # if cfg.DONKEY_GYM:
    #     lpos = LoggerPart(inputs=['dist/left', 'dist/right', 'dist', 'pos/pos_x', 'pos/pos_y', 'yaw'], level="INFO", logger="simulator")
    #     V.add(lpos, inputs=lpos.inputs)
    # if cfg.HAVE_ODOM:
    #     if cfg.HAVE_ODOM_2:
    #         lpos = LoggerPart(inputs=['enc/left/distance', 'enc/right/distance', 'enc/left/timestamp', 'enc/right/timestamp'], level="INFO", logger="odometer")
    #         # V.add(lpos, inputs=lpos.inputs)
    #     lpos = LoggerPart(inputs=['enc/distance', 'enc/timestamp'], level="INFO", logger="odometer")
    #     V.add(lpos, inputs=lpos.inputs)
    #     lpos = LoggerPart(inputs=['pos/x', 'pos/y', 'pos/steering'], level="INFO", logger="kinematics")
    #     V.add(lpos, inputs=lpos.inputs)

    def save_path():
        if path.length() > 0:
            if path.save(cfg.PATH_FILENAME):
                print("That path was saved to ", cfg.PATH_FILENAME)

                # save any recorded gps readings
                if gps_player:
                    gps_player.nmea.save()
            else:
                print("The path could NOT be saved; check the PATH_FILENAME in myconfig.py to make sure it is a legal path")
        else:
            print("There is no path to save; try recording the path.")

    def load_path():
        if os.path.exists(cfg.PATH_FILENAME) and path.load(cfg.PATH_FILENAME):
           print("The path was loaded was loaded from ", cfg.PATH_FILENAME)

           # we loaded the path; also load any recorded gps readings
           if gps_player:
               gps_player.stop().nmea.load()
               gps_player.start()
        else:
           print("path _not_ loaded; make sure you have saved a path.")

    def erase_path():
        origin_reset.reset_origin()
        if path.reset():
            print("The origin and the path were reset; you are ready to record a new path.")
            if gps_player:
                gps_player.stop().nmea.reset()
        else:
            print("The origin was reset; you are ready to record a new path.")

    def reset_origin():
        """
        Reset effective pose to (0, 0)
        """
        origin_reset.reset_origin()
        print("The origin was reset to the current position.")

        # restart any recorded gps readings from the start.
        if gps_player:
            gps_player.start()


    # When a path is loaded, we will be in follow mode. We will not record.
    if os.path.exists(cfg.PATH_FILENAME):
        load_path()

    # Here's an image we can map to.
    img = PImage(clear_each_frame=True)
    V.add(img, outputs=['map/image'])

    # This PathPlot will draw path on the image

    plot = PathPlot(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET)
    V.add(plot, inputs=['map/image', 'path'], outputs=['map/image'])

    # This will use path and current position to output cross track error
    cte = CTE(look_ahead=cfg.PATH_LOOK_AHEAD, look_behind=cfg.PATH_LOOK_BEHIND, num_pts=cfg.PATH_SEARCH_LENGTH)
    V.add(cte, inputs=['path', 'pos/x', 'pos/y', 'cte/closest_pt'], outputs=['cte/error', 'cte/closest_pt'], run_condition='run_pilot')

    # This will use the cross track error and PID constants to try to steer back towards the path.
    pid = PIDController(p=cfg.PID_P, i=cfg.PID_I, d=cfg.PID_D)
    pilot = PID_Pilot(pid, cfg.PID_THROTTLE, cfg.USE_CONSTANT_THROTTLE, min_throttle=cfg.PID_THROTTLE)
    V.add(pilot, inputs=['cte/error', 'throttles', 'cte/closest_pt'], outputs=['pilot/steering', 'pilot/throttle'], run_condition="run_pilot")

    def dec_pid_d():
        pid.Kd -= cfg.PID_D_DELTA
        logging.info("pid: d- %f" % pid.Kd)

    def inc_pid_d():
        pid.Kd += cfg.PID_D_DELTA
        logging.info("pid: d+ %f" % pid.Kd)

    def dec_pid_p():
        pid.Kp -= cfg.PID_P_DELTA
        logging.info("pid: p- %f" % pid.Kp)

    def inc_pid_p():
        pid.Kp += cfg.PID_P_DELTA
        logging.info("pid: p+ %f" % pid.Kp)


    recording_control = ToggleRecording(cfg.AUTO_RECORD_ON_THROTTLE, cfg.RECORD_DURING_AI)
    V.add(recording_control, inputs=['user/mode', "recording"], outputs=["recording"])


    #
    # Add buttons for handling various user actions
    # The button names are in configuration.
    # They may refer to game controller (joystick) buttons OR web ui buttons
    #
    # There are 5 programmable webui buttons, "web/w1" to "web/w5"
    # adding a button handler for a webui button
    # is just adding a part with a run_condition set to
    # the button's name, so it runs when button is pressed.
    #
    have_joystick = ctr is not None and isinstance(ctr, JoystickController)

    # Here's a trigger to save the path. Complete one circuit of your course, when you
    # have exactly looped, or just shy of the loop, then save the path and shutdown
    # this process. Restart and the path will be loaded.
    if cfg.SAVE_PATH_BTN:
        print(f"Save path button is {cfg.SAVE_PATH_BTN}")
        if cfg.SAVE_PATH_BTN.startswith("web/w"):
            V.add(Lambda(lambda: save_path()), run_condition=cfg.SAVE_PATH_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.SAVE_PATH_BTN, save_path)

    # allow controller to (re)load the path
    if cfg.LOAD_PATH_BTN:
        print(f"Load path button is {cfg.LOAD_PATH_BTN}")
        if cfg.LOAD_PATH_BTN.startswith("web/w"):
            V.add(Lambda(lambda: load_path()), run_condition=cfg.LOAD_PATH_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.LOAD_PATH_BTN, load_path)

    # Here's a trigger to erase a previously saved path.
    # This erases the path in memory; it does NOT erase any saved path file
    if cfg.ERASE_PATH_BTN:
        print(f"Erase path button is {cfg.ERASE_PATH_BTN}")
        if cfg.ERASE_PATH_BTN.startswith("web/w"):
            V.add(Lambda(lambda: erase_path()), run_condition=cfg.ERASE_PATH_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.ERASE_PATH_BTN, erase_path)

    # Here's a trigger to reset the origin based on the current position
    if cfg.RESET_ORIGIN_BTN:
        print(f"Reset origin button is {cfg.RESET_ORIGIN_BTN}")
        if cfg.RESET_ORIGIN_BTN.startswith("web/w"):
            V.add(Lambda(lambda: reset_origin()), run_condition=cfg.RESET_ORIGIN_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.RESET_ORIGIN_BTN, reset_origin)

    # button to toggle recording
    if cfg.TOGGLE_RECORDING_BTN:
        print(f"Toggle recording button is {cfg.TOGGLE_RECORDING_BTN}")
        if cfg.TOGGLE_RECORDING_BTN.startswith("web/w"):
            V.add(Lambda(lambda: recording_control.toggle_recording()), run_condition=cfg.TOGGLE_RECORDING_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.TOGGLE_RECORDING_BTN, recording_control.toggle_recording)

    # Buttons to tune PID constants
    if cfg.DEC_PID_P_BTN and cfg.PID_P_DELTA:
        print(f"Decrement PID P button is {cfg.DEC_PID_P_BTN}")
        if cfg.DEC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(lambda: dec_pid_p()), run_condition=cfg.DEC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_P_BTN, dec_pid_p)
    if cfg.INC_PID_P_BTN and cfg.PID_P_DELTA:
        print(f"Increment PID P button is {cfg.INC_PID_P_BTN}")
        if cfg.INC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(lambda: inc_pid_p()), run_condition=cfg.INC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_P_BTN, inc_pid_p)
    if cfg.DEC_PID_D_BTN and cfg.PID_D_DELTA:
        print(f"Decrement PID D button is {cfg.DEC_PID_D_BTN}")
        if cfg.DEC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(lambda: dec_pid_d()), run_condition=cfg.DEC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_D_BTN, dec_pid_d)
    if cfg.INC_PID_D_BTN and cfg.PID_D_DELTA:
        print(f"Increment PID D button is {cfg.INC_PID_D_BTN}")
        if cfg.INC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(lambda: inc_pid_d()), run_condition=cfg.INC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_D_BTN, inc_pid_d)


    #
    # Decide what inputs should change the car's steering and throttle
    # based on the choice of user or autopilot drive mode
    #
    V.add(DriveMode(cfg.AI_THROTTLE_MULT),
          inputs=['user/mode', 'user/steering', 'user/throttle',
                  'pilot/steering', 'pilot/throttle'],
          outputs=['steering', 'throttle'])

    # V.add(LoggerPart(['user/mode', 'steering', 'throttle'], logger="drivemode"), inputs=['user/mode', 'steering', 'throttle'])

    #
    # To make differential drive steer,
    # divide throttle between motors based on the steering value
    #
    if is_differential_drive:
        V.add(TwoWheelSteeringThrottle(),
            inputs=['throttle', 'steering'],
            outputs=['left/throttle', 'right/throttle'])

    #
    # Setup drivetrain
    #
    add_drivetrain(V, cfg)


    #
    # OLED display setup
    #
    if cfg.USE_SSD1306_128_32:
        from donkeycar.parts.oled import OLEDPart
        auto_record_on_throttle = cfg.USE_JOYSTICK_AS_DEFAULT and cfg.AUTO_RECORD_ON_THROTTLE
        oled_part = OLEDPart(cfg.SSD1306_128_32_I2C_ROTATION, cfg.SSD1306_RESOLUTION, auto_record_on_throttle)
        V.add(oled_part, inputs=['recording', 'tub/num_records', 'user/mode'], outputs=[], threaded=True)


    # Print Joystick controls
    if ctr is not None and isinstance(ctr, JoystickController):
        ctr.print_controls()

    #
    # draw a map image as the vehicle moves
    #
    loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = "blue")
    V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'], run_condition='run_pilot')

    loc_plot = PlotCircle(scale=cfg.PATH_SCALE, offset=cfg.PATH_OFFSET, color = "green")
    V.add(loc_plot, inputs=['map/image', 'pos/x', 'pos/y'], outputs=['map/image'], run_condition='run_user')


    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, 
        max_loop_count=cfg.MAX_LOOPS)


def add_gps(V, cfg):
    if cfg.HAVE_GPS:
        from donkeycar.parts.serial_port import SerialPort, SerialLineReader
        from donkeycar.parts.gps import GpsNmeaPositions, GpsLatestPosition, GpsPlayer
        from donkeycar.parts.pipe import Pipe
        from donkeycar.parts.text_writer import CsvLogger

        #
        # parts to
        # - read nmea lines from serial port
        # - OR play from recorded file
        # - convert nmea lines to positions
        # - retrieve the most recent position
        #
        serial_port = SerialPort(cfg.GPS_SERIAL, cfg.GPS_SERIAL_BAUDRATE)
        nmea_reader = SerialLineReader(serial_port)
        V.add(nmea_reader, outputs=['gps/nmea'], threaded=True)

        # part to save nmea sentences for later playback
        nmea_player = None
        if cfg.GPS_NMEA_PATH:
            nmea_writer = CsvLogger(cfg.GPS_NMEA_PATH, separator='\t', field_count=2)
            V.add(nmea_writer, inputs=['recording', 'gps/nmea'], outputs=['gps/recorded/nmea'])  # only record nmea sentences in user mode
            nmea_player = GpsPlayer(nmea_writer)
            V.add(nmea_player, inputs=['run_pilot', 'gps/nmea'], outputs=['gps/playing', 'gps/nmea'])  # only play nmea sentences in autopilot mode

        gps_positions = GpsNmeaPositions(debug=cfg.GPS_DEBUG)
        V.add(gps_positions, inputs=['gps/nmea'], outputs=['gps/positions'])
        gps_latest_position = GpsLatestPosition(debug=cfg.GPS_DEBUG)
        V.add(gps_latest_position, inputs=['gps/positions'], outputs=['gps/timestamp', 'gps/utm/longitude', 'gps/utm/latitude'])

        # rename gps utm position to pose values
        V.add(Pipe(), inputs=['gps/utm/longitude', 'gps/utm/latitude'], outputs=['pos/x', 'pos/y'])

        return nmea_player


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    log_level = args['--log'] or "INFO"
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)


    if args['drive']:
        drive(cfg, use_joystick=args['--js'], camera_type=args['--camera'])
