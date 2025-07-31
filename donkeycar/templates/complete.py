#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car

Usage:
    manage.py (drive) [--model=<model>] [--js] [--type=(linear|categorical)] [--camera=(single|stereo)] [--meta=<key:value> ...] [--myconfig=<filename>]
    manage.py (train) [--tubs=tubs] (--model=<model>) [--type=(linear|inferred|tensorrt_linear|tflite_linear)]

Options:
    -h --help               Show this screen.
    --js                    Use physical joystick.
    -f --file=<file>        A text file containing paths to tub files, one per line. Option may be used more than once.
    --meta=<key:value>      Key/Value strings describing describing a piece of meta data about this drive. Option may be used more than once.
    --myconfig=filename     Specify myconfig file to use. 
                            [default: myconfig.py]
"""
from docopt import docopt

#
# import cv2 early to avoid issue with importing after tensorflow
# see https://github.com/opencv/opencv/issues/14884#issuecomment-599852128
#
try:
    import cv2
except:
    pass


import donkeycar as dk
from donkeycar.parts.transform import TriggeredCallback, DelayedTrigger
from donkeycar.parts.tub_v2 import TubWriter
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.controller import LocalWebController, WebFpv, JoystickController
from donkeycar.parts.throttle_filter import ThrottleFilter
from donkeycar.parts.behavior import BehaviorPart
from donkeycar.parts.file_watcher import FileWatcher
from donkeycar.parts.launch import AiLaunch
from donkeycar.parts.kinematics import NormalizeSteeringAngle, UnnormalizeSteeringAngle, TwoWheelSteeringThrottle
from donkeycar.parts.kinematics import Unicycle, InverseUnicycle, UnicycleUnnormalizeAngularVelocity
from donkeycar.parts.kinematics import Bicycle, InverseBicycle, BicycleUnnormalizeAngularVelocity
from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.transform import Lambda
from donkeycar.parts.pipe import Pipe
from donkeycar.utils import *

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def drive(cfg, model_path=None, use_joystick=False, model_type=None,
          camera_type='single', meta=[]):
    """
    Construct a working robotic vehicle from many parts. Each part runs as a
    job in the Vehicle loop, calling either it's run or run_threaded method
    depending on the constructor flag `threaded`. All parts are updated one
    after another at the framerate given in cfg.DRIVE_LOOP_HZ assuming each
    part finishes processing in a timely manner. Parts may have named outputs
    and inputs. The framework handles passing named outputs to parts
    requesting the same named input.
    """
    logger.info(f'PID: {os.getpid()}')
    if cfg.DONKEY_GYM:
        #the simulator will use cuda and then we usually run out of resources
        #if we also try to use cuda. so disable for donkey_gym.
        os.environ["CUDA_VISIBLE_DEVICES"]="-1"

    if model_type is None:
        if cfg.TRAIN_LOCALIZER:
            model_type = "localizer"
        elif cfg.TRAIN_BEHAVIORS:
            model_type = "behavior"
        else:
            model_type = cfg.DEFAULT_MODEL_TYPE

    # Initialize car
    V = dk.vehicle.Vehicle()

    # Initialize logging before anything else to allow console logging
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
    # setup encoders, odometry and pose estimation
    #
    add_odometry(V, cfg)


    #
    # setup primary camera
    #
    add_camera(V, cfg, camera_type)


    # add lidar
    if cfg.USE_LIDAR:
        from donkeycar.parts.lidar import RPLidar
        if cfg.LIDAR_TYPE == 'RP':
            print("adding RP lidar part")
            lidar = RPLidar(lower_limit = cfg.LIDAR_LOWER_LIMIT, upper_limit = cfg.LIDAR_UPPER_LIMIT)
            V.add(lidar, inputs=[],outputs=['lidar/dist_array'], threaded=True)
        if cfg.LIDAR_TYPE == 'YD':
            print("YD Lidar not yet supported")

    if cfg.HAVE_TFMINI:
        from donkeycar.parts.tfmini import TFMini
        lidar = TFMini(port=cfg.TFMINI_SERIAL_PORT)
        V.add(lidar, inputs=[], outputs=['lidar/dist'], threaded=True)

    if cfg.SHOW_FPS:
        from donkeycar.parts.fps import FrequencyLogger
        V.add(FrequencyLogger(cfg.FPS_DEBUG_INTERVAL),
              outputs=["fps/current", "fps/fps_list"])

    #
    # add the user input controller(s)
    # - this will add the web controller
    # - it will optionally add any configured 'joystick' controller
    #
    has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
    ctr = add_user_controller(V, cfg, use_joystick)

    #
    # convert 'user/steering' to 'user/angle' to be backward compatible with deep learning data
    #
    V.add(Pipe(), inputs=['user/steering'], outputs=['user/angle'])

    #
    # explode the buttons input map into individual output key/values in memory
    #
    V.add(ExplodeDict(V.mem, "web/"), inputs=['web/buttons'])

    #
    # For example: adding a button handler is just adding a part with a run_condition
    # set to the button's name, so it runs when button is pressed.
    #
    V.add(Lambda(lambda v: print(f"web/w1 clicked")), inputs=["web/w1"], run_condition="web/w1")
    V.add(Lambda(lambda v: print(f"web/w2 clicked")), inputs=["web/w2"], run_condition="web/w2")
    V.add(Lambda(lambda v: print(f"web/w3 clicked")), inputs=["web/w3"], run_condition="web/w3")
    V.add(Lambda(lambda v: print(f"web/w4 clicked")), inputs=["web/w4"], run_condition="web/w4")
    V.add(Lambda(lambda v: print(f"web/w5 clicked")), inputs=["web/w5"], run_condition="web/w5")

    #this throttle filter will allow one tap back for esc reverse
    th_filter = ThrottleFilter()
    V.add(th_filter, inputs=['user/throttle'], outputs=['user/throttle'])

    #
    # maintain run conditions for user mode and autopilot mode parts.
    #
    V.add(UserPilotCondition(show_pilot_image=getattr(cfg, 'SHOW_PILOT_IMAGE', False)),
          inputs=['user/mode', "cam/image_array", "cam/image_array_trans"],
          outputs=['run_user', "run_pilot", "ui/image_array"])

    class LedConditionLogic:
        def __init__(self, cfg):
            self.cfg = cfg

        def run(self, mode, recording, recording_alert, behavior_state, model_file_changed, track_loc):
            #returns a blink rate. 0 for off. -1 for on. positive for rate.

            if track_loc is not None:
                led.set_rgb(*self.cfg.LOC_COLORS[track_loc])
                return -1

            if model_file_changed:
                led.set_rgb(self.cfg.MODEL_RELOADED_LED_R, self.cfg.MODEL_RELOADED_LED_G, self.cfg.MODEL_RELOADED_LED_B)
                return 0.1
            else:
                led.set_rgb(self.cfg.LED_R, self.cfg.LED_G, self.cfg.LED_B)

            if recording_alert:
                led.set_rgb(*recording_alert)
                return self.cfg.REC_COUNT_ALERT_BLINK_RATE
            else:
                led.set_rgb(self.cfg.LED_R, self.cfg.LED_G, self.cfg.LED_B)

            if behavior_state is not None and model_type == 'behavior':
                r, g, b = self.cfg.BEHAVIOR_LED_COLORS[behavior_state]
                led.set_rgb(r, g, b)
                return -1 #solid on

            if recording:
                return -1 #solid on
            elif mode == 'user':
                return 1
            elif mode == 'local_angle':
                return 0.5
            elif mode == 'local':
                return 0.1
            return 0

    if cfg.HAVE_RGB_LED and not cfg.DONKEY_GYM:
        from donkeycar.parts.led_status import RGB_LED
        led = RGB_LED(cfg.LED_PIN_R, cfg.LED_PIN_G, cfg.LED_PIN_B, cfg.LED_INVERT)
        led.set_rgb(cfg.LED_R, cfg.LED_G, cfg.LED_B)

        V.add(LedConditionLogic(cfg), inputs=['user/mode', 'recording', "records/alert", 'behavior/state', 'modelfile/modified', "pilot/loc"],
              outputs=['led/blink_rate'])

        V.add(led, inputs=['led/blink_rate'])

    def get_record_alert_color(num_records):
        col = (0, 0, 0)
        for count, color in cfg.RECORD_ALERT_COLOR_ARR:
            if num_records >= count:
                col = color
        return col

    class RecordTracker:
        def __init__(self):
            self.last_num_rec_print = 0
            self.dur_alert = 0
            self.force_alert = 0

        def run(self, num_records):
            if num_records is None:
                return 0

            if self.last_num_rec_print != num_records or self.force_alert:
                self.last_num_rec_print = num_records

                if num_records % 10 == 0:
                    print("recorded", num_records, "records")

                if num_records % cfg.REC_COUNT_ALERT == 0 or self.force_alert:
                    self.dur_alert = num_records // cfg.REC_COUNT_ALERT * cfg.REC_COUNT_ALERT_CYC
                    self.force_alert = 0

            if self.dur_alert > 0:
                self.dur_alert -= 1

            if self.dur_alert != 0:
                return get_record_alert_color(num_records)

            return 0

    rec_tracker_part = RecordTracker()
    V.add(rec_tracker_part, inputs=["tub/num_records"], outputs=['records/alert'])

    if cfg.AUTO_RECORD_ON_THROTTLE:
        def show_record_count_status():
            rec_tracker_part.last_num_rec_print = 0
            rec_tracker_part.force_alert = 1
        if (cfg.CONTROLLER_TYPE != "pigpio_rc") and (cfg.CONTROLLER_TYPE != "MM1"):  # these controllers don't use the joystick class
            if isinstance(ctr, JoystickController):
                ctr.set_button_down_trigger('circle', show_record_count_status) #then we are not using the circle button. hijack that to force a record count indication
        else:
            
            show_record_count_status()

    #Sombrero
    if cfg.HAVE_SOMBRERO:
        from donkeycar.parts.sombrero import Sombrero
        s = Sombrero()

    #IMU
    add_imu(V, cfg)


    # Use the FPV preview, which will show the cropped image output, or the full frame.
    if cfg.USE_FPV:
        V.add(WebFpv(), inputs=['cam/image_array'], threaded=True)

    def load_model(kl, model_path):
        start = time.time()
        print('loading model', model_path)
        kl.load(model_path)
        print('finished loading in %s sec.' % (str(time.time() - start)) )

    def load_weights(kl, weights_path):
        start = time.time()
        try:
            print('loading model weights', weights_path)
            kl.model.load_weights(weights_path)
            print('finished loading in %s sec.' % (str(time.time() - start)) )
        except Exception as e:
            print(e)
            print('ERR>> problems loading weights', weights_path)

    def load_model_json(kl, json_fnm):
        start = time.time()
        print('loading model json', json_fnm)
        from tensorflow.python import keras
        try:
            with open(json_fnm, 'r') as handle:
                contents = handle.read()
                kl.model = keras.models.model_from_json(contents)
            print('finished loading json in %s sec.' % (str(time.time() - start)) )
        except Exception as e:
            print(e)
            print("ERR>> problems loading model json", json_fnm)

    #
    # load and configure model for inference
    #
    if model_path:
        # If we have a model, create an appropriate Keras part
        kl = dk.utils.get_model_by_type(model_type, cfg)

        #
        # get callback function to reload the model
        # for the configured model format
        #
        model_reload_cb = None
        if '.h5' in model_path or '.trt' in model_path or '.tflite' in \
            model_path or '.savedmodel' in model_path or '.pth' in model_path:
            # load the whole model with weigths, etc
            load_model(kl, model_path)

            def reload_model(filename):
                load_model(kl, filename)

            model_reload_cb = reload_model

        elif '.json' in model_path:
            # when we have a .json extension
            # load the model from there and look for a matching
            # .wts file with just weights
            load_model_json(kl, model_path)
            weights_path = model_path.replace('.json', '.weights')
            load_weights(kl, weights_path)

            def reload_weights(filename):
                weights_path = filename.replace('.json', '.weights')
                load_weights(kl, weights_path)

            model_reload_cb = reload_weights

        else:
            print("ERR>> Unknown extension type on model file!!")
            return

        # this part will signal visual LED, if connected
        V.add(FileWatcher(model_path, verbose=True),
              outputs=['modelfile/modified'])

        # these parts will reload the model file, but only when ai is running
        # so we don't interrupt user driving
        V.add(FileWatcher(model_path), outputs=['modelfile/dirty'],
              run_condition="run_pilot")
        V.add(DelayedTrigger(100), inputs=['modelfile/dirty'],
              outputs=['modelfile/reload'], run_condition="run_pilot")
        V.add(TriggeredCallback(model_path, model_reload_cb),
              inputs=["modelfile/reload"], run_condition="run_pilot")

        #
        # collect inputs to model for inference
        #
        if cfg.TRAIN_BEHAVIORS:
            bh = BehaviorPart(cfg.BEHAVIOR_LIST)
            V.add(bh, outputs=['behavior/state', 'behavior/label', "behavior/one_hot_state_array"])
            try:
                ctr.set_button_down_trigger('L1', bh.increment_state)
            except:
                pass

            inputs = ['cam/image_array', "behavior/one_hot_state_array"]

        elif cfg.USE_LIDAR:
            inputs = ['cam/image_array', 'lidar/dist_array']

        elif cfg.HAVE_ODOM:
            inputs = ['cam/image_array', 'enc/speed']

        elif model_type == "imu":
            assert cfg.HAVE_IMU, 'Missing imu parameter in config'

            class Vectorizer:
                def run(self, *components):
                    return components

            V.add(Vectorizer, inputs=['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
                                      'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z'],
                  outputs=['imu_array'])

            inputs = ['cam/image_array', 'imu_array']
        else:
            inputs = ['cam/image_array']

        #
        # collect model inference outputs
        #
        outputs = ['pilot/angle', 'pilot/throttle']

        if cfg.TRAIN_LOCALIZER:
            outputs.append("pilot/loc")

        #
        # Add image transformations like crop or trapezoidal mask
        # so they get applied at inference time in autopilot mode.
        #
        if hasattr(cfg, 'TRANSFORMATIONS') or hasattr(cfg, 'POST_TRANSFORMATIONS'):
            from donkeycar.parts.image_transformations import ImageTransformations
            #
            # add the complete set of pre and post augmentation transformations
            #
            logger.info(f"Adding inference transformations")
            V.add(ImageTransformations(cfg, 'TRANSFORMATIONS',
                                       'POST_TRANSFORMATIONS'),
                  inputs=['cam/image_array'], outputs=['cam/image_array_trans'])
            inputs = ['cam/image_array_trans'] + inputs[1:]

        V.add(kl, inputs=inputs, outputs=outputs, run_condition='run_pilot')

    #
    # stop at a stop sign
    #
    if cfg.STOP_SIGN_DETECTOR:
        from donkeycar.parts.object_detector.stop_sign_detector \
            import StopSignDetector
        V.add(StopSignDetector(cfg.STOP_SIGN_MIN_SCORE,
                               cfg.STOP_SIGN_SHOW_BOUNDING_BOX,
                               cfg.STOP_SIGN_MAX_REVERSE_COUNT,
                               cfg.STOP_SIGN_REVERSE_THROTTLE),
              inputs=['cam/image_array', 'pilot/throttle'],
              outputs=['pilot/throttle', 'cam/image_array'])
        V.add(ThrottleFilter(), 
              inputs=['pilot/throttle'],
              outputs=['pilot/throttle'])

    #
    # to give the car a boost when starting ai mode in a race.
    # This will also override the stop sign detector so that
    # you can start at a stop sign using launch mode, but
    # will stop when it comes to the stop sign the next time.
    #
    # NOTE: when launch throttle is in effect, pilot speed is set to None
    #
    aiLauncher = AiLaunch(cfg.AI_LAUNCH_DURATION, cfg.AI_LAUNCH_THROTTLE, cfg.AI_LAUNCH_KEEP_ENABLED)
    V.add(aiLauncher,
          inputs=['user/mode', 'pilot/throttle'],
          outputs=['pilot/throttle'])

    #
    # Decide what inputs should change the car's steering and throttle
    # based on the choice of user or autopilot drive mode
    #
    V.add(DriveMode(cfg.AI_THROTTLE_MULT),
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'],
          outputs=['steering', 'throttle'])


    if (cfg.CONTROLLER_TYPE != "pigpio_rc") and (cfg.CONTROLLER_TYPE != "MM1"):
        if isinstance(ctr, JoystickController):
            ctr.set_button_down_trigger(cfg.AI_LAUNCH_ENABLE_BUTTON, aiLauncher.enable_ai_launch)


    # Ai Recording
    recording_control = ToggleRecording(cfg.AUTO_RECORD_ON_THROTTLE, cfg.RECORD_DURING_AI)
    V.add(recording_control, inputs=['user/mode', "recording"], outputs=["recording"])

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

    #
    # add tub to save data
    #
    if cfg.USE_LIDAR:
        inputs = ['cam/image_array', 'lidar/dist_array', 'user/angle', 'user/throttle', 'user/mode']
        types = ['image_array', 'nparray','float', 'float', 'str']
    else:
        inputs=['cam/image_array','user/angle', 'user/throttle', 'user/mode']
        types=['image_array','float', 'float','str']

    if cfg.HAVE_ODOM:
        inputs += ['enc/speed']
        types += ['float']

    if cfg.TRAIN_BEHAVIORS:
        inputs += ['behavior/state', 'behavior/label', "behavior/one_hot_state_array"]
        types += ['int', 'str', 'vector']

    if cfg.CAMERA_TYPE == "D435" and cfg.REALSENSE_D435_DEPTH:
        inputs += ['cam/depth_array']
        types += ['gray16_array']

    if cfg.CAMERA_TYPE == "OAKD" and cfg.OAKD_DEPTH:
        inputs += ['cam/depth_array']
        types += ['gray16_array']

    if cfg.HAVE_IMU or (cfg.CAMERA_TYPE == "D435" and cfg.REALSENSE_D435_IMU):
        inputs += ['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z']

        types +=['float', 'float', 'float',
           'float', 'float', 'float']

    # rbx
    if cfg.DONKEY_GYM:
        if cfg.SIM_RECORD_LOCATION:
            inputs += ['pos/pos_x', 'pos/pos_y', 'pos/pos_z', 'pos/speed', 'pos/cte']
            types  += ['float', 'float', 'float', 'float', 'float']
        if cfg.SIM_RECORD_GYROACCEL:
            inputs += ['gyro/gyro_x', 'gyro/gyro_y', 'gyro/gyro_z', 'accel/accel_x', 'accel/accel_y', 'accel/accel_z']
            types  += ['float', 'float', 'float', 'float', 'float', 'float']
        if cfg.SIM_RECORD_VELOCITY:
            inputs += ['vel/vel_x', 'vel/vel_y', 'vel/vel_z']
            types  += ['float', 'float', 'float']
        if cfg.SIM_RECORD_LIDAR:
            inputs += ['lidar/dist_array']
            types  += ['nparray']

    if cfg.RECORD_DURING_AI:
        inputs += ['pilot/angle', 'pilot/throttle']
        types += ['float', 'float']

    if cfg.HAVE_PERFMON:
        from donkeycar.parts.perfmon import PerfMonitor
        mon = PerfMonitor(cfg)
        perfmon_outputs = ['perf/cpu', 'perf/mem', 'perf/freq']
        inputs += perfmon_outputs
        types += ['float', 'float', 'float']
        V.add(mon, inputs=[], outputs=perfmon_outputs, threaded=True)

    #
    # Create data storage part
    #
    tub_path = TubHandler(path=cfg.DATA_PATH).create_tub_path() if \
        cfg.AUTO_CREATE_NEW_TUB else cfg.DATA_PATH
    meta += getattr(cfg, 'METADATA', [])
    tub_writer = TubWriter(tub_path, inputs=inputs, types=types, metadata=meta)
    V.add(tub_writer, inputs=inputs, outputs=["tub/num_records"], run_condition='recording')

    # Telemetry (we add the same metrics added to the TubHandler
    if cfg.HAVE_MQTT_TELEMETRY:
        from donkeycar.parts.telemetry import MqttTelemetry
        tel = MqttTelemetry(cfg)
        telem_inputs, _ = tel.add_step_inputs(inputs, types)
        V.add(tel, inputs=telem_inputs, outputs=["tub/queue_size"], threaded=True)

    if cfg.PUB_CAMERA_IMAGES:
        from donkeycar.parts.network import TCPServeValue
        from donkeycar.parts.image import ImgArrToJpg
        pub = TCPServeValue("camera")
        V.add(ImgArrToJpg(), inputs=['cam/image_array'], outputs=['jpg/bin'])
        V.add(pub, inputs=['jpg/bin'])


    if cfg.DONKEY_GYM:
        print("You can now go to http://localhost:%d to drive your car." % cfg.WEB_CONTROL_PORT)
    else:
        print("You can now go to <your hostname.local>:%d to drive your car." % cfg.WEB_CONTROL_PORT)
    if has_input_controller:
        print("You can now move your controller to drive your car.")
        if isinstance(ctr, JoystickController):
            ctr.set_tub(tub_writer.tub)
            ctr.print_controls()

    # run the vehicle
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=cfg.MAX_LOOPS)


class ToggleRecording:
    def __init__(self, auto_record_on_throttle, record_in_autopilot):
        """
        Donkeycar Part that manages the recording state.
        """
        self.auto_record_on_throttle = auto_record_on_throttle
        self.record_in_autopilot = record_in_autopilot
        self.recording_latch: bool = None
        self.toggle_latch: bool = False
        self.last_recording = None

    def set_recording(self, recording: bool):
        """
        Set latched recording value to be applied on next call to run()
        :param recording: True to record, False to not record
        """
        self.recording_latch = recording

    def toggle_recording(self):
        """
        Force toggle of recording state on next call to run()
        """
        self.toggle_latch = True

    def run(self, mode: str, recording: bool):
        """
        Set recording based on user/autopilot mode
        :param mode: 'user'|'local_angle'|'local_pilot'
        :param recording: current recording flag
        :return: updated recording flag
        """
        recording_in = recording
        if recording_in != self.last_recording:
            logging.info(f"Recording Change = {recording_in}")

        if self.toggle_latch:
            if self.auto_record_on_throttle:
                logger.info(
                    'auto record on throttle is enabled; ignoring toggle of manual mode.')
            else:
                recording = not self.last_recording
            self.toggle_latch = False

        if self.recording_latch is not None:
            recording = self.recording_latch
            self.recording_latch = None

        if recording and mode != 'user' and not self.record_in_autopilot:
            logging.info("Ignoring recording in auto-pilot mode")
            recording = False

        if self.last_recording != recording:
            logging.info(f"Setting Recording = {recording}")

        self.last_recording = recording

        return recording


class DriveMode:
    def __init__(self, ai_throttle_mult=1.0):
        """
        :param ai_throttle_mult: scale throttle in autopilot mode
        """
        self.ai_throttle_mult = ai_throttle_mult

    def run(self, mode,
            user_steering, user_throttle,
            pilot_steering, pilot_throttle):
        """
        Main final steering and throttle values based on user mode
        :param mode: 'user'|'local_angle'|'local_pilot'
        :param user_steering: steering value in user (manual) mode
        :param user_throttle: throttle value in user (manual) mode
        :param pilot_steering: steering value in autopilot mode
        :param pilot_throttle: throttle value in autopilot mode
        :return: tuple of (steering, throttle) where throttle is
                 scaled by ai_throttle_mult in autopilot mode
        """
        if mode == 'user':
            return user_steering, user_throttle
        elif mode == 'local_angle':
            return pilot_steering if pilot_steering else 0.0, user_throttle
        return (pilot_steering if pilot_steering else 0.0,
               pilot_throttle * self.ai_throttle_mult if pilot_throttle else 0.0)


class UserPilotCondition:
    def __init__(self, show_pilot_image:bool = False) -> None:
        """
        :param show_pilot_image:bool True to show pilot image in pilot mode
                                     False to show user image in pilot mode
        """
        self.show_pilot_image = show_pilot_image

    def run(self, mode, user_image, pilot_image):
        """
        Maintain run condition and which image to show in web ui
        :param mode: 'user'|'local_angle'|'local_pilot'
        :param user_image: image to show in manual (user) pilot
        :param pilot_image: image to show in auto pilot
        :return: tuple of (user-condition, autopilot-condition, web image)
        """
        if mode == 'user':
            return True, False, user_image
        else:
            return False, True, pilot_image if self.show_pilot_image else user_image


def add_user_controller(V, cfg, use_joystick, input_image='ui/image_array'):
    """
    Add the web controller and any other
    configured user input controller.
    :param V: the vehicle pipeline.
              On output this will be modified.
    :param cfg: the configuration (from myconfig.py)
    :return: the controller
    """

    #
    # This web controller will create a web server that is capable
    # of managing steering, throttle, and modes, and more.
    #
    ctr = LocalWebController(port=cfg.WEB_CONTROL_PORT, mode=cfg.WEB_INIT_MODE)
    V.add(ctr,
          inputs=[input_image, 'tub/num_records', 'user/mode', 'recording'],
          outputs=['user/steering', 'user/throttle', 'user/mode', 'recording', 'web/buttons'],
          threaded=True)

    #
    # also add a physical controller if one is configured
    #
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        #
        # RC controller
        #
        if cfg.CONTROLLER_TYPE == "pigpio_rc":  # an RC controllers read by GPIO pins. They typically don't have buttons
            from donkeycar.parts.controller import RCReceiver
            ctr = RCReceiver(cfg)
            V.add(
                ctr,
                inputs=['user/mode', 'recording'],
                outputs=['user/steering', 'user/throttle',
                         'user/mode', 'recording'],
                threaded=False)
        else:
            #
            # custom game controller mapping created with
            # `donkey createjs` command
            #
            if cfg.CONTROLLER_TYPE == "custom":  # custom controller created with `donkey createjs` command
                from my_joystick import MyJoystickController
                ctr = MyJoystickController(
                    throttle_dir=cfg.JOYSTICK_THROTTLE_DIR,
                    throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
                    steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                    auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
                ctr.set_deadzone(cfg.JOYSTICK_DEADZONE)
            elif cfg.CONTROLLER_TYPE == "MM1":
                from donkeycar.parts.robohat import RoboHATController
                ctr = RoboHATController(cfg)
            elif cfg.CONTROLLER_TYPE == "mock":
                from donkeycar.parts.controller import MockController
                ctr = MockController(steering=cfg.MOCK_JOYSTICK_STEERING,
                                     throttle=cfg.MOCK_JOYSTICK_THROTTLE)
            else:
                #
                # game controller
                #
                from donkeycar.parts.controller import get_js_controller
                ctr = get_js_controller(cfg)
                if cfg.USE_NETWORKED_JS:
                    from donkeycar.parts.controller import JoyStickSub
                    netwkJs = JoyStickSub(cfg.NETWORK_JS_SERVER_IP)
                    V.add(netwkJs, threaded=True)
                    ctr.js = netwkJs
            V.add(
                ctr,
                inputs=[input_image, 'user/mode', 'recording'],
                outputs=['user/steering', 'user/throttle',
                         'user/mode', 'recording'],
                threaded=True)
    return ctr


def add_simulator(V, cfg):
    # Donkey gym part will output position information if it is configured
    # TODO: the simulation outputs conflict with imu, odometry, kinematics pose estimation and T265 outputs; make them work together.
    if cfg.DONKEY_GYM:
        from donkeycar.parts.dgym import DonkeyGymEnv
        # rbx
        gym = DonkeyGymEnv(cfg.DONKEY_SIM_PATH, host=cfg.SIM_HOST, env_name=cfg.DONKEY_GYM_ENV_NAME, conf=cfg.GYM_CONF,
                           record_location=cfg.SIM_RECORD_LOCATION, record_gyroaccel=cfg.SIM_RECORD_GYROACCEL,
                           record_velocity=cfg.SIM_RECORD_VELOCITY, record_lidar=cfg.SIM_RECORD_LIDAR,
                        #    record_distance=cfg.SIM_RECORD_DISTANCE, record_orientation=cfg.SIM_RECORD_ORIENTATION,
                           delay=cfg.SIM_ARTIFICIAL_LATENCY)
        threaded = True
        inputs = ['steering', 'throttle']
        outputs = ['cam/image_array']

        if cfg.SIM_RECORD_LOCATION:
            outputs += ['pos/pos_x', 'pos/pos_y', 'pos/pos_z', 'pos/speed', 'pos/cte']
        if cfg.SIM_RECORD_GYROACCEL:
            outputs += ['gyro/gyro_x', 'gyro/gyro_y', 'gyro/gyro_z', 'accel/accel_x', 'accel/accel_y', 'accel/accel_z']
        if cfg.SIM_RECORD_VELOCITY:
            outputs += ['vel/vel_x', 'vel/vel_y', 'vel/vel_z']
        if cfg.SIM_RECORD_LIDAR:
            outputs += ['lidar/dist_array']
        # if cfg.SIM_RECORD_DISTANCE:
        #     outputs += ['dist/left', 'dist/right']
        # if cfg.SIM_RECORD_ORIENTATION:
        #     outputs += ['roll', 'pitch', 'yaw']

        V.add(gym, inputs=inputs, outputs=outputs, threaded=threaded)


def get_camera(cfg):
    """
    Get the configured camera part
    """
    cam = None
    if not cfg.DONKEY_GYM:
        if cfg.CAMERA_TYPE == "PICAM":
            from donkeycar.parts.camera import PiCamera
            cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH,
                           vflip=cfg.CAMERA_VFLIP, hflip=cfg.CAMERA_HFLIP)
        elif cfg.CAMERA_TYPE == "WEBCAM":
            from donkeycar.parts.camera import Webcam
            cam = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        elif cfg.CAMERA_TYPE == "CVCAM":
            from donkeycar.parts.cv import CvCam
            cam = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        elif cfg.CAMERA_TYPE == "CSIC":
            from donkeycar.parts.camera import CSICamera
            cam = CSICamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH,
                            capture_width=cfg.IMAGE_W, capture_height=cfg.IMAGE_H,
                            framerate=cfg.CAMERA_FRAMERATE, gstreamer_flip=cfg.CSIC_CAM_GSTREAMER_FLIP_PARM)
        elif cfg.CAMERA_TYPE == "V4L":
            from donkeycar.parts.camera import V4LCamera
            cam = V4LCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, framerate=cfg.CAMERA_FRAMERATE)
        elif cfg.CAMERA_TYPE == "IMAGE_LIST":
            from donkeycar.parts.camera import ImageListCamera
            cam = ImageListCamera(path_mask=cfg.PATH_MASK)
        elif cfg.CAMERA_TYPE == "LEOPARD":
            from donkeycar.parts.leopard_imaging import LICamera
            cam = LICamera(width=cfg.IMAGE_W, height=cfg.IMAGE_H, fps=cfg.CAMERA_FRAMERATE)
        elif cfg.CAMERA_TYPE == "MOCK":
            from donkeycar.parts.camera import MockCamera
            cam = MockCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
        else:
            raise(Exception("Unkown camera type: %s" % cfg.CAMERA_TYPE))
    return cam


def add_camera(V, cfg, camera_type):
    """
    Add the configured camera to the vehicle pipeline.

    :param V: the vehicle pipeline.
              On output this will be modified.
    :param cfg: the configuration (from myconfig.py)
    """
    logger.info("cfg.CAMERA_TYPE %s"%cfg.CAMERA_TYPE)
    if camera_type == "stereo":
        if cfg.CAMERA_TYPE == "WEBCAM":
            from donkeycar.parts.camera import Webcam

            camA = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 0)
            camB = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 1)

        elif cfg.CAMERA_TYPE == "CVCAM":
            from donkeycar.parts.cv import CvCam

            camA = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 0)
            camB = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH, iCam = 1)
        else:
            raise(Exception("Unsupported camera type: %s" % cfg.CAMERA_TYPE))

        V.add(camA, outputs=['cam/image_array_a'], threaded=True)
        V.add(camB, outputs=['cam/image_array_b'], threaded=True)

        from donkeycar.parts.image import StereoPair

        V.add(StereoPair(), inputs=['cam/image_array_a', 'cam/image_array_b'],
            outputs=['cam/image_array'])
        if cfg.BGR2RGB:
            from donkeycar.parts.cv import ImgBGR2RGB
            V.add(ImgBGR2RGB(), inputs=["cam/image_array_a"], outputs=["cam/image_array_a"])
            V.add(ImgBGR2RGB(), inputs=["cam/image_array_b"], outputs=["cam/image_array_b"])

    elif cfg.CAMERA_TYPE == "D435":
        from donkeycar.parts.realsense435i import RealSense435i
        cam = RealSense435i(
            enable_rgb=cfg.REALSENSE_D435_RGB,
            enable_depth=cfg.REALSENSE_D435_DEPTH,
            enable_imu=cfg.REALSENSE_D435_IMU,
            device_id=cfg.REALSENSE_D435_ID)
        V.add(cam, inputs=[],
              outputs=['cam/image_array', 'cam/depth_array',
                       'imu/acl_x', 'imu/acl_y', 'imu/acl_z',
                       'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z'],
              threaded=True)
        
    elif cfg.CAMERA_TYPE == "OAKD":
        from donkeycar.parts.oak_d import OakD
        cam = OakD(
            enable_rgb=cfg.OAKD_RGB,
            enable_depth=cfg.OAKD_DEPTH,
            device_id=cfg.OAKD_ID)
        V.add(cam, inputs=[],
              outputs=['cam/image_array', 'cam/depth_array'],
              threaded=True)

    else:
        inputs = []
        outputs = ['cam/image_array']
        threaded = True
        cam = get_camera(cfg)
        if cam:
            V.add(cam, inputs=inputs, outputs=outputs, threaded=threaded)
        if cfg.BGR2RGB:
            from donkeycar.parts.cv import ImgBGR2RGB
            V.add(ImgBGR2RGB(), inputs=["cam/image_array"], outputs=["cam/image_array"])


def add_odometry(V, cfg, threaded=True):
    """
    If the configuration support odometry, then
    add encoders, odometry and kinematics to the vehicle pipeline
    :param V: the vehicle pipeline.
              On output this may be modified.
    :param cfg: the configuration (from myconfig.py)
    """
    from donkeycar.parts.pose import BicyclePose, UnicyclePose

    if cfg.HAVE_ODOM:
        poll_delay_secs = 0.01  # pose estimation runs at 100hz
        kinematics = UnicyclePose(cfg, poll_delay_secs) if cfg.HAVE_ODOM_2 else BicyclePose(cfg, poll_delay_secs)
        V.add(kinematics,
            inputs = ["throttle", "steering", None],
            outputs = ['enc/distance', 'enc/speed', 'pos/x', 'pos/y',
                       'pos/angle', 'vel/x', 'vel/y', 'vel/angle',
                       'nul/timestamp'],
            threaded = threaded)


#
# IMU setup
#
def add_imu(V, cfg):
    imu = None
    if cfg.HAVE_IMU:
        from donkeycar.parts.imu import IMU

        imu = IMU(sensor=cfg.IMU_SENSOR, addr=cfg.IMU_ADDRESS,
                  dlp_setting=cfg.IMU_DLP_CONFIG)
        V.add(imu, outputs=['imu/acl_x', 'imu/acl_y', 'imu/acl_z',
                            'imu/gyr_x', 'imu/gyr_y', 'imu/gyr_z'], threaded=True)
    return imu


#
# Drive train setup
#
def add_drivetrain(V, cfg):

    if (not cfg.DONKEY_GYM) and cfg.DRIVE_TRAIN_TYPE != "MOCK":
        from donkeycar.parts import actuator, pins
        from donkeycar.parts.actuator import TwoWheelSteeringThrottle

        #
        # To make differential drive steer,
        # divide throttle between motors based on the steering value
        #
        is_differential_drive = cfg.DRIVE_TRAIN_TYPE.startswith("DC_TWO_WHEEL")
        if is_differential_drive:
            V.add(TwoWheelSteeringThrottle(),
                  inputs=['throttle', 'steering'],
                  outputs=['left/throttle', 'right/throttle'])

        if cfg.DRIVE_TRAIN_TYPE == "PWM_STEERING_THROTTLE":
            #
            # drivetrain for RC car with servo and ESC.
            # using a PwmPin for steering (servo)
            # and as second PwmPin for throttle (ESC)
            #
            from donkeycar.parts.actuator import PWMSteering, PWMThrottle, PulseController

            dt = cfg.PWM_STEERING_THROTTLE
            steering_controller = PulseController(
                pwm_pin=pins.pwm_pin_by_id(dt["PWM_STEERING_PIN"]),
                pwm_scale=dt["PWM_STEERING_SCALE"],
                pwm_inverted=dt["PWM_STEERING_INVERTED"])
            steering = PWMSteering(controller=steering_controller,
                                            left_pulse=dt["STEERING_LEFT_PWM"],
                                            right_pulse=dt["STEERING_RIGHT_PWM"])

            throttle_controller = PulseController(
                pwm_pin=pins.pwm_pin_by_id(dt["PWM_THROTTLE_PIN"]),
                pwm_scale=dt["PWM_THROTTLE_SCALE"],
                pwm_inverted=dt['PWM_THROTTLE_INVERTED'])
            throttle = PWMThrottle(controller=throttle_controller,
                                                max_pulse=dt['THROTTLE_FORWARD_PWM'],
                                                zero_pulse=dt['THROTTLE_STOPPED_PWM'],
                                                min_pulse=dt['THROTTLE_REVERSE_PWM'])
            V.add(steering, inputs=['steering'], threaded=True)
            V.add(throttle, inputs=['throttle'], threaded=True)

        elif cfg.DRIVE_TRAIN_TYPE == "I2C_SERVO":
            #
            # This driver is DEPRECATED in favor of 'DRIVE_TRAIN_TYPE == "PWM_STEERING_THROTTLE"'
            # This driver will be removed in a future release
            #
            from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle

            steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
            steering = PWMSteering(controller=steering_controller,
                                            left_pulse=cfg.STEERING_LEFT_PWM,
                                            right_pulse=cfg.STEERING_RIGHT_PWM)

            throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
            throttle = PWMThrottle(controller=throttle_controller,
                                            max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                            zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                                            min_pulse=cfg.THROTTLE_REVERSE_PWM)

            V.add(steering, inputs=['steering'], threaded=True)
            V.add(throttle, inputs=['throttle'], threaded=True)

        elif cfg.DRIVE_TRAIN_TYPE == "DC_STEER_THROTTLE":
            dt = cfg.DC_STEER_THROTTLE
            steering = actuator.L298N_HBridge_2pin(
                pins.pwm_pin_by_id(dt['LEFT_DUTY_PIN']),
                pins.pwm_pin_by_id(dt['RIGHT_DUTY_PIN']))
            throttle = actuator.L298N_HBridge_2pin(
                pins.pwm_pin_by_id(dt['FWD_DUTY_PIN']),
                pins.pwm_pin_by_id(dt['BWD_DUTY_PIN']))

            V.add(steering, inputs=['steering'])
            V.add(throttle, inputs=['throttle'])

        elif cfg.DRIVE_TRAIN_TYPE == "DC_TWO_WHEEL":
            dt = cfg.DC_TWO_WHEEL
            left_motor = actuator.L298N_HBridge_2pin(
                pins.pwm_pin_by_id(dt['LEFT_FWD_DUTY_PIN']),
                pins.pwm_pin_by_id(dt['LEFT_BWD_DUTY_PIN']))
            right_motor = actuator.L298N_HBridge_2pin(
                pins.pwm_pin_by_id(dt['RIGHT_FWD_DUTY_PIN']),
                pins.pwm_pin_by_id(dt['RIGHT_BWD_DUTY_PIN']))

            V.add(left_motor, inputs=['left/throttle'])
            V.add(right_motor, inputs=['right/throttle'])

        elif cfg.DRIVE_TRAIN_TYPE == "DC_TWO_WHEEL_L298N":
            dt = cfg.DC_TWO_WHEEL_L298N
            left_motor = actuator.L298N_HBridge_3pin(
                pins.output_pin_by_id(dt['LEFT_FWD_PIN']),
                pins.output_pin_by_id(dt['LEFT_BWD_PIN']),
                pins.pwm_pin_by_id(dt['LEFT_EN_DUTY_PIN']))
            right_motor = actuator.L298N_HBridge_3pin(
                pins.output_pin_by_id(dt['RIGHT_FWD_PIN']),
                pins.output_pin_by_id(dt['RIGHT_BWD_PIN']),
                pins.pwm_pin_by_id(dt['RIGHT_EN_DUTY_PIN']))

            V.add(left_motor, inputs=['left/throttle'])
            V.add(right_motor, inputs=['right/throttle'])

        elif cfg.DRIVE_TRAIN_TYPE == "SERVO_HBRIDGE_2PIN":
            #
            # Servo for steering and HBridge motor driver in 2pin mode for motor
            #
            from donkeycar.parts.actuator import PWMSteering, PWMThrottle, PulseController

            dt = cfg.SERVO_HBRIDGE_2PIN
            steering_controller = PulseController(
                pwm_pin=pins.pwm_pin_by_id(dt['PWM_STEERING_PIN']),
                pwm_scale=dt['PWM_STEERING_SCALE'],
                pwm_inverted=dt['PWM_STEERING_INVERTED'])
            steering = PWMSteering(controller=steering_controller,
                                            left_pulse=dt['STEERING_LEFT_PWM'],
                                            right_pulse=dt['STEERING_RIGHT_PWM'])

            motor = actuator.L298N_HBridge_2pin(
                pins.pwm_pin_by_id(dt['FWD_DUTY_PIN']),
                pins.pwm_pin_by_id(dt['BWD_DUTY_PIN']))

            V.add(steering, inputs=['steering'], threaded=True)
            V.add(motor, inputs=["throttle"])

        elif cfg.DRIVE_TRAIN_TYPE == "SERVO_HBRIDGE_3PIN":
            #
            # Servo for steering and HBridge motor driver in 3pin mode for motor
            #
            from donkeycar.parts.actuator import PWMSteering, PWMThrottle, PulseController

            dt = cfg.SERVO_HBRIDGE_3PIN
            steering_controller = PulseController(
                pwm_pin=pins.pwm_pin_by_id(dt['PWM_STEERING_PIN']),
                pwm_scale=dt['PWM_STEERING_SCALE'],
                pwm_inverted=dt['PWM_STEERING_INVERTED'])
            steering = PWMSteering(controller=steering_controller,
                                            left_pulse=dt['STEERING_LEFT_PWM'],
                                            right_pulse=dt['STEERING_RIGHT_PWM'])

            motor = actuator.L298N_HBridge_3pin(
                pins.output_pin_by_id(dt['FWD_PIN']),
                pins.output_pin_by_id(dt['BWD_PIN']),
                pins.pwm_pin_by_id(dt['DUTY_PIN']))

            V.add(steering, inputs=['steering'], threaded=True)
            V.add(motor, inputs=["throttle"])

        elif cfg.DRIVE_TRAIN_TYPE == "SERVO_HBRIDGE_PWM":
            #
            # This driver is DEPRECATED in favor of 'DRIVE_TRAIN_TYPE == "SERVO_HBRIDGE_2PIN"'
            # This driver will be removed in a future release
            #
            from donkeycar.parts.actuator import ServoBlaster, PWMSteering
            steering_controller = ServoBlaster(cfg.STEERING_CHANNEL) #really pin
            # PWM pulse values should be in the range of 100 to 200
            assert(cfg.STEERING_LEFT_PWM <= 200)
            assert(cfg.STEERING_RIGHT_PWM <= 200)
            steering = PWMSteering(controller=steering_controller,
                                   left_pulse=cfg.STEERING_LEFT_PWM,
                                   right_pulse=cfg.STEERING_RIGHT_PWM)

            from donkeycar.parts.actuator import Mini_HBridge_DC_Motor_PWM
            motor = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_FWD, cfg.HBRIDGE_PIN_BWD)

            V.add(steering, inputs=['steering'], threaded=True)
            V.add(motor, inputs=["throttle"])

        elif cfg.DRIVE_TRAIN_TYPE == "MM1":
            from donkeycar.parts.robohat import RoboHATDriver
            V.add(RoboHATDriver(cfg), inputs=['steering', 'throttle'])

        elif cfg.DRIVE_TRAIN_TYPE == "PIGPIO_PWM":
            #
            # This driver is DEPRECATED in favor of 'DRIVE_TRAIN_TYPE == "PWM_STEERING_THROTTLE"'
            # This driver will be removed in a future release
            #
            from donkeycar.parts.actuator import PWMSteering, PWMThrottle, PiGPIO_PWM
            steering_controller = PiGPIO_PWM(cfg.STEERING_PWM_PIN, freq=cfg.STEERING_PWM_FREQ,
                                             inverted=cfg.STEERING_PWM_INVERTED)
            steering = PWMSteering(controller=steering_controller,
                                   left_pulse=cfg.STEERING_LEFT_PWM,
                                   right_pulse=cfg.STEERING_RIGHT_PWM)

            throttle_controller = PiGPIO_PWM(cfg.THROTTLE_PWM_PIN, freq=cfg.THROTTLE_PWM_FREQ,
                                             inverted=cfg.THROTTLE_PWM_INVERTED)
            throttle = PWMThrottle(controller=throttle_controller,
                                   max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                   zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                                   min_pulse=cfg.THROTTLE_REVERSE_PWM)
            V.add(steering, inputs=['steering'], threaded=True)
            V.add(throttle, inputs=['throttle'], threaded=True)
    
        elif cfg.DRIVE_TRAIN_TYPE == "VESC":
            from donkeycar.parts.actuator import VESC
            logger.info("Creating VESC at port {}".format(cfg.VESC_SERIAL_PORT))
            vesc = VESC(cfg.VESC_SERIAL_PORT,
                          cfg.VESC_MAX_SPEED_PERCENT,
                          cfg.VESC_HAS_SENSOR,
                          cfg.VESC_START_HEARTBEAT,
                          cfg.VESC_BAUDRATE,
                          cfg.VESC_TIMEOUT,
                          cfg.VESC_STEERING_SCALE,
                          cfg.VESC_STEERING_OFFSET
                        )
            V.add(vesc, inputs=['steering', 'throttle'])


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config(myconfig=args['--myconfig'])

    if args['drive']:
        model_type = args['--type']
        camera_type = args['--camera']
        drive(cfg, model_path=args['--model'], use_joystick=args['--js'],
              model_type=model_type, camera_type=camera_type,
              meta=args['--meta'])
    elif args['train']:
        print('Use python train.py instead.\n')
