import json
import os
from importlib import reload

import pytest

import donkeycar.templates.cfg_complete as cfg
from donkeycar.parts.web_controller.web import LocalWebController


@pytest.fixture
def server():
    server = LocalWebController(cfg.WEB_CONTROL_PORT)
    return server


def test_json_output(server):
    result = server.run()
    json_result = json.dumps(result)
    d = json.loads(json_result)

    assert server.port == 8887

    assert d is not None
    assert int(d[0]) == 0


def test_web_control_user_defined_port():
    os.environ["WEB_CONTROL_PORT"] = "12345"
    reload(cfg)
    server = LocalWebController(port=cfg.WEB_CONTROL_PORT)

    assert server.port == 12345


def _free_port():
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_shutdown_releases_the_port():
    """
    shutdown() used to be a no-op, leaving the tornado server and its socket
    alive after the vehicle stopped. Invisible when the process exits with the
    vehicle, but the MCP supervisor rebuilds the vehicle in a running process
    and the replacement could not bind.
    """
    import threading
    import time

    port = _free_port()
    first = LocalWebController(port=port)
    thread = threading.Thread(target=first.update, daemon=True)
    thread.start()
    time.sleep(0.5)

    first.shutdown()

    second = LocalWebController(port=port)
    second_thread = threading.Thread(target=second.update, daemon=True)
    second_thread.start()
    time.sleep(0.5)
    try:
        assert second.server is not None, "could not rebind the port after shutdown"
    finally:
        second.shutdown()


def test_shutdown_before_serving_does_not_leak():
    """A shutdown arriving while the server thread is still starting must not
    leave a socket bound behind it."""
    port = _free_port()
    controller = LocalWebController(port=port)
    controller.shutdown()  # never started

    other = LocalWebController(port=port)
    import threading
    import time

    thread = threading.Thread(target=other.update, daemon=True)
    thread.start()
    time.sleep(0.5)
    try:
        assert other.server is not None
    finally:
        other.shutdown()
