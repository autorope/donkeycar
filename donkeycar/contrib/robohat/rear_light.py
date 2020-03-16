import neopixel
import board
import adafruit_logging as logging
logger = logging.getLogger('rear_light')
logger.setLevel(logging.INFO)


class RearLight:
    """
    Class for controlling rear light
    """
    RED = (255, 0, 0)
    DARK = (0, 0, 0)
    YELLOW = (255, 150, 0)

    def __init__(self):
        pixel_pin = board.NEOPIXEL
        num_pixels = 16
        pixel_brightness = 0.4
        self.pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=pixel_brightness)

        self.is_brake_light_on = False

    def fill_pixels(self, color):
        self.pixels.fill(color)
        self.pixels.show()

    def turn_on_brake_light(self):
        if not self.is_brake_light_on:
            logger.info("turning on brake light")
            self.fill_pixels(RearLight.RED)
            self.is_brake_light_on = True

    def turn_off_brake_light(self):
        if self.is_brake_light_on:
            logger.info("turning off brake light")
            self.fill_pixels(RearLight.DARK)
            self.is_brake_light_on = False

    def run(self, angle, throttle):
        if throttle > 1600:
            self.turn_off_brake_light()
        else:
            self.turn_on_brake_light()
