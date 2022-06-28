'''
file: remote_controller.py
author: Tawn Kramer
date: 2019-01-24
desc: Control a remote donkey robot over network
'''

import time

from donkeycar.parts.network import MQTTValueSub, MQTTValuePub
from donkeycar.parts.image import JpgToImgArr

class DonkeyRemoteContoller:
    def __init__(self, donkey_name, mqtt_broker, sensor_size=(120, 160, 3)):
        self.camera_sub = MQTTValueSub("donkey/%s/camera" % donkey_name, broker=mqtt_broker)
        self.controller_pub = MQTTValuePub("donkey/%s/controls" % donkey_name, broker=mqtt_broker)
        self.jpgToImg = JpgToImgArr()
        self.sensor_size = sensor_size

    def get_sensor_size(self):
        return self.sensor_size

    def wait_until_connected(self):
        pass

    def take_action(self, action):
        self.controller_pub.run(action)

    def quit(self):
        self.camera_sub.shutdown()
        self.controller_pub.shutdown()

    def get_original_image(self):
        return self.img

    def observe(self):
        jpg = self.camera_sub.run()
        self.img = self.jpgToImg.run(jpg)
        return self.img


    
