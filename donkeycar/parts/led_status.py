import time
import RPi.GPIO as GPIO

class LED:
    ''' 
    Toggle a GPIO pin for led control
    '''
    def __init__(self, pin):
        self.pin = pin

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.OUT)
        self.blink_changed = 0
        self.on = False

    def toggle(self, condition):
        if condition:
            GPIO.output(self.pin, GPIO.HIGH)
            self.on = True
        else:
            GPIO.output(self.pin, GPIO.LOW)
            self.on = False            

    def blink(self, rate):
        if time.time() - self.blink_changed > rate:
            self.toggle(not self.on)
            self.blink_changed = time.time()

    def run(self, blink_rate):
        if blink_rate == 0:
            self.toggle(False)
        elif blink_rate > 0:
            self.blink(blink_rate)
        else:
            self.toggle(True)

    def shutdown(self):
        self.toggle(False)        
        GPIO.cleanup()


class RGB_LED:
    ''' 
    Toggle a GPIO pin on at max_duty pwm if condition is true, off if condition is false.
    Good for LED pwm modulated
    '''
    def __init__(self, pin_r, pin_g, pin_b, invert_flag=False):
        self.pin_r = pin_r
        self.pin_g = pin_g
        self.pin_b = pin_b
        self.invert = invert_flag
        print('setting up gpio in board mode')
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_r, GPIO.OUT)
        GPIO.setup(self.pin_g, GPIO.OUT)
        GPIO.setup(self.pin_b, GPIO.OUT)
        freq = 50
        self.pwm_r = GPIO.PWM(self.pin_r, freq)
        self.pwm_g = GPIO.PWM(self.pin_g, freq)
        self.pwm_b = GPIO.PWM(self.pin_b, freq)
        self.pwm_r.start(0)
        self.pwm_g.start(0)
        self.pwm_b.start(0)
        self.zero = 0
        if( self.invert ):
            self.zero = 100

        self.rgb = (50, self.zero, self.zero)

        self.blink_changed = 0
        self.on = False

    def toggle(self, condition):
        if condition:
            r, g, b = self.rgb
            self.set_rgb_duty(r, g, b)
            self.on = True
        else:
            self.set_rgb_duty(self.zero, self.zero, self.zero)
            self.on = False

    def blink(self, rate):
        if time.time() - self.blink_changed > rate:
            self.toggle(not self.on)
            self.blink_changed = time.time()

    def run(self, blink_rate):
        if blink_rate == 0:
            self.toggle(False)
        elif blink_rate > 0:
            self.blink(blink_rate)
        else:
            self.toggle(True)

    def set_rgb(self, r, g, b):
        r = r if not self.invert else 100-r
        g = g if not self.invert else 100-g
        b = b if not self.invert else 100-b
        self.rgb = (r, g, b)
        self.set_rgb_duty(r, g, b)

    def set_rgb_duty(self, r, g, b):
        self.pwm_r.ChangeDutyCycle(r)
        self.pwm_g.ChangeDutyCycle(g)
        self.pwm_b.ChangeDutyCycle(b)

    def shutdown(self):
        self.toggle(False)
        GPIO.cleanup()


if __name__ == "__main__":
    import time
    import sys
    pin_r = int(sys.argv[1])
    pin_g = int(sys.argv[2])
    pin_b = int(sys.argv[3])
    rate = float(sys.argv[4])
    print('output pin', pin_r, pin_g, pin_b, 'rate', rate)

    p = RGB_LED(pin_r, pin_g, pin_b)
    
    iter = 0
    while iter < 50:
        p.run(rate)
        time.sleep(0.1)
        iter += 1
    
    delay = 0.1

    iter = 0
    while iter < 100:
        p.set_rgb(iter, 100-iter, 0)
        time.sleep(delay)
        iter += 1
    
    iter = 0
    while iter < 100:
        p.set_rgb(100 - iter, 0, iter)
        time.sleep(delay)
        iter += 1

    p.shutdown()

