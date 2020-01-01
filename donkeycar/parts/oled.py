import base64
from io import BytesIO
import math
from PIL import Image, ImageFont, ImageDraw
from queue import Queue
import subprocess


class OLEDPart(object):
    '''
    Display part for monochrome i2c OLED displays
    using SSD1306 display controllers with a dimension of 128x64 or 128x32 pixel.
    Draws stats information on the OLED display.
    '''

    def __init__(self, address=0x3C, i2c=None, process_limit=32, auto_record_on_throttle=False, display_width=128, display_height=64, name_ethernet_interface="eth0", name_wlan_interface="wlan0"):
        # Display subystem
        self._EMPTY = ''
        self._SLOT_COUNT = 4
        self.display_height = display_height
        self.slots = [self._EMPTY] * self._SLOT_COUNT
        self.display = SSD1306Driver(address, i2c, process_limit, display_width, display_height)
        self.canvas = self.display.get_canvas()
        self.font = ImageFont.load_default()

        # Static image resources
        self.IMAGE_RESOURCES = {
            "user": self.get_user_image_as_pil(),
            "local": self.get_local_pilot_image_as_pil(),
            "local_angle": self.get_local_angle_image_as_pil()
        }

        # States
        self.last_user_mode = None
        self.last_recoding_state = None
        self.last_num_records = None
        self.is_donkeycar_starting_up = True
        self.update_requested = True

        # Infomation to display
        if auto_record_on_throttle:
            self.recording = 'AUTO'
        else:
            self.recording = 'NO (Records = 0)'
        self.num_records = 0
        self.user_mode = None
        eth_interface = OLEDPart.get_ip_address(name_ethernet_interface)
        wlan_interface = OLEDPart.get_ip_address(name_wlan_interface)
        if eth_interface is not None:
            self.eth_interface = "{}: {}".format(name_ethernet_interface, eth_interface)
        else:
            self.eth_interface = None
        if wlan_interface is not None:
            self.wlan_interface = "{}: {}".format(name_wlan_interface, wlan_interface)
        else:
            self.wlan_interface = None

    def update_slot(self, index, text):
        '''
        Set text to a slot
        '''
        if index < len(self.slots):
            self.slots[index] = text

    def clear_slot(self, index):
        '''
        Clears slot content
        '''
        if index < len(self.slots):
            self.slots[index] = self._EMPTY

    def display_text(self):
        '''
        Writes text to a slot
        '''
        x = 0
        top = -2
        for i in range(self._SLOT_COUNT):
            text = self.slots[i]
            if len(text) > 0:
                self.canvas.text((x, top), text, font=self.font, fill=255)
                top += 8

    def run(self, recording, num_records, user_mode):
        '''
        Acquires status information, process them and triggers the
        graphic subsystem to send data to i2c
        '''
        # check if input data is available
        if self.is_donkeycar_starting_up:
            if None not in [recording, user_mode]:
                self.display.cls()
                self.is_donkeycar_starting_up = False
                return
        self.process_recording_stats(recording, num_records)
        self.process_user_mode(user_mode)
        if self.update_requested:
            self.display.cls()
            self.update_slots()
            self.display_text()
            self.display_user_mode_icon(user_mode)
            self.display.display()
            self.update_requested = False
        self.display.process_queues()

    def process_user_mode(self, user_mode):
        '''
        Process user mode changes
        '''
        if user_mode == None or user_mode == self.last_user_mode:
            return
        self.last_user_mode = user_mode
        self.user_mode = "User Mode ({})".format(user_mode)
        self.update_requested = True

    def display_user_mode_icon(self, user_mode):
        '''
        On large displays with 64 and more pixels, the user mode is also visualized with an image
        '''
        if self.display_height >= 64:
            assert user_mode in ["user", "local", "local_angle"]
            self.display.render_pil_image(self.canvas, self.IMAGE_RESOURCES[user_mode], 50, 34)

    def process_recording_stats(self, recording, num_records):
        '''
        Process state changes of the recording state and the number of records.
        The number of records is updated everytime its passes a multiply of 400.
        This avoids too much updates on the i2c bus, that cannot be processed in time.
        '''
        rounded_num_recs = self.roundup(num_records)
        if recording == None:
            return
        if recording == self.last_recoding_state and rounded_num_recs == self.last_num_records:
            return
        self.last_recoding_state = recording
        self.last_num_records = rounded_num_recs
        rec_state_print = "YES" if recording else "NO"
        self.recording = "{} (Records = {})".format(rec_state_print, rounded_num_recs)
        self.update_requested = True

    def update_slots(self):
        '''
        Uppdates all slots
        '''
        updates = [self.eth_interface, self.wlan_interface, self.recording, self.user_mode]
        index = 0
        for update in updates:
            if update is not None:
                self.update_slot(index, update)
                index += 1

    def roundup(self, x):
        '''
        Rounds a given number up to the next 400
        '''
        if x != None:
            return int(math.ceil(x / 400.0)) * 400
        return 0

    def shutdown(self):
        self.display.shutdown()

    def get_user_image_as_pil(self):
        return self.display.base64_to_pil_image("""
            iVBORw0KGgoAAAANSUhEUgAAABwAAAAcAQMAAABIw03XAAAABlBMVEUAAAD///+l2Z/dAAAAAWJL
            R0QAiAUdSAAAADxJREFUCNdjYJBvYGBgqH8AJP5/gBKM/38QTzBAiA8wU+wPAAl+BhgAccHq2P//
            A/L+/z/A8P8/UDUWAgBOjzmB8U2V4QAAAABJRU5ErkJggg==
        """)

    def get_local_angle_image_as_pil(self):
        return self.display.base64_to_pil_image("""
            iVBORw0KGgoAAAANSUhEUgAAABwAAAAcAQMAAABIw03XAAAABlBMVEUAAAD///+l2Z/dAAAAAWJL
            R0QAiAUdSAAAAGNJREFUCNdlzqsRgDAQRdGbQSApYTshbUVEhEEgKYnthJSwOAQzy9dhjnz3QVQI
            vkPjB3TuIBoLQlfoaZVMU0mED4tqbL4bbv7HL0yKkWSoL1nGSi+TIjJfy+tS3tCTfOL3jRMyCT0e
            1rEppwAAAABJRU5ErkJggg==
        """)

    def get_local_pilot_image_as_pil(self):
        return self.display.base64_to_pil_image("""
            iVBORw0KGgoAAAANSUhEUgAAABwAAAAcAQMAAABIw03XAAAABlBMVEUAAAD///+l2Z/dAAAAAWJL
            R0QAiAUdSAAAAIRJREFUCNctzTEKwjAYhuG3CNFB8setAbH1Bl2Fgm5eQ/AgjQgRQfBKnewieIUe
            IWOd4j+4PHzT90J0UNxLmK0eSv0Gs3spPsLSX2HhL1BKEXDdGGhy6tmm6cC5b08cw6ZmwDZEMQ67
            H0C+WUn5v2x10z8xMBerjeda+bTazRPQjUoV+AFd4h+0B3GDTQAAAABJRU5ErkJggg==
        """)

    @classmethod
    def get_ip_address(cls, interface):
        '''
        Extracts the IPv4 address of a given interface
        See https://github.com/NVIDIA-AI-IOT/jetbot/blob/master/jetbot/utils/utils.py
        '''
        try:
            if OLEDPart.get_network_interface_state(interface) == 'down':
                return None
            cmd = "ifconfig %s | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'" % interface
            return subprocess.check_output(cmd, shell=True).decode('ascii')[:-1]
        except:
            return None

    @classmethod
    def get_network_interface_state(cls, interface):
        '''
        Extracts the current operation state of a network interface from sys-fs
        '''
        return subprocess.check_output('cat /sys/class/net/%s/operstate' % interface, shell=True).decode('ascii')[:-1]


class SSD1306Driver:
    '''
    Custom SSD1306 display driver that works with Donkey's Python package selection
    and implements time-constant i2c access based on queuing.
    Inspired by https://github.com/BLavery/lib_oled96/blob/master/lib_oled96.py
    '''

    def __init__(self, address, i2c, process_limit, display_width, display_height):
        if i2c is None:
            import Adafruit_GPIO.I2C as I2C
            i2c = I2C
        self.device = i2c.get_i2c_device(address)
        self.cmd_mode = 0x00
        self.data_mode = 0x40
        self.addr = address
        self.process_limit = process_limit
        self.width = display_width
        self.height = display_height
        self.pages = int(self.height / 8)
        self.image = Image.new('1', (self.width, self.height))
        # this is a "draw" object for preparing display contents
        self.canvas = ImageDraw.Draw(self.image)
        self.data_queue = Queue()
        self.cmd_queue = Queue()
        # iInitialize the display using the magic sequence
        self._command(
            self.Cmds.DISPLAYOFF,
            self.Cmds.SETDISPLAYCLOCKDIV, 0x80,
            self.Cmds.SETMULTIPLEX,       0x3F,
            self.Cmds.SETDISPLAYOFFSET,   0x00,
            self.Cmds.SETSTARTLINE,
            self.Cmds.CHARGEPUMP,         0x14,
            self.Cmds.MEMORYMODE,         0x00,
            self.Cmds.SEGREMAP,
            self.Cmds.COMSCANDEC,
            self.Cmds.SETCOMPINS,         0x12,
            self.Cmds.SETCONTRAST,        0xCF,
            self.Cmds.SETPRECHARGE,       0xF1,
            self.Cmds.SETVCOMDETECT,      0x40,
            self.Cmds.DISPLAYALLON_RESUME,
            self.Cmds.NORMALDISPLAY,
            self.Cmds.DISPLAYON)
        self.process_queues_at_once()
        self.cls()
        if display_height > 32:
            self._show_donkey_logo()
        self.process_queues_at_once()
        print("OLED display initialized.")

    def get_canvas(self):
        return self.canvas

    def process_queues(self):
        '''
        Updates the display with "fair" usage of i2c in the drive loop.

        When it is the OLED display part's turn, send a limited
        number of queued commands to the display over i2c.
        Then, release i2c access to let other peripherials use i2c (e.g. actuators).
        '''
        process_limit = self.process_limit
        for current_queue in [self.cmd_queue, self.data_queue]:
            if current_queue.empty():
                return
            else:
                while process_limit > 0 and not current_queue.empty():
                    items = current_queue.get()
                    self.device.write8(items[0], items[1])
                    process_limit = process_limit - 1

    def process_queues_at_once(self):
        '''
        Updates the display aggressively.
        Do not use it, if other peripherials on i2c should perform
        actions simultaneously with hard/soft dead lines (e.g. control actuators)
        in the event loop.
        '''
        while not self.cmd_queue.empty() or not self.data_queue.empty():
            self.process_queues()

    def _command(self, *cmd):
        '''
        Sends a command or sequence of commands through to the
        device - maximum allowed is 32 bytes in one go.
        LIMIT ON ARDUINO: CMD BYTE + 31 = 32, SO LIMIT TO 31
        '''
        assert(len(cmd) <= 31)
        for current_cmd in list(cmd):
            self.cmd_queue.put((self.cmd_mode, current_cmd))

    def _data(self, data):
        """
        Sends a data byte or sequence of data bytes through to the
        device - maximum allowed in one transaction is 32 bytes, so if
        data is larger than this it is sent in chunks.
        """

        for i in range(0, len(data), 31):
            for current_data in list(data[i:i+31]):
                self.cmd_queue.put((self.data_mode, current_data))

    def _show_donkey_logo(self):
        self.display_base64_encoded_png_images("""
            iVBORw0KGgoAAAANSUhEUgAAAIAAAABAAQMAAADoGO08AAABhWlDQ1BJQ0MgcHJvZmlsZQAAKJF9
            kT1Iw0AcxV9TpaIVh1ZQcchQHcSCqIijVqEIFUKt0KqDyfVLaNKQpLg4Cq4FBz8Wqw4uzro6uAqC
            4AeIi6uToouU+L+k0CLGg+N+vLv3uHsHCLUSU822MUDVLCMZj4npzIoYeEUXehFCP0ZkZuqzkpSA
            5/i6h4+vd1Ge5X3uz9GdzZkM8InEM0w3LOJ14qlNS+e8TxxmRTlLfE48atAFiR+5rrj8xrngsMAz
            w0YqOUccJhYLLay0MCsaKvEkcSSrapQvpF3Oct7irJYqrHFP/sJgTlte4jrNQcSxgEVIEKGggg2U
            YCFKq0aKiSTtxzz8A45fIpdCrg0wcsyjDBWy4wf/g9/dmvmJcTcpGAPaX2z7YwgI7AL1qm1/H9t2
            /QTwPwNXWtNfrgHTn6RXm1rkCOjZBi6um5qyB1zuAH1PumzIjuSnKeTzwPsZfVMGCN0Cnatub419
            nD4AKeoqcQMcHALDBcpe83h3R2tv/55p9PcDjopysj7af4sAAAAGUExURQAAAP///6XZn90AAAAB
            YktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH4wsVFAkgvZDFHQAAAZ9JREFU
            OMvV071LAmEcwPGTy6DCWrSIxLFBClpaQtTqP2jrjQiR2gtyOH3MKIcKaWgIBNFoSYSIWiJ86Ygb
            ImwrCjzrqKul5+SG5w6j66jz/Pkn9GzPh+/vgYeHh6L+z/JVfXEWJwqELRogIU4HRNjoHyBFEwWc
            8MlCA1SMOd6FCGecEVFlLPJeRLABzLyAxVnPHP3ZADWAg3yIMUGpv2Cx8q6YoMri7drjyQP9ZRaC
            RlKSxjbgQxZv1ngdFANqhOO1AgD1vpxaKEiElf72FpWUNaQXG1JzJBUuKBJdNYoaSeRRpNYEWYdw
            GIB+9TxiVFAsJS7RXBNorax5UKiusSZw378QLzYg/sVEdNgq7bSlz6M60AoTUfTi6sK2uOQH72EN
            Wp+zENor9omDIoAuW2cpCIsuRx8bg4XN5kgHYNHpGjlcjwLopUYncxAGqOWXYwjdlDuTpFpGpgff
            ILipmcNhODLmvHvdbSmcZ5lNWNiHV9zbsBhaTV53tED/1FEPBG+umt1sOfQ0k3VAGNgrHu9DsF/F
            nuwQ2v3+ccs/+pM/j2DaTwHeAPoAAAAASUVORK5CYII=
        """)

    def display_base64_encoded_png_images(self, base64_str_data, x_offset=0, y_offset=0):
        '''
        Display base64-encoded PNG image data on the display.

        To avoid external files, images are stored as base64-encoded black/white PNG images
        with a one bit palette.
        '''
        im = self.base64_to_pil_image(base64_str_data)
        self.render_pil_image(self.canvas, im, x_offset, y_offset)
        self.display()

    def base64_to_pil_image(self, base64_str_data):
        '''
        Loads pil images from base64-encoded image files
        '''
        binary_monochrome_png = base64.b64decode(base64_str_data)
        return Image.open(BytesIO(binary_monochrome_png))

    def render_pil_image(self, canvas, pil_image, x_offset=0, y_offset=0):
        '''
        Draws any PIL image on a canvas
        '''
        width, height = pil_image.size
        for x in range(width):
            for y in range(height):
                data = pil_image.getpixel((x, y))
                assert data == 0 or data == 1
                x_coords = x + x_offset
                y_coords = y + y_offset
                canvas.rectangle(
                    (x_coords, y_coords, x_coords, y_coords), outline=data, fill=0)

    def shutdown(self):
        # indicate that the thread should be stopped
        print('Stopping OLEDDisplay')
        self.cls()
        self.process_queues_at_once()

    def display(self):
        '''
        The image on the "canvas" is flushed through to the hardware display.
        Takes the 1-bit image and queues it in order to send it to the display lateron.
        '''

        self._command(
            self.Cmds.COLUMNADDR, 0x00, self.width-1,  # Column start/end address
            self.Cmds.PAGEADDR,   0x00, self.pages-1)  # Page start/end address

        pix = list(self.image.getdata())
        step = self.width * 8
        buf = []
        for y in range(0, self.pages * step, step):
            i = y + self.width-1
            while i >= y:
                byte = 0
                for n in range(0, step, self.width):
                    byte |= (pix[i + n] & 0x01) << 8
                    byte >>= 1

                buf.append(byte)
                i -= 1
        self._data(buf)  # push out the whole lot

    def cls(self):
        self.canvas.rectangle(
            (0, 0, self.width-1, self.height-1), outline=0, fill=0)
        self.display()

    def onoff(self, onoff):
        if onoff == 0:
            self._command(self.Cmds.DISPLAYOFF)
        else:
            self._command(self.Cmds.DISPLAYON)

    class Cmds:
        CHARGEPUMP = 0x8D
        COLUMNADDR = 0x21
        COMSCANDEC = 0xC8
        COMSCANINC = 0xC0
        DISPLAYALLON = 0xA5
        DISPLAYALLON_RESUME = 0xA4
        DISPLAYOFF = 0xAE
        DISPLAYON = 0xAF
        EXTERNALVCC = 0x1
        INVERTDISPLAY = 0xA7
        MEMORYMODE = 0x20
        NORMALDISPLAY = 0xA6
        PAGEADDR = 0x22
        SEGREMAP = 0xA0
        SETCOMPINS = 0xDA
        SETCONTRAST = 0x81
        SETDISPLAYCLOCKDIV = 0xD5
        SETDISPLAYOFFSET = 0xD3
        SETHIGHCOLUMN = 0x10
        SETLOWCOLUMN = 0x00
        SETMULTIPLEX = 0xA8
        SETPRECHARGE = 0xD9
        SETSEGMENTREMAP = 0xA1
        SETSTARTLINE = 0x40
        SETVCOMDETECT = 0xDB
        SWITCHCAPVCC = 0x2
