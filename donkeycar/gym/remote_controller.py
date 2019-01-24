'''
file: remote_controller.py
author: Tawn Kramer
date: 2016-01-24
desc: Control a remote donkey robot over network
'''

import time

from donkeycar.parts.network import TCPClientValue, UDPValuePub
from donkeycar.parts.image import JpgToImgArr

class DonkeyRemoteContoller:
    def __init__(self, host, sensors_port, controls_port):
        self.camera_sub = TCPClientValue("donkey/camera", host=host, port=sensors_port)
        self.controller_pub = UDPValuePub("donkey/controls", port=controls_port)
        self.jpgToImg = JpgToImgArr()

    def get_sensor_size(self):
        return (120, 160, 3)

    def wait_until_connected(self):
        while not self.camera_sub.is_connected():
            self.camera_sub.connect()

    def take_action(self, action):
        self.controller_pub.run(action)

    def quit(self):
        self.camera_sub.shutdown()
        self.controller_pub.shutdown()

    def observe(self):
        img = self.camera_sub.run()
        observation = self.jpgToImg.run(img)
        return observation
    

    
