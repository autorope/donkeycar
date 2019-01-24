'''
file: manage_remote.py
author: Tawn Kramer
date: 2016-01-24
desc: Control a remote donkey robot over network
'''
import time
import donkeycar as dk
from donkeycar.parts.camera import PiCamera
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.network import TCPServeValue, UDPValueSub
from donkeycar.parts.image import ImgArrToJpg

cfg = dk.load_config()

V = dk.Vehicle()

cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
V.add(cam, outputs=["camera/arr"], threaded=True)

#warm up camera
while cam.run_threaded() is None:
    V.update_parts()
    time.sleep(1)

img_to_jpg = ImgArrToJpg()
V.add(img_to_jpg, inputs=["camera/arr"], outputs=["camera/jpg"])

pub_cam = TCPServeValue("donkey/camera", port=cfg.CAMERA_PORT)
V.add(pub_cam, inputs=["camera/jpg"])

sub_controls = UDPValueSub("donkey/controls", port=cfg.CONTROLS_PORT, def_value=(0., 0.))
V.add(sub_controls, outputs=["angle", "throttle"], threaded=True)

steering_controller = PCA9685(cfg.STEERING_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
steering = PWMSteering(controller=steering_controller,
                                left_pulse=cfg.STEERING_LEFT_PWM, 
                                right_pulse=cfg.STEERING_RIGHT_PWM)

throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL, cfg.PCA9685_I2C_ADDR, busnum=cfg.PCA9685_I2C_BUSNUM)
throttle = PWMThrottle(controller=throttle_controller,
                                max_pulse=cfg.THROTTLE_FORWARD_PWM,
                                zero_pulse=cfg.THROTTLE_STOPPED_PWM, 
                                min_pulse=cfg.THROTTLE_REVERSE_PWM)

V.add(steering, inputs=['angle'])
V.add(throttle, inputs=['throttle'])

V.start(rate_hz=cfg.DRIVE_LOOP_HZ)
