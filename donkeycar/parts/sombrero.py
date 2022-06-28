class Sombrero:
    '''
    A pi hat developed by Adam Conway to manage power, pwm for a Donkeycar
    This requires that GPIO 26 is brought low to enable the pwm out.
    Because all GPIO modes have to be the same accross code, we use BOARD
    mode, which is physical pin 37.
    '''

    def __init__(self):
        try:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(37, GPIO.OUT)
            GPIO.output(37, GPIO.LOW)
            print("sombrero enabled")
        except:
            pass

    def __del__(self):
        try:
            import RPi.GPIO as GPIO

            GPIO.cleanup()
            print("sombrero disabled")
        except:
            pass
