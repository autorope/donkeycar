# -*- coding: utf-8 -*-
import pytest
import json
import os
from donkeycar.parts.web_controller.web import LocalWebController
import donkeycar.templates.cfg_complete as cfg
from importlib import reload

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
    os.environ['WEB_CONTROL_PORT'] = "12345"
    reload(cfg)
    server = LocalWebController(port=cfg.WEB_CONTROL_PORT)
    
    assert server.port == 12345

