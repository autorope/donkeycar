"""
actuators.py

Classes to control the motors and servos. These classes 
are wrapped in a mixer class before being used in the drive loop.

"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except Exception as err:
    print("Error importing RPi.GPIO")


def map_range(x, X_min, X_max, Y_min, Y_max):
    ''' 
    Linear mapping between two ranges of values 
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range / Y_range

    y = ((x - X_min) / XY_ratio + Y_min) // 1

    return int(y)


class RasPiRobot_Controller:
    def __init__(self, driveLeft, driveRight):
        import rrb3
        rr = RRB3(9, 6)
        leftDir = 0
        rightDir = 0
        if driveLeft < 0:  # change direction if number is negative
            leftDir = 1
        if driveRight < 0:
            rightDir = 1
        rr.set_motors(abs(driveLeft), leftDir, abs(driveRight), rightDir)


class PCA9685_Controller:
    ''' 
    Adafruit PWM controler. 
    This is used for most RC Cars
    '''

    def __init__(self, channel, frequency=60):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        self.pwm.set_pwm_freq(frequency)
        self.channel = channel

    def set_pulse(self, pulse):
        self.pwm.set_pwm(self.channel, 0, pulse)


class GPIOSteeringAcutator:
    def __init__(self, left_channel, right_channel):
        GPIO.setmode(GPIO.BCM)
        self.left_channel = left_channel
        self.right_channel = right_channel
        GPIO.setup(left_channel, GPIO.OUT)
        GPIO.setup(right_channel, GPIO.OUT)

    def update(self, angle):
        if angle > 0:
            print("Turning right: right_channel("
                + str(self.right_channel)
                + ")=HIGH, left_channel("
                + str(self.left_channel) + ")=LOW")
            GPIO.output(self.right_channel, GPIO.HIGH)
            GPIO.output(self.left_channel, GPIO.LOW)
        elif angle == 0:
            print("No Turning: right_channel("
                  + str(self.right_channel)
                  + ")=LOW, left_channel("
                  + str(self.left_channel) + ")=LOW")
            GPIO.output(self.left_channel, GPIO.LOW)
            GPIO.output(self.right_channel, GPIO.LOW)
        else:
            print("Turning left: right_channel("
                  + str(self.right_channel)
                  + ")=LOW, left_channel("
                  + str(self.left_channel) + ")=HIGH")
            GPIO.output(self.left_channel, GPIO.HIGH)
            GPIO.output(self.right_channel, GPIO.LOW)


class GPIOThrottleActuator:
    def __init__(self, fwd_channel, bwd_channel):
        GPIO.setmode(GPIO.BCM)
        self.bwd_channel = bwd_channel
        self.fwd_channel = fwd_channel
        GPIO.setup(fwd_channel, GPIO.OUT)
        GPIO.setup(bwd_channel, GPIO.OUT)

    def update(self, throttle):
        if throttle > 0:
            GPIO.output(self.fwd_channel, GPIO.HIGH)
            GPIO.output(self.bwd_channel, GPIO.LOW)
        elif throttle < 0:
            GPIO.output(self.fwd_channel, GPIO.LOW)
            GPIO.output(self.bwd_channel, GPIO.HIGH)
        else:
            GPIO.output(self.fwd_channel, GPIO.LOW)
            GPIO.output(self.bwd_channel, GPIO.LOW)


class PWMSteeringActuator:
    # max angle wheels can turn
    LEFT_ANGLE = -1
    RIGHT_ANGLE = 1

    def __init__(self, controller=None,
                 left_pulse=290,
                 right_pulse=490):
        self.controller = controller
        self.left_pulse = left_pulse
        self.right_pulse = right_pulse

    def update(self, angle):
        # map absolute angle to angle that vehicle can implement.
        pulse = map_range(angle,
                          self.LEFT_ANGLE, self.RIGHT_ANGLE,
                          self.left_pulse, self.right_pulse)

        self.controller.set_pulse(pulse)


class PWMThrottleActuator:
    MIN_THROTTLE = -1
    MAX_THROTTLE = 1

    def __init__(self, controller=None,
                 max_pulse=300,
                 min_pulse=490,
                 zero_pulse=350):

        # super().__init__(channel, frequency)
        self.controller = controller
        self.max_pulse = max_pulse
        self.min_pulse = min_pulse
        self.zero_pulse = zero_pulse
        self.calibrate()

    def calibrate(self):
        # Calibrate ESC (TODO: THIS DOES NOT WORK YET)
        print('center: %s' % self.zero_pulse)
        self.controller.set_pulse(self.zero_pulse)  # Set Max Throttle
        time.sleep(1)

    def update(self, throttle):
        if throttle > 0:
            pulse = map_range(throttle,
                              0, self.MAX_THROTTLE,
                              self.zero_pulse, self.max_pulse)
        else:
            pulse = map_range(throttle,
                              self.MIN_THROTTLE, 0,
                              self.min_pulse, self.zero_pulse)

        sys.stdout.flush()
        self.controller.set_pulse(pulse)
        return '123'


class Adafruit_Motor_Hat_Controller:
    ''' 
    Adafruit DC Motor Controller 
    For differential drive cars you need one controller for each motor.
    '''

    def __init__(self, motor_num):
        from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor
        import atexit

        self.FORWARD = Adafruit_MotorHAT.FORWARD
        self.BACKWARD = Adafruit_MotorHAT.BACKWARD
        self.mh = Adafruit_MotorHAT(addr=0x60)

        self.motor = self.mh.getMotor(motor_num)
        self.motor_num = motor_num

        atexit.register(self.turn_off_motors)
        self.speed = 0
        self.throttle = 0

    def turn_off_motors(self):
        self.mh.getMotor(self.motor_num).run(Adafruit_MotorHAT.RELEASE)

    def turn(self, speed):
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''
        if speed > 1 or speed < -1:
            raise ValueError("Speed must be between 1(forward) and -1(reverse)")

        self.speed = speed
        self.throttle = int(map_range(abs(speed), -1, 1, -255, 255))

        if speed > 0:
            self.motor.run(self.FORWARD)
        else:
            self.motor.run(self.BACKWARD)

        self.motor.setSpeed(self.throttle)

    def test(self, seconds=.5):
        speeds = [-.5, -1, -.5, 0, .5, 1, 0]
        for s in speeds:
            self.turn(s)
            time.sleep(seconds)
            print('speed: %s   throttle: %s' % (self.speed, self.throttle))
        print('motor #%s test complete' % self.motor_num)
