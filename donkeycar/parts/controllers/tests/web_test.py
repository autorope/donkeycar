# -*- coding: utf-8 -*-
import pytest
import json
import tempfile
from ..web import LocalWebController

@pytest.fixture
def server():
    server = LocalWebController()
    return server


def test_json_output(server):
    result = server.run()
    print(result)
    json_result = json.dumps(result)
    d = json.loads(json_result)
    print(d)
    assert d['user/angle'] is not None
