import time
import requests


class AlexaController(object):
    '''
    Accept simple command from alexa. For the command supported, please refer
    to the README.md
    '''
    API_ENDPOINT = "http://alexa.robocarstore.com"

    def __init__(self, ctr, cfg, debug=False):
        self.running = True
        self.debug = debug
        self.ctr = ctr
        self.cfg = cfg  # Pass the config object for altering AI_THROTTLE_MULT

        if self.cfg.ALEXA_DEVICE_CODE is None:
            raise Exception("Please set cfg.ALEXA_DEVICE_CODE in myconfig.py")

    def get_command(self):
        url = "{}/{}".format(self.API_ENDPOINT, 'command')

        params = {
            'deviceCode': self.cfg.ALEXA_DEVICE_CODE
        }

        r = requests.get(url=url, params=params)
        result = r.json()

        return result['command']

    def update(self):
        while (self.running):
            command = self.get_command()
            if self.debug:
                print("command = {}".format(command))
            elif command is not None:
                print("Voice control: {}".format(command))

            if command == "autopilot":
                self.ctr.mode = "local"
            elif command == "speedup":
                self.cfg.AI_THROTTLE_MULT += 0.05
            elif command == "slowdown":
                self.cfg.AI_THROTTLE_MULT -= 0.05
            elif command == "stop":
                self.ctr.mode = "user"
                self.cfg.AI_THROTTLE_MULT = 1

            if self.debug:
                print("mode = {}, cfg.AI_THROTTLE_MULT={}".format(
                    self.ctr.mode, self.cfg.AI_THROTTLE_MULT))
            time.sleep(0.25)

    def run_threaded(self):
        pass

    def shutdown(self):
        self.running = False
