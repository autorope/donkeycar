'''
file: manage_remote.py
author: Tawn Kramer
date: 2016-01-24
desc: Control a remote donkey robot over network
'''
import time
import donkeycar as dk
from donkeycar.parts.camera import PiCamera
from donkeycar.parts.network import TCPServeValue, UDPValueSub, MQTTValueSub, MQTTValuePub
from donkeycar.parts.image import ImgArrToJpg
from donkeycar.parts.actuator import Mini_HBridge_DC_Motor_PWM
from donkeycar.parts.actuator import ServoBlaster, PWMSteering

cfg = dk.load_config()

V = dk.Vehicle()

print("starting up", cfg.DONKEY_UNIQUE_NAME)

cam = PiCamera(image_w=cfg.IMAGE_W, image_h=cfg.IMAGE_H, image_d=cfg.IMAGE_DEPTH)
V.add(cam, outputs=["camera/arr"], threaded=True)

img_to_jpg = ImgArrToJpg()
V.add(img_to_jpg, inputs=["camera/arr"], outputs=["camera/jpg"])

pub_cam = MQTTValuePub("donkey/%s/camera" % cfg.DONKEY_UNIQUE_NAME)
V.add(pub_cam, inputs=["camera/jpg"])

print("Listening for donkey/controls")
sub_controls = MQTTValueSub("donkey/%s/controls" % cfg.DONKEY_UNIQUE_NAME, def_value=(0., 0.))
V.add(sub_controls, outputs=["angle", "throttle"])

steering_controller = ServoBlaster(cfg.STEERING_CHANNEL)

#PWM pulse values should be in the range of 100 to 200
assert(cfg.STEERING_LEFT_PWM <= 200)
assert(cfg.STEERING_RIGHT_PWM <= 200)
steering = PWMSteering(controller=steering_controller,
                                left_pulse=cfg.STEERING_LEFT_PWM, 
                                right_pulse=cfg.STEERING_RIGHT_PWM)


from donkeycar.parts.actuator import Mini_HBridge_DC_Motor_PWM
motor = Mini_HBridge_DC_Motor_PWM(cfg.HBRIDGE_PIN_FWD, cfg.HBRIDGE_PIN_BWD)

V.add(steering, inputs=['angle'])
V.add(motor, inputs=["throttle"])

V.start(rate_hz=cfg.DRIVE_LOOP_HZ)
