
import base64
import json
import logging
import socket
import threading
import time
import unittest

import numpy as np
import cv2

from donkeycar.parts.dgym import DonkeyGymEnv


class Config(object):
    def __init__(self):
        self.DONKEY_GYM = True
        self.DONKEY_SIM_PATH = "remote"
        self.DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0"
        self.SIM_HOST = "127.0.0.1"
        self.SIM_ARTIFICIAL_LATENCY = 9091
        self.SIM_RECORD = {
            "pos": False,
            "vel": False,
            "gyro": False,
            "accel": False,
            "odom": False,
            "lidar": False,
            "cte": False,
            "speed": False,
            "orientation": False,
        }

        self.GYM_CONF = {
            "body_style": "donkey",
            "body_rgb": (128, 128, 128),
            "car_name": "donkey",
            "font_size": 100,
        }


class Server(object):
    """
    A simple TCP server that listens for a connection.
    Used to test the DonkeyGymEnv class.
    """

    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 9091

        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

        self.running = True
        self.last_control = None

        logging.info("Test server started")

    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.client, self.addr = self.socket.accept()

        # send a car_loaded message then start listening
        self.car_loaded()
        self.listen()

    def car_loaded(self):
        msg = {"msg_type": "car_loaded"}
        self.send(msg)

    def listen(self):
        while self.running:
            data = self.client.recv(1024)
            if not data:
                break
            data = data.decode("utf-8").strip()
            logging.debug(f"Received: {data}")

            # create dummy base64 png image
            img = np.zeros((120, 160, 3), dtype=np.uint8)
            _, encimg = cv2.imencode(".png", img)

            # send dummy telemetry
            msg = {
                "msg_type": "telemetry",
                "image": base64.b64encode(encimg).decode("utf-8"),
                "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0,
                "vel_x": 0.0, "vel_y": 0.0, "vel_z": 0.0,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
                "accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0,
                "odom_fl": 0.1, "odom_fr": 0.2, "odom_rl": 0.3, "odom_rr": 0.4,
                "lidar": [
                    {"d": 0.0, "rx": 0.0, "ry": 0.0},
                    {"d": 0.0, "rx": 0.1, "ry": 0.0},
                    {"d": 0.0, "rx": 0.2, "ry": 0.0},
                ],
                "cte": 0.0,
                "speed": 0.0,
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            }
            self.send(msg)
            logging.debug(f"Sent: {msg}")

    def send(self, msg: dict):
        json_msg = json.dumps(msg)
        self.client.sendall(json_msg.encode("utf-8") + b"\n")

    def close(self):
        self.running = False
        self.socket.close()
        logging.info("Test server closed")


#
# python -m unittest donkeycar/tests/test_dgym.py
#
class TestDgym(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()
        self.server = Server()

    def tearDown(self):
        self.cfg = None
        self.server.close()

    def test_dgym_startup(self):
        # order of these keys does matter as they determine the order of the output list
        self.cfg.SIM_RECORD = {
            "pos": True,
            "vel": True,
            "gyro": True,
            "accel": True,
            "odom": True,
            "lidar": False,  # disabling lidar for now, need to test as well
            "cte": True,
            "speed": True,
            "orientation": True,
        }

        outputs = ["cam/image_array"]
        self.gym = DonkeyGymEnv(self.cfg, outputs)

        self.assertNotEqual(self.gym.env, None)
        self.assertEqual(self.gym.action, [0.0, 0.0, 0.0])
        self.assertEqual(self.gym.running, True)

        # check that the output list is correct
        self.assertEqual(outputs, [
            "cam/image_array",
            "pos/x", "pos/y", "pos/z",
            "vel/x", "vel/y", "vel/z",
            "gyro/x", "gyro/y", "gyro/z",
            "accel/x", "accel/y", "accel/z",
            "odom/front_left", "odom/front_right", "odom/rear_left", "odom/rear_right",
            "cte",
            "speed",
            "orientation/roll", "orientation/pitch", "orientation/yaw",
        ])

        self.gym.run_threaded(0.5, 0.25, brake=0.1)
        self.assertEqual(self.gym.action, [0.5, 0.25, 0.1])

    def test_dgym_telemetry(self):
        # order of these keys does matter as they determine the order of the output list
        self.cfg.SIM_RECORD = {
            "pos": True,
            "vel": True,
            "gyro": True,
            "accel": True,
            "odom": True,
            "lidar": False,  # disabling lidar for now, need to test as well
            "cte": True,
            "speed": True,
            "orientation": True,
        }

        outputs = ["cam/image_array"]
        self.gym = DonkeyGymEnv(self.cfg, outputs)

        self.assertNotEqual(self.gym.env, None)
        self.assertEqual(self.gym.action, [0.0, 0.0, 0.0])
        self.assertEqual(self.gym.running, True)

        # check that the output list is correct
        self.assertEqual(outputs, [
            "cam/image_array",
            "pos/x", "pos/y", "pos/z",
            "vel/x", "vel/y", "vel/z",
            "gyro/x", "gyro/y", "gyro/z",
            "accel/x", "accel/y", "accel/z",
            "odom/front_left", "odom/front_right", "odom/rear_left", "odom/rear_right",
            "cte",
            "speed",
            "orientation/roll", "orientation/pitch", "orientation/yaw",
        ])

        # check that the telemetry is correct
        current_frame, _, _, current_info = self.gym.env.step([0.5, 0.25, 0.1])
        self.gym.frame = current_frame
        self.gym.info = current_info

        output_data = self.gym.run_threaded(0.5, 0.25, brake=0.1)
        output_image, output_info = output_data[0], output_data[1:]

        self.assertEqual(output_info, [
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            0.1, 0.2, 0.3, 0.4,
            0.0,
            0.0,
            0.0, 0.0, 0.0,
        ])

        self.assertEqual(output_image.shape, current_frame.shape)
