import time
import donkeycar as dk
from donkeycar.parts.actuator import ServoBlaster, PWMSteering
from donkeycar.parts.transform import Lambda
import math

cfg = dk.load_config()

V = dk.Vehicle()
V.timer = time.time()

def steering_control():
    t = time.time() - V.timer
    val = math.cos(t)
    return val

controls = Lambda(steering_control)
V.add(controls, outputs=["angle"])

steering_controller = ServoBlaster(cfg.STEERING_CHANNEL) #really pin

#PWM pulse values should be in the range of 100 to 200
assert(cfg.STEERING_LEFT_PWM <= 200)
assert(cfg.STEERING_RIGHT_PWM <= 200)
steering = PWMSteering(controller=steering_controller,
                                left_pulse=cfg.STEERING_LEFT_PWM, 
                                right_pulse=cfg.STEERING_RIGHT_PWM)
V.add(steering, inputs=['angle'])
V.start(rate_hz=cfg.DRIVE_LOOP_HZ)
