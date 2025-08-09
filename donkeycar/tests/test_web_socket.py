from tornado import testing
import tornado.websocket
import tornado.web
import json
from unittest.mock import Mock
from donkeycar.parts.web_controller.web import WebSocketCalibrateAPI
import tornado.gen


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
    
    async def wait_for_attribute_value(self, obj, attr_name, 
                                       expected_value, timeout_seconds=5):
        """Poll until an object's attribute equals the expected value or timeout."""
        iterations = int(timeout_seconds / 0.1)
        for _ in range(iterations):
            if (hasattr(obj, attr_name) 
                and getattr(obj, attr_name) == expected_value):
                return True
            await tornado.gen.sleep(0.1)
        return False

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_1b(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.left_pulse = None
        mock.right_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = mock
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"STEERING_LEFT_PWM": 444}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['steering'], 'left_pulse', 444)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['steering'].left_pulse == 444
        assert self.app.drive_train['steering'].right_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_1a(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.left_pulse = None
        mock.right_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = mock
        self.app.drive_train_type = "PWM_STEERING_THROTTLE"

        data = {"config": {"STEERING_LEFT_PWM": 444}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['steering'], 'left_pulse', 444)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['steering'].left_pulse == 444
        assert self.app.drive_train['steering'].right_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_2b(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.left_pulse = None
        mock.right_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = mock
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"STEERING_RIGHT_PWM": 555}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['steering'], 'right_pulse', 555)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['steering'].right_pulse == 555
        assert self.app.drive_train['steering'].left_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_2a(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.left_pulse = None
        mock.right_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['steering'] = mock
        self.app.drive_train_type = "PWM_STEERING_THROTTLE"

        data = {"config": {"STEERING_RIGHT_PWM": 555}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['steering'], 'right_pulse', 555)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['steering'].right_pulse == 555
        assert self.app.drive_train['steering'].left_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_3b(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.max_pulse = None
        mock.min_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['throttle'] = mock
        self.app.drive_train_type = "I2C_SERVO"

        data = {"config": {"THROTTLE_FORWARD_PWM": 666}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['throttle'], 'max_pulse', 666)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['throttle'].max_pulse == 666
        assert self.app.drive_train['throttle'].min_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_servo_esc_3a(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.max_pulse = None
        mock.min_pulse = None
        self.app.drive_train = dict()
        self.app.drive_train['throttle'] = mock
        self.app.drive_train_type = "PWM_STEERING_THROTTLE"

        data = {"config": {"THROTTLE_FORWARD_PWM": 666}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train['throttle'], 'max_pulse', 666)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train['throttle'].max_pulse == 666
        assert self.app.drive_train['throttle'].min_pulse is None

    @tornado.testing.gen_test
    def test_calibrate_mm1(self):
        ws_client = yield tornado.websocket.websocket_connect(self.get_ws_url())

        # Now we can run a test on the WebSocket.
        mock = Mock()
        mock.STEERING_MID = None
        self.app.drive_train = mock
        self.app.drive_train_type = "MM1"
        data = {"config": {"MM1_STEERING_MID": 1234}}
        yield ws_client.write_message(json.dumps(data))
        yield ws_client.close()
        
        result = yield self.wait_for_attribute_value(
            self.app.drive_train, 'STEERING_MID', 1234)
        assert result, "WebSocket message not processed within timeout"
        assert self.app.drive_train.STEERING_MID == 1234
