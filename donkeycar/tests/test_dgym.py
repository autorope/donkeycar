
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

logger = logging.getLogger(__name__)


class Config(object):
    def __init__(self):
        self.DONKEY_GYM = True
        self.DONKEY_SIM_PATH = "remote"
        self.DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0"

        self.SIM_HOST = "127.0.0.1"
        self.SIM_ARTIFICIAL_LATENCY = 0
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

        self.socket = None
        self.client = None
        self.running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

        logger.info("Test server started")

    def __enter__(self):
        return self

    def car_loaded(self):
        msg = {"msg_type": "car_loaded"}
        self.send(msg)

    def run(self):
        """
        Imitate the donkeysim server with telemetry.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.client, self.addr = self.socket.accept()

        self.car_loaded()

        while self.running:
            try:
                data = self.client.recv(1024 * 256)
                if not data:
                    self.running = False
                    break
            except socket.error:
                self.running = False
                break

            data = data.decode("utf-8").strip()
            logger.debug(f"Received: {data}")

            # create dummy base64 png image
            img = np.zeros((120, 160, 3), dtype=np.uint8)
            _, encimg = cv2.imencode(".png", img)

            # send dummy telemetry
            msg = {
                "msg_type": "telemetry",
                "image": base64.b64encode(encimg).decode("utf-8"),
                "pos_x": 0.1, "pos_y": 0.2, "pos_z": 0.3,
                "vel_x": 0.4, "vel_y": 0.5, "vel_z": 0.6,
                "gyro_x": 0.7, "gyro_y": 0.8, "gyro_z": 0.9,
                "accel_x": 1.0, "accel_y": 1.1, "accel_z": 1.2,
                "odom_fl": 1.3, "odom_fr": 1.4, "odom_rl": 1.5, "odom_rr": 1.6,
                "lidar": [  # simplified lidar data for testing
                    {"d": 10.0, "rx": 0.0, "ry": 0.0},
                    {"d": 20.0, "rx": 90.0, "ry": 0.0},
                    {"d": 30.0, "rx": 180.0, "ry": 0.0},
                    {"d": 40.0, "rx": 270.0, "ry": 0.0},
                ],
                "cte": 1.7,
                "speed": 1.8,
                "roll": 1.9, "pitch": 2.0, "yaw": 2.1,
            }
            self.send(msg)
            logger.debug(f"Sent: {msg}")

    def send(self, msg: dict):
        json_msg = json.dumps(msg)
        self.client.sendall(json_msg.encode("utf-8") + b"\n")

    def close(self):
        self.running = False
        if self.client is not None:
            self.client.close()
        if self.socket is not None:
            self.socket.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


#
# python -m unittest donkeycar/tests/test_dgym.py
#
class TestDgym(unittest.TestCase):
    def setUp(self):
        self.gym = None
        self.cfg = Config()
        self.server = Server()

    def tearDown(self):
        self.cfg = None
        if self.gym is not None:
            self.gym.shutdown()
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
            "pos",
            "vel",
            "gyro",
            "accel",
            "front_left",
            "front_right",
            "rear_left",
            "rear_right",
            "cte",
            "speed",
            "orientation",
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
            "lidar": False,  # disabling lidar, testing it separately
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
            "pos",
            "vel",
            "gyro",
            "accel",
            "front_left",
            "front_right",
            "rear_left",
            "rear_right",
            "cte",
            "speed",
            "orientation",
        ])

        # check that the telemetry is correct
        current_frame, _, _, current_info = self.gym.env.step(
            [0.5, 0.25, 0.1])
        self.gym.frame = current_frame
        self.gym.info = current_info

        output_data = self.gym.run_threaded(0.5, 0.25, brake=0.1)
        output_image, output_info = output_data[0], output_data[1:]

        self.assertEqual(output_info, [
            [0.1, 0.2, 0.3],  # pos
            [0.4, 0.5, 0.6],  # vel
            [0.7, 0.8, 0.9],  # gyro
            [1.0, 1.1, 1.2],  # accel
            1.3, 1.4, 1.5, 1.6,  # odom (front_left, front_right, rear_left and rear_right)
            1.7,  # cte
            1.8,  # speed
            [1.9, 2.0, 2.1],  # orientation
        ])

        self.assertEqual(output_image.shape, current_frame.shape)

    def test_dgym_lidar_not_initialized(self):
        self.cfg.SIM_RECORD = {
            "lidar": True,
        }

        outputs = ["cam/image_array"]
        self.gym = DonkeyGymEnv(self.cfg, outputs)

        self.assertNotEqual(self.gym.env, None)
        self.assertEqual(self.gym.action, [0.0, 0.0, 0.0])
        self.assertEqual(self.gym.running, True)

        # check that the output list is correct
        self.assertEqual(outputs, [
            "cam/image_array",
            "lidar",
        ])

        # check the telemetry when lidar is not initialized
        current_frame, _, _, current_info = self.gym.env.step([0.5, 0.25, 0.1])
        self.gym.frame = current_frame
        self.gym.info = current_info

        output_data = self.gym.run_threaded(0.5, 0.25, brake=0.1)
        output_image, output_info = output_data[0], output_data[1:]

        # expected to be empty as we don't have initialized the lidar
        self.assertEqual(output_info, [[]])

    def test_dgym_lidar_initialized(self):
        self.cfg.SIM_RECORD = {
            "lidar": True,
        }

        self.cfg.GYM_CONF = {
            "lidar_config": {
                "deg_per_sweep_inc": "90.0",
                "deg_ang_down": "0.0",
                "deg_ang_delta": "-1.0",
                "num_sweeps_levels": "1",
                "max_range": "50.0",
                "noise": "0.4",
                "offset_x": "0.0", "offset_y": "0.5", "offset_z": "0.5", "rot_x": "0.0",
            },
        }

        outputs = ["cam/image_array"]
        self.gym = DonkeyGymEnv(self.cfg, outputs)

        self.assertNotEqual(self.gym.env, None)
        self.assertEqual(self.gym.action, [0.0, 0.0, 0.0])
        self.assertEqual(self.gym.running, True)

        # check that the output list is correct
        self.assertEqual(outputs, [
            "cam/image_array",
            "lidar",
        ])

        # check the telemetry when lidar is not initialized
        current_frame, _, _, current_info = self.gym.env.step([0.5, 0.25, 0.1])
        self.gym.frame = current_frame
        self.gym.info = current_info

        output_data = self.gym.run_threaded(0.5, 0.25, brake=0.1)
        output_image, output_info = output_data[0], output_data[1:]

        self.assertEqual(len(output_info[0]), 4)
        self.assertEqual(output_info, [[10.0, 20.0, 30.0, 40.0]])
