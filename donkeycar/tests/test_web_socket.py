
from donkeycar.parts.web_controller.web import WebSocketCalibrateAPI
from functools import partial

from tornado import testing
import tornado.websocket
import tornado.web
import tornado.ioloop
import json
from unittest.mock import Mock
from donkeycar.parts.actuator import PWMSteering, PWMThrottle


class WebSocketCalibrateTest(testing.AsyncHTTPTestCase):
    """
    Example of WebSocket usage as a client
    in AsyncHTTPTestCase-based unit tests.
    """

    def get_app(self):
        app = tornado.web.Application([('/', WebSocketCalibrateAPI)])
        self.app = app

        return app

    def get_ws_url(self):
        return "ws://localhost:" + str(self.get_http_port()) + "/"

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_1(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = Mock()
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"STEERING_LEFT_PWM": 444}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()

        assert self.app.drive_train['steering'].left_pulse == 444
        assert isinstance(self.app.drive_train['steering'].right_pulse, Mock)

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_2(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = Mock()
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"STEERING_RIGHT_PWM": 555}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()

        assert self.app.drive_train['steering'].right_pulse == 555
        assert isinstance(self.app.drive_train['steering'].left_pulse, Mock)

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_3(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        self.app.drive_train = dict()
        self.app.drive_train['throttle'] = Mock()
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"THROTTLE_FORWARD_PWM": 666}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()

        assert self.app.drive_train['throttle'].max_pulse == 666
        assert isinstance(self.app.drive_train['throttle'].min_pulse, Mock)

    @tornado.testing.gen_test
    def test_calibrate_mm1(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        self.app.drive_train = Mock()
        self.app.drive_train_type = "MM1"
        data = {"config": {"MM1_STEERING_MID": 1234}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()

        assert self.app.drive_train.STEERING_MID == 1234
