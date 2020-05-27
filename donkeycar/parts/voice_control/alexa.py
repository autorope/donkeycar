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
        self.DEFAULT_AI_THROTTLE_MULT = self.cfg.AI_THROTTLE_MULT

        if self.cfg.ALEXA_DEVICE_CODE is None:
            raise Exception("Please set cfg.ALEXA_DEVICE_CODE in myconfig.py")

    def log(self, msg):
        print("Voice control: {}".format(msg))

    def get_command(self):
        url = "{}/{}".format(self.API_ENDPOINT, 'command')

        params = {
            'deviceCode': self.cfg.ALEXA_DEVICE_CODE
        }

        command = None

        try:
            response = requests.get(url=url, params=params, timeout=5)
            response.raise_for_status()
            result = response.json()
            if "command" in result:
                command = result['command']
            else:
                self.log("Warning - No command found in response")
        except requests.exceptions.RequestException as e:
            self.log("Warning - Failed to reach Alexa API endpoint")
        except ValueError:  # Catch JSONDecodeError
            self.log('Warning - Decoding JSON failed')

        return command

    def update(self):
        while (self.running):
            command = self.get_command()
            if self.debug:
                self.log("Command = {}".format(command))
            elif command is not None:
                self.log("Command = {}".format(command))

            if command == "autopilot":
                self.ctr.mode = "local"
            elif command == "speedup":
                self.cfg.AI_THROTTLE_MULT += 0.05
            elif command == "slowdown":
                self.cfg.AI_THROTTLE_MULT -= 0.05
            elif command == "stop":
                self.ctr.mode = "user"
                self.cfg.AI_THROTTLE_MULT = self.DEFAULT_AI_THROTTLE_MULT

            if self.debug:
                self.log("mode = {}, cfg.AI_THROTTLE_MULT={}".format(
                    self.ctr.mode, self.cfg.AI_THROTTLE_MULT))

            time.sleep(0.25)  # Give a break between requests

    def run_threaded(self):
        pass

    def shutdown(self):
        self.running = False
