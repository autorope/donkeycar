#!/usr/bin/env python3
"""
Scripts to drive a donkey car

Usage:
    manage.py drive [--model=<model>] [--type=(linear|categorical|tflite_linear)]

Options:
    -h --help          Show this screen.
"""

from docopt import docopt

import donkeycar as dk
from donkeycar.parts.tub_v2 import TubWriter
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.controller import LocalWebController
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle


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
    """ Helper class to determine how is in charge of driving"""
    def run(self, mode):
        return mode != 'user'


def drive(cfg, model_path=None, model_type=None):
    """
    Construct a minimal robotic vehicle from many parts. Here, we use a
    single camera, web or joystick controller, autopilot and tubwriter.

    Each part runs as a job in the Vehicle loop, calling either it's run or
    run_threaded method depending on the constructor flag `threaded`. All
    parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely
    manner. Parts may have named outputs and inputs. The framework handles
    passing named outputs to parts requesting the same named input.
    """

    car = dk.vehicle.Vehicle()
    # add camera
    inputs = []
    if cfg.DONKEY_GYM:
        from donkeycar.parts.dgym import DonkeyGymEnv 
        cam = DonkeyGymEnv(cfg.DONKEY_SIM_PATH, host=cfg.SIM_HOST, env_name=cfg.DONKEY_GYM_ENV_NAME, conf=cfg.GYM_CONF, delay=cfg.SIM_ARTIFICIAL_LATENCY)
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
            outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
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
        steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR,
                                    busnum=cfg.PCA9685_I2C_BUSNUM)
        steering = PWMSteering(controller=steering_controller,
                            left_pulse=cfg.STEERING_LEFT_PWM,
                            right_pulse=cfg.STEERING_RIGHT_PWM)

        throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR,
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
    # start the car
    car.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=cfg.MAX_LOOPS)


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()
    drive(cfg, model_path=args['--model'], model_type=args['--type'])
