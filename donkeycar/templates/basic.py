#!/usr/bin/env python3
"""
Scripts to drive a donkey car

Usage:
    manage.py drive [--model=<model>] [--type=(linear|categorical|...)]
    manage.py calibrate

Options:
    -h --help          Show this screen.
"""

from docopt import docopt
import logging
import os

import donkeycar as dk
from donkeycar.parts.tub_v2 import TubWriter, TubWiper
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.controller import LocalWebController, RCReceiver
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.pipeline.augmentations import ImageAugmentation

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


class DriveMode:
    """ Helper class to dispatch between ai and user driving"""

    def __init__(self, cfg):
        self.cfg = cfg

    def run(self, mode, user_angle, user_throttle, pilot_angle, pilot_throttle):
        if mode == 'user':
            return user_angle, user_throttle
        elif mode == 'local_angle':
            return pilot_angle if pilot_angle else 0.0, user_throttle
        else:
            return pilot_angle if pilot_angle else 0.0, \
                   pilot_throttle * self.cfg.AI_THROTTLE_MULT if \
                       pilot_throttle else 0.0


class PilotCondition:
    """ Helper class to determine who is in charge of driving"""
    def run(self, mode):
        return mode != 'user'


def drive(cfg, model_path=None, model_type=None):
    """
    Construct a minimal robotic vehicle from many parts. Here, we use a
    single camera, web or joystick controller, autopilot and tubwriter.

    Each part runs as a job in the Vehicle loop, calling either its run or
    run_threaded method depending on the constructor flag `threaded`. All
    parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely
    manner. Parts may have named outputs and inputs. The framework handles
    passing named outputs to parts requesting the same named input.
    """
    logger.info(f'PID: {os.getpid()}')
    car = dk.vehicle.Vehicle()
    # add camera
    inputs = []
    if cfg.DONKEY_GYM:
        from donkeycar.parts.dgym import DonkeyGymEnv 
        cam = DonkeyGymEnv(cfg.DONKEY_SIM_PATH, host=cfg.SIM_HOST,
                           env_name=cfg.DONKEY_GYM_ENV_NAME, conf=cfg.GYM_CONF,
                           delay=cfg.SIM_ARTIFICIAL_LATENCY)
        inputs = ['angle', 'throttle', 'brake']
    elif cfg.CAMERA_TYPE == "PICAM":
        from donkeycar.parts.camera import PiCamera
        cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                       image_d=cfg.IMAGE_DEPTH, framerate=cfg.CAMERA_FRAMERATE,
                       vflip=cfg.CAMERA_VFLIP, hflip=cfg.CAMERA_HFLIP)
    elif cfg.CAMERA_TYPE == "WEBCAM":
        from donkeycar.parts.camera import Webcam
        cam = Webcam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                     image_d=cfg.IMAGE_DEPTH)
    elif cfg.CAMERA_TYPE == "CVCAM":
        from donkeycar.parts.cv import CvCam
        cam = CvCam(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                    image_d=cfg.IMAGE_DEPTH)
    elif cfg.CAMERA_TYPE == "CSIC":
        from donkeycar.parts.camera import CSICamera
        cam = CSICamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                        image_d=cfg.IMAGE_DEPTH, framerate=cfg.CAMERA_FRAMERATE,
                        gstreamer_flip=cfg.CSIC_CAM_GSTREAMER_FLIP_PARM)
    elif cfg.CAMERA_TYPE == "V4L":
        from donkeycar.parts.camera import V4LCamera
        cam = V4LCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                        image_d=cfg.IMAGE_DEPTH, framerate=cfg.CAMERA_FRAMERATE)
    elif cfg.CAMERA_TYPE == "MOCK":
        from donkeycar.parts.camera import MockCamera
        cam = MockCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H,
                         image_d=cfg.IMAGE_DEPTH)
    elif cfg.CAMERA_TYPE == "IMAGE_LIST":
        from donkeycar.parts.camera import ImageListCamera
        cam = ImageListCamera(path_mask=cfg.PATH_MASK)
    else:
        raise (Exception("Unkown camera type: %s" % cfg.CAMERA_TYPE))

    car.add(cam, inputs=inputs, outputs=['cam/image_array'], threaded=True)

    # add controller
    if cfg.USE_RC:
        rc_steering = RCReceiver(cfg.STEERING_RC_GPIO, invert=True)
        rc_throttle = RCReceiver(cfg.THROTTLE_RC_GPIO)
        rc_wiper = RCReceiver(cfg.DATA_WIPER_RC_GPIO, jitter=0.05, no_action=0)
        car.add(rc_steering, outputs=['user/angle', 'user/angle_on'])
        car.add(rc_throttle, outputs=['user/throttle', 'user/throttle_on'])
        car.add(rc_wiper, outputs=['user/wiper', 'user/wiper_on'])
        ctr = LocalWebController(port=cfg.WEB_CONTROL_PORT,
                                 mode=cfg.WEB_INIT_MODE)
        # web controller sets user mode, its angle, throttle are not used.
        car.add(ctr, inputs=['cam/image_array'],
                outputs=['webcontroller/angle', 'webcontroller/throttle',
                         'user/mode', 'recording'],
                threaded=True)

    else:
        if cfg.USE_JOYSTICK_AS_DEFAULT:
            from donkeycar.parts.controller import get_js_controller
            ctr = get_js_controller(cfg)
            if cfg.USE_NETWORKED_JS:
                from donkeycar.parts.controller import JoyStickSub
                netwkJs = JoyStickSub(cfg.NETWORK_JS_SERVER_IP)
                car.add(netwkJs, threaded=True)
                ctr.js = netwkJs
        else:
            ctr = LocalWebController(port=cfg.WEB_CONTROL_PORT,
                                     mode=cfg.WEB_INIT_MODE)
        car.add(ctr,
                inputs=['cam/image_array'],
                outputs=['user/angle', 'user/throttle', 'user/mode',
                         'recording'],
                threaded=True)

    # pilot condition to determine if user or ai are driving
    car.add(PilotCondition(), inputs=['user/mode'], outputs=['run_pilot'])

    # adding the auto-pilot
    if model_type is None:
        model_type = cfg.DEFAULT_MODEL_TYPE
    if model_path:
        kl = dk.utils.get_model_by_type(model_type, cfg)
        kl.load(model_path=model_path)
        inputs = ['cam/image_array']
        # Add image transformations like crop or trapezoidal mask
        if hasattr(cfg, 'TRANSFORMATIONS') and cfg.TRANSFORMATIONS:
            outputs = ['cam/image_array_trans']
            car.add(ImageAugmentation(cfg, 'TRANSFORMATIONS'),
                    inputs=inputs, outputs=outputs)
            inputs = outputs

        outputs = ['pilot/angle', 'pilot/throttle']
        car.add(kl, inputs=inputs, outputs=outputs, run_condition='run_pilot')

    # Choose what inputs should change the car.
    car.add(DriveMode(cfg=cfg),
            inputs=['user/mode', 'user/angle', 'user/throttle',
                    'pilot/angle', 'pilot/throttle'],
            outputs=['angle', 'throttle'])

    # Drive train setup
    if cfg.DONKEY_GYM or cfg.DRIVE_TRAIN_TYPE == "MOCK":
        pass
    else:
        steering_controller = PCA9685(cfg.STEERING_CHANNEL,
                                      cfg.PCA9685_I2C_ADDR,
                                      busnum=cfg.PCA9685_I2C_BUSNUM)
        steering = PWMSteering(controller=steering_controller,
                               left_pulse=cfg.STEERING_LEFT_PWM,
                               right_pulse=cfg.STEERING_RIGHT_PWM)

        throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL,
                                      cfg.PCA9685_I2C_ADDR,
                                      busnum=cfg.PCA9685_I2C_BUSNUM)
        throttle = PWMThrottle(controller=throttle_controller,
                               max_pulse=cfg.THROTTLE_FORWARD_PWM,
                               zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                               min_pulse=cfg.THROTTLE_REVERSE_PWM)

        car.add(steering, inputs=['angle'])
        car.add(throttle, inputs=['throttle'])

    # add tub to save data
    inputs = ['cam/image_array', 'user/angle', 'user/throttle', 'user/mode']
    types = ['image_array', 'float', 'float', 'str']

    # do we want to store new records into own dir or append to existing
    tub_path = TubHandler(path=cfg.DATA_PATH).create_tub_path() if \
        cfg.AUTO_CREATE_NEW_TUB else cfg.DATA_PATH
    tub_writer = TubWriter(base_path=tub_path, inputs=inputs, types=types)
    car.add(tub_writer, inputs=inputs, outputs=["tub/num_records"],
            run_condition='recording')
    if not model_path and cfg.USE_RC:
        tub_wiper = TubWiper(tub_writer.tub, num_records=cfg.DRIVE_LOOP_HZ)
        car.add(tub_wiper, inputs=['user/wiper_on'])
    # start the car
    car.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=cfg.MAX_LOOPS)


def calibrate(cfg):
    """
    Construct an auxiliary robotic vehicle from only the RC controllers and
    prints their values. The RC remote usually has a tuning pot for the throttle
    and steering channel. In this loop we run the controllers and simply print
    their values in order to allow centering the RC pwm signals. If there is a
    third channel on the remote we can use it for wiping bad data while
    recording, so we print its values here, too.
    """
    donkey_car = dk.vehicle.Vehicle()

    # create the RC receiver
    rc_steering = RCReceiver(cfg.STEERING_RC_GPIO, invert=True)
    rc_throttle = RCReceiver(cfg.THROTTLE_RC_GPIO)
    rc_wiper = RCReceiver(cfg.DATA_WIPER_RC_GPIO, jitter=0.05, no_action=0)
    donkey_car.add(rc_steering, outputs=['user/angle', 'user/steering_on'])
    donkey_car.add(rc_throttle, outputs=['user/throttle', 'user/throttle_on'])
    donkey_car.add(rc_wiper, outputs=['user/wiper', 'user/wiper_on'])

    # create plotter part for printing into the shell
    class Plotter:
        def run(self, angle, steering_on, throttle, throttle_on, wiper, wiper_on):
            print('angle=%+5.4f, steering_on=%1d, throttle=%+5.4f, '
                  'throttle_on=%1d wiper=%+5.4f, wiper_on=%1d' %
                  (angle, steering_on, throttle, throttle_on, wiper, wiper_on))

    # add plotter part
    donkey_car.add(Plotter(), inputs=['user/angle', 'user/steering_on',
                                      'user/throttle', 'user/throttle_on',
                                      'user/wiper', 'user/wiper_on'])
    # run the vehicle at 5Hz to keep network traffic down
    donkey_car.start(rate_hz=10, max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    if args['drive']:
        drive(cfg, model_path=args['--model'], model_type=args['--type'])
    elif args['calibrate']:
        calibrate(cfg)
