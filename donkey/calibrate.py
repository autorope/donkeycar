from time import sleep

class PCA9685_Controller:
    # Init with 60hz frequency by default, good for servos.
    def __init__(self, channel, frequency=60):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()

        self.pwm.set_pwm_freq(frequency)
        self.channel = channel

    def set_pulse(self, pulse):
        self.pwm.set_pwm(self.channel, 0, pulse) 
        

if __name__ == '__main__':

	c = PCA9685_Controller(0)
	for i in range (1, 1000):
		c.set_pulse(i)
		sleep(1)
