#!/usr/bin/env python3
'''
Use the default template.
Remove these lines:
'''

    from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle

    steering_controller = PCA9685(cfg.STEERING_CHANNEL)
    steering = PWMSteering(controller=steering_controller,
                           left_pulse=cfg.STEERING_LEFT_PWM,
                           right_pulse=cfg.STEERING_RIGHT_PWM)

    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL)
    throttle = PWMThrottle(controller=throttle_controller,
                           max_pulse=cfg.THROTTLE_FORWARD_PWM,
                           zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                           min_pulse=cfg.THROTTLE_REVERSE_PWM)

    V.add(steering, inputs=['angle'])
    V.add(throttle, inputs=['throttle'])

'''
Replace them with these lines
'''
    from donkeycar.parts.actuator import TwoWheelSteeringThrottle, L298N_HBridge_DC_Motor

    left_motor = L298N_HBridge_DC_Motor(cfg.LEFT_PIN_FRWD, cfg.LEFT_PIN_BKWD, cfg.LEFT_PIN_PWM)
    right_motor = L298N_HBridge_DC_Motor(cfg.RIGHT_PIN_FRWD, cfg.RIGHT_PIN_BKWD, cfg.RIGHT_PIN_PWM)
    two_wheel_control = TwoWheelSteeringThrottle()

    V.add(two_wheel_control, 
            inputs=['throttle', 'angle'],
            outputs=['left_motor_speed', 'right_motor_speed'])

    V.add(left_motor, inputs=['left_motor_speed'])
    V.add(right_motor, inputs=['right_motor_speed'])

'''
Add these lines to your config.py
'''

    #TWO WHEEL BOTS
    #These pins are in board number mode
    LEFT_PIN_FRWD = 0
    LEFT_PIN_BKWD = 0
    RIGHT_PIN_FRWD = 0
    RIGHT_PIN_BKWD = 0
    RIGHT_PIN_PWM = 12 #for the PI these are recommended
    LEFT_PIN_PWM = 19 #for the PI these are recommended
