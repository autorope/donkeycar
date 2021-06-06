# requires the Adafruit ssd1306 library: pip install adafruit-circuitpython-ssd1306

import subprocess
import time
from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306


class OLEDDisplay(object):
    '''
    Manages drawing of text on the OLED display.
    '''
    def __init__(self, rotation=0, resolution=1):
        # Placeholder
        self._EMPTY = ''
        # Total number of lines of text
        self._SLOT_COUNT = 4
        self.slots = [self._EMPTY] * self._SLOT_COUNT
        self.display = None
        self.rotation = rotation
        if resolution == 2:
            self.height = 64
        else:
            self.height = 32

    def init_display(self):
        '''
        Initializes the OLED display.
        '''
        if self.display is None:
            # Create the I2C interface.
            i2c = busio.I2C(SCL, SDA)
            # Create the SSD1306 OLED class.
            # The first two parameters are the pixel width and pixel height.  Change these
            # to the right size for your display!
            self.display = adafruit_ssd1306.SSD1306_I2C(128, self.height, i2c)
            self.display.rotation = self.rotation


            self.display.fill(0)
            self.display.show()

            # Create blank image for drawing.
            # Make sure to create image with mode '1' for 1-bit color.
            self.width = self.display.width
            self.image = Image.new("1", (self.width, self.height))

            # Get drawing object to draw on image.
            self.draw = ImageDraw.Draw(self.image)

            # Draw a black filled box to clear the image.
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
            # Load Fonts
            self.font = ImageFont.load_default()
            self.clear_display()

    def clear_display(self):
        if self.draw is not None:
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

    def update_slot(self, index, text):
        if index < len(self.slots):
            self.slots[index] = text

    def clear_slot(self, index):
        if index < len(self.slots):
            self.slots[index] = self._EMPTY

    def update(self):
        '''Display text'''
        x = 0
        top = -2
        self.clear_display()
        for i in range(self._SLOT_COUNT):
            text = self.slots[i]
            if len(text) > 0:
                self.draw.text((x, top), text, font=self.font, fill=255)
                top += 8

        # Update
        self.display.rotation = self.rotation
        self.display.image(self.image)
        self.display.show()


class OLEDPart(object):
    '''
    The part that updates status on the oled display.
    '''
    def __init__(self, rotation, resolution, auto_record_on_throttle=False):
        self.oled = OLEDDisplay(rotation, resolution)
        self.oled.init_display()
        self.on = False
        if auto_record_on_throttle:
            self.recording = 'AUTO'
        else:
            self.recording = 'NO'
        self.num_records = 0
        self.user_mode = None
        eth0 = OLEDPart.get_ip_address('eth0')
        wlan0 = OLEDPart.get_ip_address('wlan0')
        if eth0 is not None:
            self.eth0 = 'eth0 : %s' % (eth0)
        else:
            self.eth0 = None
        if wlan0 is not None:
            self.wlan0 = 'wlan0 : %s' % (wlan0)
        else:
            self.wlan0 = None

    def run(self):
        if not self.on:
            self.on = True

    def run_threaded(self, recording, num_records, user_mode):
        if num_records is not None and num_records > 0:
            self.num_records = num_records

        if recording:
            self.recording = 'YES (Records = %s)' % (self.num_records)
        else:
            self.recording = 'NO (Records = %s)' % (self.num_records)

        self.user_mode = 'User Mode (%s)' % (user_mode)

    def update_slots(self):
        updates = [self.eth0, self.wlan0, self.recording, self.user_mode]
        index = 0
        # Update slots
        for update in updates:
            if update is not None:
                self.oled.update_slot(index, update)
                index += 1

        # Update display
        self.oled.update()

    def update(self):
        self.on = True
        # Run threaded loop by itself
        while self.on:
            self.update_slots()

    def shutdown(self):
        self.oled.clear_display()
        self.on = False

    # https://github.com/NVIDIA-AI-IOT/jetbot/blob/master/jetbot/utils/utils.py

    @classmethod
    def get_ip_address(cls, interface):
        if OLEDPart.get_network_interface_state(interface) == 'down':
            return None
        cmd = "ifconfig %s | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'" % interface
        return subprocess.check_output(cmd, shell=True).decode('ascii')[:-1]

    @classmethod
    def get_network_interface_state(cls, interface):
        return subprocess.check_output('cat /sys/class/net/%s/operstate' % interface, shell=True).decode('ascii')[:-1]
